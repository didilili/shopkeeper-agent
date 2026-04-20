"""
column_info ORM 模型模块

定义元数据库中 column_info 表对应的 ORM 模型，
它负责保存字段级元数据，包括字段类型 字段角色 示例值 说明 别名 以及所属表
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base


class ColumnInfoMySQL(Base):
    # 对应元数据库中的 column_info 表
    __tablename__ = "column_info"

    # id 采用 表名.字段名 的组合形式
    # 这样在整个数仓范围内更容易保证唯一性
    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="列编号")
    name: Mapped[str | None] = mapped_column(String(128), comment="列名称")
    type: Mapped[str | None] = mapped_column(String(64), comment="数据类型")
    role: Mapped[str | None] = mapped_column(
        String(32), comment="列类型(primary_key,foreign_key,measure,dimension)"
    )
    # examples 和 alias 都使用 JSON 存储
    # 方便保存列表结构而不是再拆独立子表
    examples: Mapped[dict | list | None] = mapped_column(JSON, comment="数据示例")
    description: Mapped[str | None] = mapped_column(Text, comment="列描述")
    alias: Mapped[dict | list | None] = mapped_column(JSON, comment="列别名")
    table_id: Mapped[str | None] = mapped_column(String(64), comment="所属表编号")
