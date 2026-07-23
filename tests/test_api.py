"""FastAPI 健康检查、请求追踪和 SSE 接口集成测试。"""

import importlib

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_query_service
from app.api.security import InMemoryRateLimiter, query_access_controller
from app.config.app_config import APIAccessConfig, app_config
from app.main import create_app


class FakeQueryService:
    async def query(self, query: str, *, request_id: str):
        yield (
            'data: {"type":"result","data":[{"query":"'
            + query
            + '","request_id":"'
            + request_id
            + '"}]}\n\n'
        )


def make_client() -> tuple[TestClient, object]:
    application = create_app(lifespan_handler=None)
    application.dependency_overrides[get_query_service] = lambda: FakeQueryService()
    return TestClient(application), application


def test_liveness_and_readiness_have_distinct_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HealthyService:
        async def check(self):
            return type("Snapshot", (), {"status": "healthy"})()

    health_module = importlib.import_module("app.api.routers.health_router")
    monkeypatch.setattr(
        health_module,
        "dependency_health_service",
        HealthyService(),
    )
    client, application = make_client()

    live = client.get("/api/health/live")
    not_ready = client.get("/api/health/ready")
    application.state.ready = True
    ready = client.get("/api/health/ready")

    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert not_ready.status_code == 503
    assert not_ready.json()["status"] == "not_ready"
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_query_echoes_valid_request_id_and_sets_stream_headers() -> None:
    client, _ = make_client()

    response = client.post(
        "/api/query",
        json={"query": " 查询销售额 "},
        headers={"X-Request-ID": "client-request-42"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "client-request-42"
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Accel-Buffering"] == "no"
    assert '"query":"查询销售额"' in response.text
    assert '"request_id":"client-request-42"' in response.text


def test_invalid_request_id_is_replaced() -> None:
    client, _ = make_client()

    response = client.get(
        "/api/health/live",
        headers={"X-Request-ID": "unsafe request id"},
    )

    generated = response.headers["X-Request-ID"]
    assert response.status_code == 200
    assert generated != "unsafe request id"
    assert len(generated) == 32


def test_query_validation_errors_still_include_request_id() -> None:
    client, _ = make_client()

    response = client.post(
        "/api/query",
        json={"query": "   "},
        headers={"X-Request-ID": "validation-request"},
    )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "validation-request"


def test_query_requires_configured_api_key_but_health_remains_public(
    monkeypatch,
) -> None:
    api_key = "a" * 32
    access_config = APIAccessConfig(
        enabled=True,
        api_key=api_key,
        rate_limit_requests=10,
        rate_limit_window_seconds=60,
    )
    monkeypatch.setattr(query_access_controller, "config", access_config)
    monkeypatch.setattr(
        query_access_controller,
        "rate_limiter",
        InMemoryRateLimiter(requests=10, window_seconds=60),
    )
    client, _ = make_client()

    unauthorized = client.post("/api/query", json={"query": "查询销售额"})
    authorized = client.post(
        "/api/query",
        json={"query": "查询销售额"},
        headers={"X-API-Key": api_key},
    )
    health = client.get("/api/health/live")
    diagnostics = client.get("/api/diagnostics")
    metrics = client.get("/metrics")

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert health.status_code == 200
    assert diagnostics.status_code == 401
    assert metrics.status_code == 401


def test_degraded_dependencies_make_readiness_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DegradedService:
        async def check(self):
            return type("Snapshot", (), {"status": "degraded"})()

    health_module = importlib.import_module("app.api.routers.health_router")
    monkeypatch.setattr(
        health_module,
        "dependency_health_service",
        DegradedService(),
    )
    client, application = make_client()
    application.state.ready = True

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_diagnostics_and_metrics_are_available_when_authorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HealthySnapshot:
        def to_dict(self):
            return {
                "status": "healthy",
                "checked_at": "2026-07-23T00:00:00+00:00",
                "dependencies": {
                    "embedding": {
                        "status": "up",
                        "latency_ms": 1.5,
                        "error_category": None,
                    }
                },
            }

    class HealthyService:
        async def check(self):
            return HealthySnapshot()

    observability_module = importlib.import_module(
        "app.api.routers.observability_router"
    )
    monkeypatch.setattr(
        observability_module,
        "dependency_health_service",
        HealthyService(),
    )
    client, _ = make_client()

    diagnostics = client.get("/api/diagnostics")
    metrics = client.get("/metrics")

    assert diagnostics.status_code == 200
    assert diagnostics.json()["dependencies"]["embedding"]["status"] == "up"
    assert metrics.status_code == 200
    assert "text/plain" in metrics.headers["content-type"]
    assert "shopkeeper_http_requests_total" in metrics.text


def test_observability_master_switch_hides_runtime_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observability_module = importlib.import_module(
        "app.api.routers.observability_router"
    )
    disabled_config = app_config.model_copy(
        update={
            "observability": app_config.observability.model_copy(
                update={"enabled": False}
            )
        }
    )
    monkeypatch.setattr(observability_module, "app_config", disabled_config)
    client, _ = make_client()

    assert client.get("/api/diagnostics").status_code == 404
    assert client.get("/metrics").status_code == 404
