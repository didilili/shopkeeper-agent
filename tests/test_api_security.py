"""API Key 认证和单进程限流测试。"""

import asyncio

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from app.api.security import InMemoryRateLimiter, QueryAccessController
from app.config.app_config import APIAccessConfig


def make_request(host: str = "127.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/query",
            "headers": [],
            "client": (host, 12345),
        }
    )


def access_config(*, enabled: bool, api_key: str = "") -> APIAccessConfig:
    return APIAccessConfig(
        enabled=enabled,
        api_key=api_key,
        rate_limit_requests=10,
        rate_limit_window_seconds=60,
    )


def test_enabled_auth_requires_strong_key() -> None:
    with pytest.raises(ValidationError, match="至少需要 32 个字符"):
        access_config(enabled=True, api_key="short")


def test_controller_rejects_missing_or_invalid_key() -> None:
    controller = QueryAccessController(access_config(enabled=True, api_key="a" * 32))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(controller.authorize(make_request(), "wrong-key"))

    assert exc_info.value.status_code == 401


def test_controller_accepts_valid_key_without_exposing_it() -> None:
    api_key = "a" * 32
    controller = QueryAccessController(access_config(enabled=True, api_key=api_key))

    principal = asyncio.run(controller.authorize(make_request(), api_key))

    assert principal.subject != api_key
    assert len(principal.subject) == 16


def test_disabled_auth_uses_client_identity() -> None:
    controller = QueryAccessController(access_config(enabled=False))

    principal = asyncio.run(controller.authorize(make_request("10.0.0.8"), None))

    assert principal.subject == "10.0.0.8"


def test_rate_limiter_returns_retry_after() -> None:
    limiter = InMemoryRateLimiter(requests=1, window_seconds=60)

    asyncio.run(limiter.acquire("client"))
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(limiter.acquire("client"))

    assert exc_info.value.status_code == 429
    assert int(exc_info.value.headers["Retry-After"]) >= 1
