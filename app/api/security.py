"""查询接口的 API Key 认证与单进程固定窗口限流。"""

import asyncio
import hashlib
import math
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.config.app_config import APIAccessConfig, app_config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class AccessPrincipal:
    subject: str


@dataclass
class _RateWindow:
    started_at: float
    count: int = 0


class InMemoryRateLimiter:
    """适合单进程部署的固定窗口限流器。"""

    def __init__(self, *, requests: int, window_seconds: int):
        self.requests = requests
        self.window_seconds = window_seconds
        self._windows: dict[str, _RateWindow] = {}
        self._lock = asyncio.Lock()
        self._operations = 0

    async def acquire(self, identity: str) -> None:
        now = time.monotonic()
        async with self._lock:
            self._operations += 1
            if self._operations % 128 == 0:
                self._windows = {
                    key: window
                    for key, window in self._windows.items()
                    if now - window.started_at < self.window_seconds
                }

            window = self._windows.get(identity)
            if window is None or now - window.started_at >= self.window_seconds:
                self._windows[identity] = _RateWindow(started_at=now, count=1)
                return
            if window.count >= self.requests:
                retry_after = max(
                    1,
                    math.ceil(self.window_seconds - (now - window.started_at)),
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="请求过于频繁，请稍后重试。",
                    headers={"Retry-After": str(retry_after)},
                )
            window.count += 1


class QueryAccessController:
    def __init__(self, config: APIAccessConfig):
        self.config = config
        self.rate_limiter = InMemoryRateLimiter(
            requests=config.rate_limit_requests,
            window_seconds=config.rate_limit_window_seconds,
        )

    async def authorize(
        self, request: Request, provided_api_key: str | None
    ) -> AccessPrincipal:
        if self.config.enabled:
            expected = self.config.api_key.get_secret_value()
            if not provided_api_key or not secrets.compare_digest(
                provided_api_key, expected
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="缺少或无效的 API Key。",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
            identity = hashlib.sha256(provided_api_key.encode()).hexdigest()[:16]
        else:
            identity = request.client.host if request.client else "anonymous"

        await self.rate_limiter.acquire(identity)
        return AccessPrincipal(subject=identity)


query_access_controller = QueryAccessController(app_config.api_access)


async def require_query_access(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> AccessPrincipal:
    return await query_access_controller.authorize(request, api_key)
