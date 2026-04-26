"""
指标过滤节点

负责从召回指标中筛选出和用户问题最相关的指标
这一步会为 SQL 生成提供更明确的计算口径和依赖字段
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """根据用户问题和召回结果筛选候选指标"""

    writer = runtime.stream_writer
    # 指标过滤结果后续会和表结构信息一起组成 SQL 生成上下文
    writer("过滤指标信息")
    import asyncio

    # 当前章节先保留占位逻辑，后续会结合 LLM 或规则完成筛选
    await asyncio.sleep(0.5)
