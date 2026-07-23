"""
表信息过滤节点

负责在合并后的候选表结构中筛选出当前问题真正需要的表和字段
这里让大模型只返回“保留哪些表和字段”的选择结果，真正的结构裁剪仍由程序完成
"""

import yaml
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState
from app.observability.logging import audit_event, log_failure
from app.prompt.factory import build_prompt_chain
from app.prompt.validators import validate_table_selection


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """根据用户问题裁剪候选表结构上下文"""

    writer = runtime.stream_writer
    step = "过滤表信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        table_infos: list[TableInfoState] = state["table_infos"]

        # table_infos 是嵌套结构，转成 YAML 后更适合放进提示词，也保留中文字段说明
        chain = build_prompt_chain("filter_table_info")

        result = await chain.ainvoke(
            {
                "query": query,
                "table_infos": yaml.dump(
                    table_infos, allow_unicode=True, sort_keys=False
                ),
            }
        )
        validate_table_selection(result, table_infos)
        # 模型只负责选择，程序根据选择结果从原始 TableInfoState 中裁剪，避免模型重写复杂结构出错
        filtered_table_infos: list[TableInfoState] = []
        for table_info in table_infos:
            if table_info["name"] in result:
                filtered_table_infos.append(
                    {
                        **table_info,
                        "columns": [
                            column_info
                            for column_info in table_info["columns"]
                            if column_info["name"] in result[table_info["name"]]
                        ],
                    }
                )

        audit_event(
            "context_filtered",
            component="agent",
            operation="filter_table",
            selected_count=len(filtered_table_infos),
        )
        writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": filtered_table_infos}

    except Exception as e:
        log_failure("agent", "filter_table", e)
        writer({"type": "progress", "step": step, "status": "error"})
        raise
