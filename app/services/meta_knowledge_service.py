"""
元数据知识构建服务模块

负责组织元数据知识库构建的核心业务流程，位于脚本入口和仓储层之间，
一方面接收配置文件，另一方面协调元数据库和数仓查询仓储。
当前实现先保留配置加载与总编排骨架，具体的表字段入库、向量索引、
全文索引和指标构建逻辑后续再逐步补充。
"""

from pathlib import Path

from omegaconf import OmegaConf

from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository


class MetaKnowledgeService:
    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
    ):
        # meta repository 负责结构化元数据的落库
        self.meta_mysql_repository: MetaMySQLRepository = meta_mysql_repository
        # dw repository 负责到教学数仓中读取真实表结构和示例值
        self.dw_mysql_repository: DWMySQLRepository = dw_mysql_repository

    async def build(self, config_path: Path):
        # 1. 读取配置文件并转换成结构化配置对象
        #    后续流程统一围绕 MetaConfig 展开
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

        # 2. 根据配置文件判断后续要进入哪条构建链路
        if meta_config.tables:
            table_infos: list[TableInfo] = []
            column_infos: list[ColumnInfo] = []
            for table in meta_config.tables:
                # table -> table_info
                table_info = TableInfo(
                    id=table.name,
                    name=table.name,
                    role=table.role,
                    description=table.description,
                )
                table_infos.append(table_info)

            # 查询字段类型
            column_types = await self.dw_mysql_repository.get_column_types(table.name)

            for column in table.columns:
                # 查询字段取值示例
                column_values = await self.dw_mysql_repository.get_column_values(
                    table.name, column.name
                )
                # column -> column_info
                column_info = ColumnInfo(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_types[column.name],
                    role=column.role,
                    examples=column_values,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                )
                column_infos.append(column_info)
                # self.meta_mysql_repository.add(table_info)

        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_table_infos(table_infos)
            self.meta_mysql_repository.save_column_infos(column_infos)

            print(table_infos)
            print(column_infos)
        # 3. 根据配置文件同步指定的指标信息
        if meta_config.metrics:
            logger.info("检测到 metrics 配置，指标链路入口已准备就绪")
            logger.info("指标入库与指标向量索引逻辑后续继续补充")

        logger.info("当前阶段完成：配置加载与元数据知识库构建骨架准备")
