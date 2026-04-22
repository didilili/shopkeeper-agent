"""
数仓 MySQL 仓储模块

封装对教学数仓库 dw 的查询操作。

当前先保留仓储对象本身和 session 依赖，
让脚本入口与服务层的依赖注入链路保持完整。

字段类型查询、字段示例值查询，以及后续 SQL 校验和执行等逻辑，
会在后续继续补进来。
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name) -> dict[str, str]:
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        result_dict = result.mappings().fetchall()
        # [{Field:order_id,Type:varchar(30),Null:No},{Field:customer_id,Type:varchar(20),Null:YES}]

        return {row["Field"]: row["Type"] for row in result_dict}
        # {order_id:varchar(30),customer_id:varchar(30)}

    async def get_column_values(self, table_name, column_name, limit=10):
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return [row[0] for row in result.fetchall()]
