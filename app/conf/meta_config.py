"""
元数据知识构建配置模块

定义 meta_config.yaml 在程序中的结构，这份配置不描述底层基础设施，
而是描述一次元数据知识构建要处理哪些表 哪些字段 和哪些指标，脚本入口会先读取 YAML，
再把内容转换成这里定义的 dataclass 对象，后续服务层就可以按统一结构完成元数据同步
"""

from dataclasses import dataclass
from typing import Optional


# 单个字段配置
# 描述字段的业务角色 说明 别名以及是否同步字段值
@dataclass
class ColumnConfig:
    name: str
    role: str
    description: str
    alias: list[str]
    sync: bool


# 单张表配置
# 一张表下面会继续声明需要纳入知识库的字段列表
@dataclass
class TableConfig:
    name: str
    role: str
    description: str
    columns: list[ColumnConfig]


# 指标配置
# relevant_columns 用来描述指标和底层字段之间的关联关系
@dataclass
class MetricConfig:
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


# 元数据知识构建总配置
# tables 和 metrics 都允许为空 便于分阶段只构建其中一部分
@dataclass
class MetaConfig:
    tables: Optional[list[TableConfig]] = None
    metrics: Optional[list[MetricConfig]] = None
