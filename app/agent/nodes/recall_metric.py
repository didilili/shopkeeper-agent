"""
指标召回节点

负责根据用户问题从指标向量知识库中召回候选指标
它帮助 Agent 把“销售额 转化率 客单价”等业务表达映射到已定义指标
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回和用户问题语义相关的业务指标"""

    writer = runtime.stream_writer
    # 指标召回和字段召回并行执行，输出进度可以看清图的运行顺序
    writer("召回指标信息")
    import asyncio

    # 当前章节先保留占位逻辑，后续接入 MetricQdrantRepository 查询
    await asyncio.sleep(0.5)
