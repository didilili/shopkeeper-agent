"""
数仓 MySQL 仓储模块

封装对教学数仓库 dw 的查询操作，当前重点服务于元数据知识构建流程，
用于补齐字段类型和字段示例值这类需要从真实表结构和真实数据中读取的信息
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        # Repository 本身不管理连接生命周期
        # 只复用外部传入的 AsyncSession 执行查询
        self.session = session

    async def get_column_types(self, table_name) -> dict[str, str]:
        # 通过 show columns 直接读取当前表的字段定义
        # 返回结果最终整理成 字段名 -> 字段类型 的映射
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        result_dict = result.mappings().fetchall()

        return {row["Field"]: row["Type"] for row in result_dict}
        # {order_id:varchar(30),customer_id:varchar(30)}

    async def get_column_values(self, table_name, column_name, limit=10):
        # 读取字段的去重示例值
        # 这些值后续会写入元数据库中的 examples 字段
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return [row[0] for row in result.fetchall()]
