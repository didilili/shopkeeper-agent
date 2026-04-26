"""
表过滤节点

负责从召回字段对应的表中筛选出真正需要参与 SQL 生成的表
这一步可以减少模型面对的表结构数量，降低生成错误 SQL 的概率
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """根据召回信息筛选候选数据表"""

    writer = runtime.stream_writer
    # 表过滤和指标过滤可以并行进行，最后一起汇入上下文补充节点
    writer("过滤表信息")
    import asyncio

    # 当前章节先保留占位逻辑，后续会结合召回字段和表元数据筛选
    await asyncio.sleep(0.5)
