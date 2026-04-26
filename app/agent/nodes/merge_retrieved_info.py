"""
召回信息合并节点

负责把字段 字段取值和指标三路召回结果聚合到统一状态中
后续过滤节点不再关心信息来自哪个检索分支，只处理合并后的候选上下文
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def merge_retrieved_info(
    state: DataAgentState, runtime: Runtime[DataAgentContext]
):
    """合并多路召回结果，为后续过滤和 SQL 生成做准备"""

    writer = runtime.stream_writer
    # 这里是并行召回分支汇合点，适合做去重 排序和结构化整理
    writer("合并召回信息")
    import asyncio

    # 当前章节先保留占位逻辑，后续会合并字段 值 指标等中间结果
    await asyncio.sleep(0.5)
