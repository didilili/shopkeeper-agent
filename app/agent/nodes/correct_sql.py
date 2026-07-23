"""
SQL 修正节点

负责在 SQL 校验失败后，结合原问题 原 SQL 数据库错误和完整上下文做最小必要修正
只有 validate_sql 写入错误信息时，LangGraph 才会进入这个分支
"""

import yaml
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.config.app_config import app_config
from app.observability.logging import audit_event, log_failure, sql_fingerprint
from app.observability.metrics import SQL_CORRECTIONS
from app.prompt.factory import build_prompt_chain


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """根据校验错误修正 SQL"""

    writer = runtime.stream_writer
    step = "校正SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # 校正 SQL 仍然需要完整上下文，避免模型只根据报错修语法却改丢业务语义
        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]
        query = state["query"]

        # sql 是待修正的候选 SQL，error 是数据库 explain 返回的具体错误信息
        sql = state["sql"]
        error = state["error"]

        chain = build_prompt_chain("correct_sql")

        result = await chain.ainvoke(
            {
                # 与生成节点保持一致，用 YAML 向模型提供稳定 可读的结构化上下文
                "table_infos": yaml.dump(
                    table_infos, allow_unicode=True, sort_keys=False
                ),
                "metric_infos": yaml.dump(
                    metric_infos, allow_unicode=True, sort_keys=False
                ),
                "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
                "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
                "query": query,
                "sql": sql,
                "error": error,
            }
        )

        if (
            app_config.observability.enabled
            and app_config.observability.metrics_enabled
        ):
            SQL_CORRECTIONS.labels("generated").inc()
        audit_event(
            "sql_corrected",
            component="sql",
            operation="correct",
            sql_fingerprint=sql_fingerprint(result),
            sql_length=len(result),
        )
        writer({"type": "progress", "step": step, "status": "success"})
        return {
            "sql": result,
            "correction_attempts": state.get("correction_attempts", 0) + 1,
        }
    except Exception as e:
        if (
            app_config.observability.enabled
            and app_config.observability.metrics_enabled
        ):
            SQL_CORRECTIONS.labels("error").inc()
        log_failure("agent", "correct_sql", e)
        writer({"type": "progress", "step": step, "status": "error"})
        raise
