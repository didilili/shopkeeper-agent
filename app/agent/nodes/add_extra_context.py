"""
额外上下文补全节点

负责在 SQL 生成前补齐不来自召回结果、但模型必须知道的运行环境信息
当前包括日期信息和数据库方言/版本，后续可继续扩展权限、租户、时区等上下文
"""

from datetime import date

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState, DBInfoState
from app.observability.logging import audit_event, log_failure


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """补齐 SQL 生成所需的日期和数据库环境信息"""

    writer = runtime.stream_writer
    step = "添加额外上下文"
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        # 当前日期信息会帮助模型处理“今天 本月 本季度 最近 N 天”等相对时间表达
        today = date.today()
        date_str = today.strftime("%Y-%m-%d")
        weekday = today.strftime("%A")
        quarter = f"Q{(today.month - 1) // 3 + 1}"
        date_info = DateInfoState(date=date_str, weekday=weekday, quarter=quarter)

        # 数据库方言和版本会影响函数名 日期运算 limit 语法等 SQL 细节
        db = await dw_mysql_repository.get_db_info()
        db_info = DBInfoState(**db)
        audit_event(
            "context_enriched",
            component="agent",
            operation="add_extra_context",
            dialect=db_info["dialect"],
        )

        writer({"type": "progress", "step": step, "status": "success"})
        return {"date_info": date_info, "db_info": db_info}

    except Exception as e:
        log_failure("agent", "add_extra_context", e)
        writer({"type": "progress", "step": step, "status": "error"})
        raise
