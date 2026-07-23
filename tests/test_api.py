"""FastAPI 健康检查、请求追踪和 SSE 接口集成测试。"""

from fastapi.testclient import TestClient

from app.api.dependencies import get_query_service
from app.api.security import InMemoryRateLimiter, query_access_controller
from app.config.app_config import APIAccessConfig
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


def test_liveness_and_readiness_have_distinct_semantics() -> None:
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

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert health.status_code == 200
