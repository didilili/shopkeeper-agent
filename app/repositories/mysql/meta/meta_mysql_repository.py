"""
元数据库 MySQL 仓储模块

封装对元数据库 meta 的读写操作，当前代码还处在元数据知识库构建的早期阶段，
所以这里先保留统一的仓储入口，
后续 table_info column_info metric_info 和 column_metric 的写入逻辑都会逐步沉淀到这里
"""

from sqlalchemy.ext.asyncio import AsyncSession


class MetaMySQLRepository:
    def __init__(self, session: AsyncSession):
        # 外部负责创建和关闭 session
        # 仓储层只关注具体的数据访问逻辑
        self.session = session
