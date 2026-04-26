"""
SQL 校验节点

负责在执行前检查生成 SQL 是否可用
如果校验发现错误，会把错误信息写入 state，让图进入 SQL 修正分支
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """校验 SQL，并返回 error 字段控制后续条件分支"""

    writer = runtime.stream_writer
    # 校验节点的返回值会更新到 DataAgentState 中，供 graph.py 的条件边读取
    writer("校验SQL")
    import asyncio

    # 当前章节先模拟校验通过，后续会替换为真实 SQL 解析或试运行逻辑
    await asyncio.sleep(0.5)
    return {"error": None}
