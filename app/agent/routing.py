"""LangGraph 条件边使用的纯路由函数。"""

from typing import Literal

from app.agent.state import DataAgentState

SQLRoute = Literal["run_sql", "correct_sql", "reject_sql"]


def route_after_sql_validation(
    state: DataAgentState, *, max_correction_attempts: int
) -> SQLRoute:
    """校验通过则执行，否则在修正预算内重试，耗尽后拒绝。"""

    if state["error"] is None:
        return "run_sql"
    if state.get("correction_attempts", 0) < max_correction_attempts:
        return "correct_sql"
    return "reject_sql"
