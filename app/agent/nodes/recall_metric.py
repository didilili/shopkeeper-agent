"""
指标召回节点

负责根据用户问题从指标向量知识库中召回候选指标
它帮助 Agent 把“销售额 转化率 客单价”等业务表达映射到已定义指标
实现路径和字段召回类似：关键词扩展 -> Embedding -> Qdrant 相似度检索 -> MetricInfo 去重
"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回和用户问题语义相关的业务指标"""

    writer = runtime.stream_writer
    writer("召回指标信息")

    # query 用于让 LLM 生成指标层检索词，keywords 来自上游的通用关键词抽取
    query = state["query"]
    keywords = state["keywords"]
    # 指标召回使用向量检索，需要 Embedding 客户端和指标 Qdrant 仓储配合
    embedding_client = runtime.context["embedding_client"]
    metric_qdrant_repository = runtime.context["metric_qdrant_repository"]

    # 用 LLM 把用户问法扩展成“指标概念”列表，例如“销售总额”可扩展出“GMV”“成交额”
    prompt = PromptTemplate(
        template=load_prompt("extend_keywords_for_metric_recall"),
        input_variables=["query"],
    )
    # 指标扩展 prompt 要求只输出 JSON 数组，解析后 result 就是 list[str]
    output_parser = JsonOutputParser()
    # LCEL 管道：填充提示词 -> 调用模型 -> 解析 JSON
    chain = prompt | llm | output_parser

    result = await chain.ainvoke({"query": query})

    # 通用关键词和指标扩展词都参与召回，提升同义指标的命中率
    keywords = set(keywords + result)

    # 用指标 id 做唯一键，避免多个关键词命中同一个指标时重复写入 state
    metric_info_map: dict[str, MetricInfo] = {}
    for keyword in keywords:
        # 指标库是向量集合，查询词必须先 Embedding 成 query vector
        embedding = await embedding_client.aembed_query(keyword)
        current_metric_infos: list[MetricInfo] = await metric_qdrant_repository.search(
            embedding
        )
        for metric_info in current_metric_infos:
            if metric_info.id not in metric_info_map:
                metric_info_map[metric_info.id] = metric_info

    # 写回 state 的是业务实体列表，后续过滤节点不需要关心 Qdrant 原始 point 结构
    retrieved_metric_infos: list[MetricInfo] = list(metric_info_map.values())

    logger.info(f"检索到指标信息：{list(metric_info_map.keys())}")
    return {"retrieved_metric_infos": retrieved_metric_infos}
