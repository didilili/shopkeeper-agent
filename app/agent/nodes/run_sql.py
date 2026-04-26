"""
SQL 执行节点

负责执行最终确认可用的 SQL，并把查询结果写回状态
它是本章 Agent 图的结束节点，执行完成后流程进入 END
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """执行 SQL 并产出最终问数结果"""

    writer = runtime.stream_writer
    # 后续真实实现会通过数仓 Repository 执行 SQL，并把结果写回 DataAgentState
    writer("执行SQL")
    import asyncio

    # 当前章节先保留占位逻辑，后续替换为真实数据库查询
    await asyncio.sleep(0.5)
