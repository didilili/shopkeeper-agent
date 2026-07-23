"""应用环境配置测试。"""

import pytest

from app.config.app_config import ConfigurationError, load_app_config


def test_test_environment_uses_isolated_databases() -> None:
    config = load_app_config("test")

    assert config.runtime.environment == "test"
    assert config.db_meta.database == "meta_test"
    assert config.db_dw.database == "dw_test"
    assert config.retrieval.column.final_limit == 20
    assert config.retrieval.metric.final_limit == 10
    assert config.retrieval.max_queries == 12
    assert config.sql_execution.max_result_rows == 1000
    assert config.sql_execution.max_correction_attempts == 2
    assert config.api_access.enabled is False
    assert config.api_access.rate_limit_requests == 60
    assert config.embedding.batch_size == 20
    assert config.observability.metrics_enabled is True
    assert config.observability.health_cache_ttl_seconds == 10


def test_secret_values_are_masked() -> None:
    config = load_app_config("test")

    assert "test-only-password" not in repr(config)
    assert "**********" in repr(config.db_meta.password)


def test_retrieval_query_limit_can_be_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RETRIEVAL_MAX_QUERIES", "6")

    config = load_app_config("test")

    assert config.retrieval.max_queries == 6


def test_production_rejects_example_passwords(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_META_PASSWORD", "dili123")
    monkeypatch.setenv("DB_DW_PASSWORD", "dili123")

    with pytest.raises(ConfigurationError, match="生产环境禁止") as exc_info:
        load_app_config("production")

    assert "dili123" not in str(exc_info.value)


def test_production_accepts_injected_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_META_PASSWORD", "production-meta-secret")
    monkeypatch.setenv("DB_DW_PASSWORD", "production-dw-secret")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEY", "production-api-key-with-32-characters")

    config = load_app_config("production")

    assert config.runtime.environment == "production"
    assert config.runtime.debug is False
    assert config.api_access.enabled is True
    assert config.logging.structured is True


def test_production_requires_api_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_META_PASSWORD", "production-meta-secret")
    monkeypatch.setenv("DB_DW_PASSWORD", "production-dw-secret")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")

    with pytest.raises(ConfigurationError, match="API_AUTH_ENABLED"):
        load_app_config("production")
