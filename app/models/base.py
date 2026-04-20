"""
ORM 基类模块

定义项目中所有 SQLAlchemy ORM 模型共享的基类，
后续 table_info column_info metric_info 和 column_metric 都会继承这里的 Base
"""

from sqlalchemy.orm import DeclarativeBase


# 统一的声明式基类
# 方便 SQLAlchemy 收集所有模型定义并生成映射元数据
class Base(DeclarativeBase):
    pass
