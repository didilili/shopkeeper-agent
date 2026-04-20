"""
元数据知识库构建脚本入口

相当于构建流程的 controller 层，负责接收命令行参数 初始化客户端 创建仓储和服务对象，
再把真正的构建任务调度到 MetaKnowledgeService，它本身不承载复杂业务细节，
主要目标是把整条构建链路稳定地启动起来
"""

import argparse
import asyncio
from pathlib import Path

from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


async def build(config_path: Path):
    # 整条构建链路会同时访问两套 MySQL
    # meta 用来写结构化元数据
    # dw 用来读取真实表结构和字段示例值
    # 1. 初始化两个 MySQL 客户端：
    #    一个连元数据库，一个连数仓模拟库
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()

    # 2. 打开两个异步 Session，分别供两个 repository 使用
    async with (
        meta_mysql_client_manager.session_factory() as meta_session,
        dw_mysql_client_manager.session_factory() as dw_session,
    ):
        # 3. 创建 repository 对象
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)

        # 4. 创建 service 对象，并把 repository 注入进去
        meta_knowledge_service = MetaKnowledgeService(
            meta_mysql_repository,
            dw_mysql_repository,
        )

        # 5. 真正进入服务层的构建逻辑
        await meta_knowledge_service.build(config_path)

    # 6. 结束后关闭客户端连接
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()


if __name__ == "__main__":
    # 7. 解析命令行参数
    #    由外部决定本次构建使用哪份配置文件
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--conf")
    args = parser.parse_args()

    # 8. 将字符串路径转成 Path
    #    再启动异步 build
    asyncio.run(build(Path(args.conf)))
