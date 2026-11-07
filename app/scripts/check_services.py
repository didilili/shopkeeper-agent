# =========== 学习导航（Learning Guide）· 本文件要学到什么程度 ===========
# 优先级：P2 · 跑通读懂 ｜ 对应章节：第 3、5、6 章
# 掌握程度：能说清"端口可达"和"服务真能干活"的区别，并知道每个服务用什么最小请求验证
# 面试追问：为什么 MySQL 用 select 1、Qdrant 用 get_collections、Embedding 用一次真实向量化？
# 学习动作：先停掉一个容器跑一次，再启动后跑一次，确认失败项和提示对得上
# ========================================================================

"""
本地依赖服务连通性自检

一次检查问数链路依赖的全部基础服务，只看"能否连通并正常响应"，
不校验数据条数、索引内容等业务数据是否正确：
1. TCP 端口是否可达：快速区分"容器没起来"和"起来了但还没就绪"
2. 协议级最小请求：确认服务真的能处理请求，而不只是端口开着

默认零参数直接跑。
"""

import argparse
import asyncio
import socket
import sys
import time
from collections.abc import Awaitable, Callable

from sqlalchemy import text

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.conf.app_config import app_config


def _force_utf8_stdout():
    """Windows 控制台默认 GBK，强制 UTF-8 输出，避免中文乱码"""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def probe_tcp(host: str, port: int, timeout: float) -> tuple[bool, str]:
    """逐个解析出来的地址做 TCP 连接测试，任意一个通就算通过"""
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        return False, f"解析 {host}:{port} 失败：{e}"

    tried: list[str] = []
    for family, socktype, _, _, sockaddr in addresses:
        ip = sockaddr[0]
        # localhost 同时有 ::1 和 127.0.0.1，同一个 IP 只试一次
        if ip in tried:
            continue
        tried.append(ip)

        sock = socket.socket(family, socktype)
        sock.settimeout(timeout)
        try:
            sock.connect(sockaddr)
        except OSError:
            continue
        else:
            return True, f"TCP {ip}:{port} 可连接"
        finally:
            sock.close()

    return False, f"TCP {host}:{port} 在 {timeout}s 内不可达"


async def run_check(
    name: str, check: Callable[[], Awaitable[str]], timeout: float
) -> bool:
    """执行一次协议级检查，统一处理超时和异常"""
    start = time.perf_counter()
    try:
        detail = await asyncio.wait_for(check(), timeout)
    except TimeoutError:
        print(f"[FAIL] {name}：超时（{timeout}s）")
        return False
    except Exception as e:
        print(f"[FAIL] {name}：{type(e).__name__}: {e}")
        return False

    cost_ms = (time.perf_counter() - start) * 1000
    print(f"[OK]   {name}：{detail}（{cost_ms:.0f}ms）")
    return True


async def check_mysql(manager, database: str) -> str:
    """执行一次 select 1，验证账号、库名和连接池都能正常工作"""
    manager.init()
    try:
        async with manager.session_factory() as session:
            await session.execute(text("select 1"))
    finally:
        # init 失败时 engine 可能还是 None
        if manager.engine is not None:
            await manager.close()
    return f"select 1 正常（数据库={database}）"


async def check_qdrant() -> str:
    """拉一次集合列表，验证 Qdrant 服务可用"""
    qdrant_client_manager.init()
    try:
        await qdrant_client_manager.client.get_collections()
    finally:
        await qdrant_client_manager.client.close()
    return "get_collections 正常"


async def check_embedding() -> str:
    """真正做一次向量化，确认模型已加载（冷启动可能较慢）"""
    embedding_client_manager.init()
    vector = await embedding_client_manager.client.aembed_query("ping")
    return f"向量化正常（维度={len(vector)}）"


async def check_es(timeout: float) -> str:
    """查询集群健康状态，red 表示主分片不可用"""
    es_client_manager.init()
    try:
        client = es_client_manager.client.options(request_timeout=timeout)
        health = await client.cluster.health()
    finally:
        await es_client_manager.close()

    status = health["status"]
    if status not in ("green", "yellow"):
        # 抛异常交给 run_check 统一按失败处理
        raise RuntimeError(f"集群状态为 {status}，暂不可用")
    return f"集群健康={status}（节点数={health.get('number_of_nodes')}）"


async def main() -> int:
    parser = argparse.ArgumentParser(description="检查本地依赖服务连通性")
    parser.add_argument("--timeout", type=float, default=5.0, help="常规检查超时秒数")
    parser.add_argument(
        "--embedding-timeout",
        type=float,
        default=60.0,
        help="Embedding 冷启动加载模型可能较慢，单独放宽超时",
    )
    args = parser.parse_args()

    print("== 端口连通性 ==")
    targets = [
        ("mysql-meta", app_config.db_meta.host, app_config.db_meta.port),
        ("mysql-dw", app_config.db_dw.host, app_config.db_dw.port),
        ("qdrant", app_config.qdrant.host, app_config.qdrant.port),
        ("embedding", app_config.embedding.host, app_config.embedding.port),
        ("elasticsearch", app_config.es.host, app_config.es.port),
    ]
    # 端口探测放到线程里并行做，避免多个服务同时不可用时一直串行等待
    probes = await asyncio.gather(
        *(
            asyncio.to_thread(probe_tcp, host, port, args.timeout)
            for _, host, port in targets
        )
    )
    reachable: dict[str, bool] = {}
    for (name, _, _), (ok, detail) in zip(targets, probes):
        marker = "[OK]   " if ok else "[FAIL] "
        print(f"{marker}{name}：{detail}")
        reachable[name] = ok

    print("== 服务响应 ==")
    checks: dict[str, Callable[[], Awaitable[str]]] = {
        "mysql-meta": lambda: check_mysql(
            meta_mysql_client_manager, app_config.db_meta.database
        ),
        "mysql-dw": lambda: check_mysql(
            dw_mysql_client_manager, app_config.db_dw.database
        ),
        "qdrant": check_qdrant,
        "embedding": check_embedding,
        "elasticsearch": lambda: check_es(args.timeout),
    }
    results: dict[str, bool] = {}
    for name, _, _ in targets:
        if not reachable[name]:
            results[name] = False
            continue
        timeout = args.embedding_timeout if name == "embedding" else args.timeout
        results[name] = await run_check(name, checks[name], timeout)

    failed = [name for name, ok in results.items() if not ok]
    ok_count = len(results) - len(failed)
    print(f"结果：{ok_count}/{len(results)} 个服务正常")
    if failed:
        print("失败项：" + "、".join(failed))
        print("提示：docker compose -f docker/docker-compose.yaml up -d")
        print("      docker compose -f docker/docker-compose.yaml ps")
        return 1
    return 0


if __name__ == "__main__":
    _force_utf8_stdout()
    sys.exit(asyncio.run(main()))
