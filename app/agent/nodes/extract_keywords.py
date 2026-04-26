"""
关键词抽取节点

负责从用户自然语言问题中识别检索线索
后续字段召回 字段取值召回和指标召回都会基于这些关键词展开
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """抽取用户问题中的关键词，并通过流式输出反馈当前进度"""

    writer = runtime.stream_writer
    # stream_writer 会把节点进度推送给图调用方，方便调试或前端展示执行过程
    writer("抽取关键词")
    import asyncio

    # 当前章节先用 sleep 模拟真实节点耗时，后续会替换为 LLM 或规则抽取逻辑
    await asyncio.sleep(0.5)
