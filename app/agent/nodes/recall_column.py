"""
字段召回节点

负责根据关键词从字段向量知识库中召回候选字段
它解决的是“用户问题可能对应哪些数据库字段”的问题
本章的主线是：关键词扩展 -> Embedding -> Qdrant 相似度检索 -> ColumnInfo 去重
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.config.app_config import app_config
from app.entities.column_info import ColumnInfo
from app.observability.logging import audit_event, log_failure
from app.prompt.factory import build_prompt_chain
from app.retrieval.service import retrieve_vector_candidates


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回和用户问题语义相关的字段元数据"""

    writer = runtime.stream_writer
    step = "召回字段信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # state 保存图内业务中间结果：原始问题和上游抽取出的关键词
        keywords = state["keywords"]
        query = state["query"]
        # context 保存外部运行时工具：向量仓储和 Embedding 客户端
        column_qdrant_repository = runtime.context["column_qdrant_repository"]
        embedding_client = runtime.context["embedding_client"]

        # 用 LLM 把用户问法扩展成“字段语义”列表，例如“销售总额”可扩展出“销售金额”
        chain = build_prompt_chain("extend_keywords_for_column_recall")

        result = await chain.ainvoke({"query": query})

        ranked_candidates = await retrieve_vector_candidates(
            [*keywords, *result],
            embedding_client=embedding_client,
            search=column_qdrant_repository.search,
            config=app_config.retrieval.column,
            max_concurrency=app_config.retrieval.max_concurrency,
            max_queries=app_config.retrieval.max_queries,
            key=lambda item: item.id,
            searchable_terms=lambda item: [item.name, *item.alias],
        )
        retrieved_column_infos: list[ColumnInfo] = [
            candidate.item for candidate in ranked_candidates
        ]
        audit_event(
            "retrieval_completed",
            component="retrieval",
            operation="recall_column",
            candidate_count=len(ranked_candidates),
        )

        writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_column_infos": retrieved_column_infos}
    except Exception as e:
        log_failure("agent", "recall_column", e)
        writer({"type": "progress", "step": step, "status": "error"})
        raise
