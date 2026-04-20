"""
MySQL 客户端管理模块

统一创建和管理项目中的异步 MySQL 客户端，当前项目会同时连接两套 MySQL，
一套是保存结构化元数据的 meta 数据库，一套是模拟教学数仓的 dw 数据库，
模块对外提供可复用的客户端管理器和 session 工厂，
方便脚本入口 服务层和仓储层按统一方式访问数据库
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.conf.app_config import DBConfig, app_config


class MySQLClientManager:
    def __init__(self, config: DBConfig):
        # Engine 是数据库连接层核心对象，底层会维护连接池
        self.engine: AsyncEngine | None = None
        # session_factory 用来按需创建新的 AsyncSession
        self.session_factory = None
        # 保存数据库配置，后面拼接连接地址要用
        self.config = config

    def _get_url(self):
        # mysql+asyncmy 表示：连接 MySQL，并使用 asyncmy 作为异步驱动
        return f"mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}?charset=utf8mb4"

    def init(self):
        # 创建异步 Engine，相当于先把“数据库连接能力”准备好
        self.engine = create_async_engine(
            self._get_url(), pool_size=10, pool_pre_ping=True
        )
        # 基于 Engine 创建 Session 工厂，后面真正查库时再拿 session
        self.session_factory = async_sessionmaker(
            self.engine, autoflush=True, expire_on_commit=False
        )

    async def close(self):
        # 程序结束时释放连接池资源
        await self.engine.dispose()


# 一套连元数据库，一套连数仓模拟库
# 后续由不同 repository 按职责分别使用
meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)

if __name__ == "__main__":
    # 这里演示的是数仓库查询，所以先初始化 dw 这一套客户端
    dw_mysql_client_manager.init()

    async def test():
        # 通过 session_factory 创建一次数据库会话
        async with dw_mysql_client_manager.session_factory() as session:
            sql = "select * from fact_order limit 10"
            # text(sql) 表示把原生 SQL 语句交给 SQLAlchemy 执行
            result = await session.execute(text(sql))

            # mappings().fetchall() 会把结果转成“按列名访问”的行对象列表
            rows = result.mappings().fetchall()

            # 下面三行只是为了帮助观察返回结果的结构
            print(type(rows))
            print(type(rows[0]))
            print(rows[0]["order_id"])

    asyncio.run(test())
