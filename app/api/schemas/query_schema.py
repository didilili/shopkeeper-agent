"""
问数接口请求体定义

集中声明 API 层输入输出的数据结构，让路由函数只处理业务流程，
字段校验和 OpenAPI 文档生成交给 Pydantic 与 FastAPI 完成。
"""

from typing import Annotated

from pydantic import BaseModel, StringConstraints


class QuerySchema(BaseModel):
    """`/api/query` 请求体，承载用户输入的自然语言问题"""

    # 前端请求体中的 query 字段，例如 {"query": "统计华北地区销售额"}
    query: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]
