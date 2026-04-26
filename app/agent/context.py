"""
掌柜问数 Agent 运行上下文

Context 用来保存一次图执行过程中不参与状态合并的外部依赖或配置
当前章节先保留空结构，后续可以继续放入用户信息 数据源配置 权限信息等运行时参数
"""

from typing import TypedDict


class DataAgentContext(TypedDict):
    """LangGraph Runtime 中传递的上下文对象"""

    pass
