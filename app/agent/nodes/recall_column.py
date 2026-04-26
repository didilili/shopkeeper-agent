"""
字段召回节点

负责根据关键词从字段向量知识库中召回候选字段
它解决的是“用户问题可能对应哪些数据库字段”的问题
本章的主线是：关键词扩展 -> Embedding -> Qdrant 相似度检索 -> ColumnInfo 去重
"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """召回和用户问题语义相关的字段元数据"""

    writer = runtime.stream_writer
    writer("召回字段信息")

    # state 保存图内业务中间结果：原始问题和上游抽取出的关键词
    keywords = state["keywords"]
    query = state["query"]
    # context 保存外部运行时工具：向量仓储和 Embedding 客户端
    column_qdrant_repository = runtime.context["column_qdrant_repository"]
    embedding_client = runtime.context["embedding_client"]

    # 用 LLM 把用户问法扩展成“字段语义”列表，例如“销售总额”可扩展出“销售金额”
    prompt = PromptTemplate(
        template=load_prompt("extend_keywords_for_column_recall"),
        input_variables=["query"],
    )
    # 提示词要求模型只输出 JSON 数组，解析后 result 就是 list[str]
    output_parser = JsonOutputParser()
    # LCEL 管道：填充提示词 -> 调用模型 -> 解析 JSON
    chain = prompt | llm | output_parser

    result = await chain.ainvoke({"query": query})

    # 原始关键词和 LLM 扩展词一起参与召回；set 去重，避免重复请求同一关键词
    keywords = set(keywords + result)

    # 用字段 id 做唯一键，因为多个关键词、同一字段的多个向量点都可能命中同一个字段
    column_info_map: dict[str, ColumnInfo] = {}
    for keyword in keywords:
        # 查询词必须先转成向量，才能和第 9 章写入 Qdrant 的字段向量做相似度检索
        embedding = await embedding_client.aembed_query(keyword)
        current_column_infos: list[ColumnInfo] = await column_qdrant_repository.search(
            embedding
        )
        for column_info in current_column_infos:
            if column_info.id not in column_info_map:
                column_info_map[column_info.id] = column_info

    # 写回 state 的是去重后的 ColumnInfo 列表，不暴露 Qdrant 原始 point 结构
    retrieved_column_infos: list[ColumnInfo] = list(column_info_map.values())

    logger.info(f"检索到字段信息：{list(column_info_map.keys())}")
    return {"retrieved_column_infos": retrieved_column_infos}
