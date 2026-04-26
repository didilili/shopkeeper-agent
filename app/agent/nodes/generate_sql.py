"""
SQL 生成节点

负责根据用户问题和前面整理出的字段 指标 表结构上下文生成 SQL
这是自然语言问数链路里从“理解问题”走向“可执行查询”的关键一步
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """基于已检索和过滤的上下文生成 SQL"""

    writer = runtime.stream_writer
    # 后续真实实现会调用 llm，把 SQL 写回 DataAgentState
    writer("生成SQL")
    import asyncio

    # 当前章节先保留占位逻辑，后续替换为 LLM 生成 SQL
    await asyncio.sleep(0.5)
