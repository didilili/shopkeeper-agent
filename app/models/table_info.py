"""
table_info ORM 模型模块

定义元数据库中 table_info 表对应的 ORM 模型，
它负责保存纳入元数据知识库的表级信息，比如表名 表角色 和表说明
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TableInfoMySQL(Base):
    # 对应元数据库中的 table_info 表
    __tablename__ = "table_info"

    # id 直接使用表名
    # 在当前项目里它既是主键 也是后续字段归属关系里的表标识
    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="表编号")
    name: Mapped[str | None] = mapped_column(String(128), comment="表名称")
    role: Mapped[str | None] = mapped_column(String(32), comment="表类型(fact/dim)")
    description: Mapped[str | None] = mapped_column(Text, comment="表描述")
