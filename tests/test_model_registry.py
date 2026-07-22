"""模型注册表、凭证解析和模型工厂测试。"""

import pytest
from langchain_core.language_models.chat_models import BaseChatModel

from app.llm.errors import CredentialError, ProfileNotFoundError
from app.llm.factory import clear_model_caches, get_chat_model
from app.llm.registry import clear_model_caches as clear_registry_cache
from app.llm.registry import resolve_model


@pytest.fixture(autouse=True)
def clear_caches() -> None:
    clear_model_caches()
    clear_registry_cache()


def test_resolve_business_profile_and_mask_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-model-secret")

    config = resolve_model("sql_agent")

    assert config.deployment_name == "siliconflow_glm"
    assert config.adapter == "openai_compatible"
    assert "test-model-secret" not in repr(config)


def test_missing_credential_fails_before_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")

    with pytest.raises(CredentialError, match="缺少有效环境变量"):
        resolve_model("sql_agent")


def test_unknown_profile_reports_available_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-model-secret")

    with pytest.raises(ProfileNotFoundError, match="sql_agent"):
        resolve_model("unknown")


def test_factory_builds_langchain_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-model-secret")

    model = get_chat_model("sql_agent")

    assert isinstance(model, BaseChatModel)
