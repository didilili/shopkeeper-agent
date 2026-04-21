"""
数仓 MySQL 仓储模块

封装对教学数仓库 dw 的查询操作。

当前先保留仓储对象本身和 session 依赖，
让脚本入口与服务层的依赖注入链路保持完整。

字段类型查询、字段示例值查询，以及后续 SQL 校验和执行等逻辑，
会在后续继续补进来。
"""

from sqlalchemy.ext.asyncio import AsyncSession


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        # Repository 本身不管理连接生命周期
        # 只复用外部传入的 AsyncSession 执行查询
        self.session = session
