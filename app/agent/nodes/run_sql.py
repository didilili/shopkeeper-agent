"""
SQL 执行节点

负责执行最终 SQL，并记录查询结果。
它是当前 SQL 闭环的结束节点，执行完成后流程进入 END。
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.observability.logging import audit_event, log_failure, sql_fingerprint


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """执行 SQL 并产出最终问数结果"""

    writer = runtime.stream_writer
    step = "执行SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # 这里拿到的可能是 generate_sql 直接通过校验的 SQL，也可能是 correct_sql 覆盖后的 SQL
        sql = state["sql"]
        allowed_tables = {table["name"] for table in state["table_infos"]}
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        # 真实数据库访问统一封装在仓储层，节点只负责从状态取 SQL 并触发执行
        result = await dw_mysql_repository.run(
            sql,
            allowed_tables=allowed_tables,
        )
        audit_event(
            "sql_executed",
            component="sql",
            operation="run",
            sql_fingerprint=sql_fingerprint(sql),
            row_count=len(result),
        )
        writer({"type": "progress", "step": step, "status": "success"})
        writer({"type": "result", "data": result})

    except Exception as e:
        log_failure("agent", "run_sql", e)
        writer({"type": "progress", "step": step, "status": "error"})
        raise
