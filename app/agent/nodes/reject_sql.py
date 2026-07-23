"""SQL 多次校验失败后的终止节点。"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.config.app_config import app_config
from app.observability.logging import audit_event
from app.observability.metrics import SQL_CORRECTIONS


class SQLValidationError(RuntimeError):
    """候选 SQL 在有限修正后仍无法通过校验。"""


async def reject_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """终止不可信 SQL，确保不会进入执行节点。"""

    step = "拒绝SQL"
    attempts = state.get("correction_attempts", 0)
    if app_config.observability.enabled and app_config.observability.metrics_enabled:
        SQL_CORRECTIONS.labels("rejected").inc()
    audit_event(
        "sql_rejected",
        level="ERROR",
        component="sql",
        operation="reject",
        correction_attempts=attempts,
    )
    runtime.stream_writer({"type": "progress", "step": step, "status": "error"})
    raise SQLValidationError(f"SQL 在 {attempts} 次修正后仍未通过安全校验")
