"""
元数据知识构建服务模块

负责组织元数据知识库构建的核心业务流程，位于脚本入口和仓储层之间，
一方面接收配置文件，另一方面协调元数据库和数仓查询仓储，当前这版代码重点完成表信息和字段信息的整理流程，
后续还会继续扩展到向量索引 全文索引和指标信息构建
"""

from pathlib import Path

from omegaconf import OmegaConf

from app.conf.meta_config import MetaConfig
from app.models.column_info import ColumnInfoMySQL
from app.models.table_info import TableInfoMySQL
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

        # 2. 根据配置文件同步指定的表和字段信息
        if meta_config.tables:
            table_infos: list[TableInfoMySQL] = []
            column_infos: list[ColumnInfoMySQL] = []
            # 2.1 先把配置里的表定义和数仓中的真实字段信息整理出来
            #     形成后续可直接入库和建索引的标准化对象
            for table in meta_config.tables:
                # table -> table_info
                # 当前表级信息主要来自配置文件中的 name 和 description
                table_info = TableInfoMySQL(
                    id=table.name, name=table.name, description=table.description
                )
                table_infos.append(table_info)

                # 从数仓读取当前表的字段类型
                # 这部分信息不是手写配置 而是来自真实表结构
                column_types = await self.dw_mysql_repository.get_column_types(
                    table.name
                )

                for column in table.columns:
                    # 查询字段取值示例
                    # 示例值既能帮助后续理解字段语义
                    # 也能作为元数据库中的 examples 字段落盘
                    column_values = await self.dw_mysql_repository.get_column_values(
                        table.name, column.name
                    )
                    # column -> column_info
                    # 字段说明 角色 别名来自配置
                    # 字段类型和示例值来自数仓查询
                    column_info = ColumnInfoMySQL(
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

            print(table_infos)
            print("=" * 100)
            print(column_infos)

            # 2.2 对字段信息建立向量索引
            #     后续会把 column_infos 写入 Qdrant

            # 2.3 对指定的维度字段取值建立全文索引
            #     后续会按配置把需要 sync 的字段值写入 Elasticsearch

        # 3. 根据配置文件同步指定的指标信息
        if meta_config.metrics:
            pass
            # 3.1 将指标信息保存 meta 数据库中

            # 3.2 对指标信息建立向量索引
