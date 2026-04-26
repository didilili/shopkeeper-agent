"""
掌柜问数 Agent 状态定义

State 是 LangGraph 各节点之间传递和更新的共享数据
本章先保留用户问题和 SQL 校验错误，后续字段 指标 SQL 结果等中间信息都会继续扩展到这里
"""

from typing import TypedDict


class DataAgentState(TypedDict):
    """一次问数链路中的核心状态"""

    query: str  # 用户输入的查询
    error: str  # 校验SQL时出现的错误信息
