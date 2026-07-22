"""模型配置与构建过程使用的领域异常。"""


class LLMError(Exception):
    """LLM 基础异常。"""


class LLMConfigurationError(LLMError):
    """模型注册表或初始化参数无效。"""


class ProfileNotFoundError(LLMConfigurationError):
    """业务模型角色不存在。"""


class AdapterNotFoundError(LLMConfigurationError):
    """模型引用了未安装或未注册的协议适配器。"""


class CredentialError(LLMConfigurationError):
    """所选模型需要的凭证缺失。"""


class ModelBuildError(LLMError):
    """协议适配器无法创建 LangChain 模型。"""
