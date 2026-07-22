"""应用环境配置测试。"""

import pytest

from app.conf.app_config import ConfigurationError, load_app_config


def test_test_environment_uses_isolated_databases() -> None:
    config = load_app_config("test")

    assert config.runtime.environment == "test"
    assert config.db_meta.database == "meta_test"
    assert config.db_dw.database == "dw_test"
    assert config.retrieval.column.final_limit == 20
    assert config.retrieval.metric.final_limit == 10


def test_secret_values_are_masked() -> None:
    config = load_app_config("test")

    assert "test-only-password" not in repr(config)
    assert "**********" in repr(config.db_meta.password)


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

    config = load_app_config("production")

    assert config.runtime.environment == "production"
    assert config.runtime.debug is False
