"""
数仓 MySQL 仓储

这一层对应文档里的 DW Repository，职责是到真实数仓中补齐配置文件里
没有显式维护的信息，例如字段类型和字段示例值。Service 层只关心
“需要哪些信息”，具体怎样查数仓由仓储层统一封装
SQL 生成闭环中的数据库环境读取 SQL 校验和最终查询执行也集中放在这里
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.app_config import SQLExecutionConfig, app_config
from app.core.log import logger
from app.observability.instrumentation import observe_external
from app.observability.metrics import SQL_RESULT_ROWS
from app.security.sql_guard import SQLGuard


class DWMySQLRepository:
    """负责查询数仓真实表结构和字段样例值"""

    def __init__(
        self,
        session: AsyncSession,
        execution_config: SQLExecutionConfig | None = None,
    ):
        self.session = session
        self.execution_config = execution_config or app_config.sql_execution
        self.sql_guard = SQLGuard(
            max_sql_length=self.execution_config.max_sql_length,
            allowed_schema=app_config.db_dw.database,
        )

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        """查询整张表的字段类型，作为 ColumnInfo.type 的真实来源"""
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        result_dict = result.mappings().fetchall()
        return {row["Field"]: row["Type"] for row in result_dict}

    async def get_column_values(
        self, table_name: str, column_name: str, limit: int = 10
    ) -> list:
        """抽样查询字段示例值，供元数据入库和后续检索链路复用"""
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return [row[0] for row in result.fetchall()]

    async def get_db_info(self):
        """读取当前数仓数据库的方言和版本，供 SQL 生成提示词使用"""

        sql = "select version()"
        result = await self.session.execute(text(sql))
        version = result.scalar()

        # dialect 来自 SQLAlchemy 当前绑定的数据库方言，例如 mysql
        dialect = self.session.bind.dialect.name
        return {"dialect": dialect, "version": version}

    async def validate(self, sql: str, *, allowed_tables: set[str] | None = None):
        """先执行安全审计，再用 EXPLAIN 检查语法、表名和字段名。"""

        guarded_sql = self.sql_guard.validate(sql, allowed_tables=allowed_tables)
        async with observe_external("dw_mysql", "validate_sql"):
            async with asyncio.timeout(self.execution_config.query_timeout_seconds):
                await self.session.execute(text(f"explain {guarded_sql}"))

    async def run(
        self, sql: str, *, allowed_tables: set[str] | None = None
    ) -> list[dict]:
        """再次执行安全审计，并限制等待时间和返回到应用层的数据量。"""

        guarded_sql = self.sql_guard.validate(sql, allowed_tables=allowed_tables)
        async with observe_external("dw_mysql", "run_sql"):
            async with asyncio.timeout(self.execution_config.query_timeout_seconds):
                result = await self.session.execute(text(guarded_sql))

        rows = result.mappings().fetchmany(self.execution_config.max_result_rows + 1)
        if len(rows) > self.execution_config.max_result_rows:
            logger.warning(
                "SQL 结果超过最大返回行数 {}，已截断",
                self.execution_config.max_result_rows,
            )
            rows = rows[: self.execution_config.max_result_rows]
        if (
            app_config.observability.enabled
            and app_config.observability.metrics_enabled
        ):
            SQL_RESULT_ROWS.observe(len(rows))
        return [dict(row) for row in rows]
