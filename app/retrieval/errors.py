"""召回服务对外暴露的领域异常。"""


class RetrievalError(RuntimeError):
    """召回链路无法产出可信结果。"""
