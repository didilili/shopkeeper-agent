"""
字段取值召回节点

负责从字段值全文索引中召回候选取值
当用户问题里出现店铺名 类目名 地区名等业务值时，这一步可以帮助定位真实字段和值
实现路径和字段/指标召回不同：关键词扩展 -> Elasticsearch 全文检索 -> ValueInfo 去重
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.conf.app_config import app_config
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.factory import build_prompt_chain
from app.retrieval.service import retrieve_text_candidates


async def recall_value(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回和用户问题相关的字段取值"""

    writer = runtime.stream_writer
    step = "召回字段取值"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # query 用于让 LLM 生成字段值层面的检索词，keywords 来自上游通用关键词抽取
        query = state["query"]
        keywords = state["keywords"]
        # 字段取值更关注真实文本命中，因此这里走 Elasticsearch，而不是向量检索
        value_es_repository = runtime.context["value_es_repository"]

        # 用 LLM 把用户问法扩展成“可能出现在字段值里的词”
        # 例如“华北地区”可以补充出“华北”，避免 SQL 条件值和真实存储值不一致
        chain = build_prompt_chain("extend_keywords_for_value_recall")

        result = await chain.ainvoke({"query": query})

        ranked_candidates = await retrieve_text_candidates(
            [*keywords, *result],
            search=value_es_repository.search,
            config=app_config.retrieval.value,
            max_concurrency=app_config.retrieval.max_concurrency,
            key=lambda item: item.id,
            searchable_terms=lambda item: [item.value],
        )
        retrieved_value_infos: list[ValueInfo] = [
            candidate.item for candidate in ranked_candidates
        ]
        logger.info(
            "字段值融合排序：{}",
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
        return {"retrieved_value_infos": retrieved_value_infos}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
