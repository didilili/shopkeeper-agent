"""由业务模型角色创建并缓存 LangChain Chat Model。"""

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from app.llm.adapters.registry import get_adapter
from app.llm.errors import LLMError, ModelBuildError
from app.llm.registry import resolve_model
from app.llm.schemas import ResolvedModel


def _build_resolved_model(config: ResolvedModel) -> BaseChatModel:
    adapter = get_adapter(config.adapter)
    try:
        model = adapter.build(config)
    except LLMError:
        raise
    except Exception as exc:
        raise ModelBuildError(f"无法构建模型角色 {config.profile_name!r}") from exc

    if not isinstance(model, BaseChatModel):
        raise ModelBuildError(f"适配器 {config.adapter!r} 未返回 BaseChatModel")
    return model


@lru_cache
def get_chat_model(profile_name: str | None = None) -> BaseChatModel:
    """获取适合进程内复用的模型实例。"""

    return _build_resolved_model(resolve_model(profile_name))


def clear_model_caches() -> None:
    get_chat_model.cache_clear()
