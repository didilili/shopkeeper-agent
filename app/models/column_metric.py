"""
column_metric ORM 模型模块

定义元数据库中 column_metric 表对应的 ORM 模型，
它负责保存字段和指标之间的关联关系，方便后续从字段追踪相关指标，或者从指标回查依赖字段
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ColumnMetricMySQL(Base):
    # 对应元数据库中的 column_metric 关系表
    __tablename__ = "column_metric"

    # 这里采用联合主键
    # 表示同一对 字段 指标 关系只允许出现一次
    column_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="列编号"
    )
    metric_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="指标编号"
    )
