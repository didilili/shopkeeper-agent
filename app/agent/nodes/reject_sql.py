"""SQL 多次校验失败后的终止节点。"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


class SQLValidationError(RuntimeError):
    """候选 SQL 在有限修正后仍无法通过校验。"""


async def reject_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """终止不可信 SQL，确保不会进入执行节点。"""

    step = "拒绝SQL"
    attempts = state.get("correction_attempts", 0)
    logger.error("SQL 在 {} 次修正后仍未通过校验：{}", attempts, state["error"])
    runtime.stream_writer({"type": "progress", "step": step, "status": "error"})
    raise SQLValidationError(f"SQL 在 {attempts} 次修正后仍未通过安全校验")
