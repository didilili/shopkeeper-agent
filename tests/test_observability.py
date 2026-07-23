"""可观测性指标、节点计时和依赖健康缓存测试。"""

import asyncio
import importlib

import pytest
from prometheus_client import generate_latest

from app.config.app_config import ObservabilityConfig, app_config
from app.observability.health import DependencyHealthService
from app.observability.instrumentation import observe_agent_node
from app.observability.logging import sql_fingerprint


def observability_config(**overrides) -> ObservabilityConfig:
    values = {
        "enabled": True,
        "metrics_enabled": True,
        "diagnostics_enabled": True,
        "health_timeout_seconds": 1,
        "health_cache_ttl_seconds": 10,
        "slow_query_threshold_seconds": 10,
    }
    values.update(overrides)
    return ObservabilityConfig(**values)


def test_dependency_health_checks_are_cached() -> None:
    calls = 0

    async def healthy_probe() -> None:
        nonlocal calls
        calls += 1

    service = DependencyHealthService(
        observability_config(),
        probes={"dependency": healthy_probe},
    )

    async def check_twice():
        first = await service.check()
        second = await service.check()
        return first, second

    first, second = asyncio.run(check_twice())

    assert first.status == "healthy"
    assert second is first
    assert calls == 1


def test_dependency_timeout_is_sanitized() -> None:
    async def slow_probe() -> None:
        await asyncio.sleep(0.05)

    service = DependencyHealthService(
        observability_config(health_timeout_seconds=0.01),
        probes={"slow": slow_probe},
    )

    snapshot = asyncio.run(service.check())

    assert snapshot.status == "degraded"
    assert snapshot.dependencies["slow"].status == "down"
    assert snapshot.dependencies["slow"].error_category == "dependency_timeout"
    assert "slow_probe" not in str(snapshot.to_dict())


def test_agent_node_wrapper_records_bounded_metrics() -> None:
    async def node(value: int) -> int:
        return value + 1

    wrapped = observe_agent_node("unit_test_node", node)

    assert asyncio.run(wrapped(1)) == 2
    metrics = generate_latest().decode()
    assert 'node="unit_test_node",outcome="success"' in metrics


def test_metrics_switch_disables_node_metric_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instrumentation_module = importlib.import_module(
        "app.observability.instrumentation"
    )
    disabled_config = app_config.model_copy(
        update={
            "observability": app_config.observability.model_copy(
                update={"metrics_enabled": False}
            )
        }
    )
    monkeypatch.setattr(instrumentation_module, "app_config", disabled_config)

    async def node() -> None:
        return None

    wrapped = observe_agent_node("metrics_disabled_test_node", node)
    asyncio.run(wrapped())

    assert 'node="metrics_disabled_test_node"' not in generate_latest().decode()


def test_sql_fingerprint_does_not_expose_sql() -> None:
    sql = "SELECT secret_column FROM private_table"

    fingerprint = sql_fingerprint(sql)

    assert len(fingerprint) == 16
    assert "secret_column" not in fingerprint
