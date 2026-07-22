"""Prompt 注册、渲染和输出解析领域异常。"""


class PromptError(Exception):
    """Prompt 模块基础异常。"""


class PromptConfigurationError(PromptError):
    """Prompt 注册表或模板定义不合法。"""


class PromptNotFoundError(PromptConfigurationError):
    """请求的 Prompt 未注册。"""


class PromptOutputError(PromptError):
    """模型输出不满足 Prompt 声明的协议。"""
