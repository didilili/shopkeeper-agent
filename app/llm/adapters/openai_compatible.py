"""OpenAI Chat Completions 兼容协议适配器。"""

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from app.llm.adapters.base import ChatModelAdapter
from app.llm.adapters.registry import register_adapter
from app.llm.errors import CredentialError, LLMConfigurationError
from app.llm.schemas import ResolvedModel


@register_adapter
class OpenAICompatibleAdapter(ChatModelAdapter):
    name = "openai_compatible"

    def build(self, config: ResolvedModel) -> BaseChatModel:
        if config.base_url is None:
            raise LLMConfigurationError(
                f"部署 {config.deployment_name!r} 缺少 base_url"
            )
        if config.credentials.api_key is None:
            raise CredentialError(f"部署 {config.deployment_name!r} 缺少 API Key")

        protected = {"model", "model_provider", "api_key", "base_url"}
        conflicts = protected & config.options.extra_kwargs.keys()
        if conflicts:
            raise LLMConfigurationError(
                "extra_kwargs 不得覆盖固定参数：" + ", ".join(sorted(conflicts))
            )

        kwargs = {
            "model": config.model,
            "model_provider": "openai",
            "api_key": config.credentials.api_key.get_secret_value(),
            "base_url": str(config.base_url).rstrip("/"),
            "temperature": config.options.temperature,
            "timeout": config.options.timeout,
            "max_retries": config.options.max_retries,
            **config.options.extra_kwargs,
        }
        if config.options.max_tokens is not None:
            kwargs["max_tokens"] = config.options.max_tokens
        return init_chat_model(**kwargs)
