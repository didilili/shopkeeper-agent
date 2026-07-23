"""问数服务 SSE 编码、错误脱敏和取消传播测试。"""

import asyncio
import importlib
import json

import pytest

from app.config.app_config import app_config
from app.core.context import request_id_ctx_var
from app.services.query_service import QueryService


class SuccessfulGraph:
    async def astream(self, **kwargs):
        yield {"type": "progress", "step": "测试", "status": "success"}
        yield {"type": "result", "data": [{"value": 1}]}


class FailingGraph:
    async def astream(self, **kwargs):
        if False:
            yield None
        raise RuntimeError("internal database details")


class CancelledGraph:
    async def astream(self, **kwargs):
        if False:
            yield None
        raise asyncio.CancelledError


def make_service(agent_graph) -> QueryService:
    return QueryService(
        meta_mysql_repository=None,
        embedding_client=None,
        dw_mysql_repository=None,
        column_qdrant_repository=None,
        metric_qdrant_repository=None,
        value_es_repository=None,
        agent_graph=agent_graph,
    )


async def collect_events(service: QueryService, request_id: str) -> list[dict]:
    chunks = [chunk async for chunk in service.query("测试问题", request_id=request_id)]
    return [json.loads(chunk.removeprefix("data: ").strip()) for chunk in chunks]


def test_query_streams_existing_progress_and_result_contract() -> None:
    events = asyncio.run(collect_events(make_service(SuccessfulGraph()), "req-success"))

    assert [event["type"] for event in events] == ["progress", "result"]
    assert events[1]["data"] == [{"value": 1}]


def test_query_hides_internal_error_and_returns_request_id() -> None:
    events = asyncio.run(collect_events(make_service(FailingGraph()), "req-failure"))

    assert events == [
        {
            "type": "error",
            "message": "查询处理失败，请使用 request_id 联系管理员。",
            "request_id": "req-failure",
        }
    ]
    assert "database" not in events[0]["message"]


def test_query_restores_context_after_stream_finishes() -> None:
    token = request_id_ctx_var.set("outer-request")
    try:
        asyncio.run(collect_events(make_service(SuccessfulGraph()), "inner-request"))
        assert request_id_ctx_var.get() == "outer-request"
    finally:
        request_id_ctx_var.reset(token)


def test_query_propagates_client_cancellation() -> None:
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(collect_events(make_service(CancelledGraph()), "req-cancelled"))


def test_query_completion_audit_remains_when_metrics_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query_service_module = importlib.import_module("app.services.query_service")
    metrics_disabled_config = app_config.model_copy(
        update={
            "observability": app_config.observability.model_copy(
                update={"metrics_enabled": False}
            )
        }
    )
    events: list[str] = []

    monkeypatch.setattr(query_service_module, "app_config", metrics_disabled_config)
    monkeypatch.setattr(
        query_service_module,
        "audit_event",
        lambda event, **_fields: events.append(event),
    )

    asyncio.run(collect_events(make_service(SuccessfulGraph()), "req-audit"))

    assert "query_stream_completed" in events
