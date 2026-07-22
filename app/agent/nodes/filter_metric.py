"""
指标信息过滤节点

负责从合并后的候选指标中筛选出当前问题真正需要的指标
过滤后的指标会进入 SQL 生成上下文，帮助模型遵循正确的业务口径
"""

import yaml
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, MetricInfoState
from app.core.log import logger
from app.prompt.factory import build_prompt_chain
from app.prompt.validators import validate_name_selection


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """根据用户问题裁剪候选指标上下文"""

    writer = runtime.stream_writer
    step = "过滤指标信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        metric_infos: list[MetricInfoState] = state["metric_infos"]

        # metric_infos 转成 YAML 后作为候选项交给模型，模型只需要返回被选中的指标名称
        chain = build_prompt_chain("filter_metric_info")

        result = await chain.ainvoke(
            {
                "query": query,
                "metric_infos": yaml.dump(
                    metric_infos, allow_unicode=True, sort_keys=False
                ),
            }
        )
        validate_name_selection(result, metric_infos, label="指标")
        # 用模型返回的指标名称过滤原始结构，保留描述 依赖字段 别名等完整上下文
        filtered_metric_infos = [
            metric_info for metric_info in metric_infos if metric_info["name"] in result
        ]

        logger.info(
            f"过滤后的指标信息：{[filtered_metric_info['name'] for filtered_metric_info in filtered_metric_infos]}"
        )

        writer({"type": "progress", "step": step, "status": "success"})
        return {"metric_infos": filtered_metric_infos}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
