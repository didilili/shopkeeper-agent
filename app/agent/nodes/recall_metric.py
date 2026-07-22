"""
指标召回节点

负责根据用户问题从指标向量知识库中召回候选指标
它帮助 Agent 把“销售额 转化率 客单价”等业务表达映射到已定义指标
实现路径和字段召回类似：关键词扩展 -> Embedding -> Qdrant 相似度检索 -> MetricInfo 去重
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.conf.app_config import app_config
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.factory import build_prompt_chain
from app.retrieval.service import retrieve_vector_candidates


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回和用户问题语义相关的业务指标"""

    writer = runtime.stream_writer
    step = "召回指标信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # query 用于让 LLM 生成指标层检索词，keywords 来自上游的通用关键词抽取
        query = state["query"]
        keywords = state["keywords"]
        # 指标召回使用向量检索，需要 Embedding 客户端和指标 Qdrant 仓储配合
        embedding_client = runtime.context["embedding_client"]
        metric_qdrant_repository = runtime.context["metric_qdrant_repository"]

        # 用 LLM 把用户问法扩展成“指标概念”列表，例如“销售总额”可扩展出“GMV”“成交额”
        chain = build_prompt_chain("extend_keywords_for_metric_recall")

        result = await chain.ainvoke({"query": query})

        ranked_candidates = await retrieve_vector_candidates(
            [*keywords, *result],
            embedding_client=embedding_client,
            search=metric_qdrant_repository.search,
            config=app_config.retrieval.metric,
            max_concurrency=app_config.retrieval.max_concurrency,
            key=lambda item: item.id,
            searchable_terms=lambda item: [item.name, *item.alias],
        )
        retrieved_metric_infos: list[MetricInfo] = [
            candidate.item for candidate in ranked_candidates
        ]
        logger.info(
            "指标融合排序：{}",
            [
                {
                    "id": candidate.item.id,
                    "score": round(candidate.score, 4),
                    "queries": candidate.matched_queries,
                }
                for candidate in ranked_candidates
            ],
        )
        writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_metric_infos": retrieved_metric_infos}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
