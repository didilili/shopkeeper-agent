"""
元数据库 MySQL 仓储模块

封装对元数据库 meta 的读写操作，当前代码还处在元数据知识库构建的早期阶段，
所以这里先保留统一的仓储入口，
后续 table_info column_info metric_info 和 column_metric 的写入逻辑都会逐步沉淀到这里
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper


class MetaMySQLRepository:
    def __init__(self, session: AsyncSession):
        # 外部负责创建和关闭 session
        # 仓储层只关注具体的数据访问逻辑
        self.session = session

    def save_table_infos(self, table_infos: list[TableInfo]):
        self.session.add_all(
            [TableInfoMapper.to_model(table_info) for table_info in table_infos]
        )

    def save_column_infos(self, column_infos: list[ColumnInfo]):
        self.session.add_all(
            [ColumnInfoMapper.to_model(column_info) for column_info in column_infos]
        )
