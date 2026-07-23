"""并发、限时且带缓存的外部依赖健康检查。"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import text

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.config.app_config import ObservabilityConfig, app_config
from app.observability.errors import classify_error
from app.observability.metrics import DEPENDENCY_UP

Probe = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class DependencyCheck:
    status: str
    latency_ms: float
    error_category: str | None = None


@dataclass(frozen=True)
class HealthSnapshot:
    status: str
    checked_at: str
    dependencies: dict[str, DependencyCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "dependencies": {
                name: asdict(check) for name, check in self.dependencies.items()
            },
        }


class DependencyHealthService:
    def __init__(
        self,
        config: ObservabilityConfig,
        *,
        probes: dict[str, Probe] | None = None,
    ):
        self.config = config
        self.probes = probes or default_dependency_probes()
        self._snapshot: HealthSnapshot | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def check(self, *, force: bool = False) -> HealthSnapshot:
        now = time.monotonic()
        if not force and self._snapshot is not None and now < self._expires_at:
            return self._snapshot

        async with self._lock:
            now = time.monotonic()
            if not force and self._snapshot is not None and now < self._expires_at:
                return self._snapshot
            names = list(self.probes)
            checks = await asyncio.gather(
                *(self._run_probe(name, self.probes[name]) for name in names)
            )
            dependencies = dict(zip(names, checks, strict=True))
            healthy = all(check.status == "up" for check in checks)
            snapshot = HealthSnapshot(
                status="healthy" if healthy else "degraded",
                checked_at=datetime.now(UTC).isoformat(),
                dependencies=dependencies,
            )
            self._snapshot = snapshot
            self._expires_at = time.monotonic() + self.config.health_cache_ttl_seconds
            return snapshot

    async def _run_probe(self, name: str, probe: Probe) -> DependencyCheck:
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self.config.health_timeout_seconds):
                await probe()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            check = DependencyCheck(
                status="down",
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                error_category=classify_error(error),
            )
            if self.config.enabled and self.config.metrics_enabled:
                DEPENDENCY_UP.labels(name).set(0)
            return check
        check = DependencyCheck(
            status="up",
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
        )
        if self.config.enabled and self.config.metrics_enabled:
            DEPENDENCY_UP.labels(name).set(1)
        return check


async def _probe_meta_mysql() -> None:
    if meta_mysql_client_manager.session_factory is None:
        raise ConnectionError("Meta MySQL client unavailable")
    async with meta_mysql_client_manager.session_factory() as session:
        await session.execute(text("SELECT 1"))


async def _probe_dw_mysql() -> None:
    if dw_mysql_client_manager.session_factory is None:
        raise ConnectionError("DW MySQL client unavailable")
    async with dw_mysql_client_manager.session_factory() as session:
        await session.execute(text("SELECT 1"))


async def _probe_qdrant() -> None:
    if qdrant_client_manager.client is None:
        raise ConnectionError("Qdrant client unavailable")
    await qdrant_client_manager.client.get_collections()


async def _probe_elasticsearch() -> None:
    if es_client_manager.client is None or not await es_client_manager.client.ping():
        raise ConnectionError("Elasticsearch unavailable")


async def _probe_embedding() -> None:
    url = (
        f"http://{embedding_client_manager.config.host}:"
        f"{embedding_client_manager.config.port}/health"
    )
    async with httpx.AsyncClient(
        timeout=app_config.observability.health_timeout_seconds
    ) as client:
        response = await client.get(url)
        response.raise_for_status()


def default_dependency_probes() -> dict[str, Probe]:
    return {
        "meta_mysql": _probe_meta_mysql,
        "dw_mysql": _probe_dw_mysql,
        "qdrant": _probe_qdrant,
        "elasticsearch": _probe_elasticsearch,
        "embedding": _probe_embedding,
    }


dependency_health_service = DependencyHealthService(app_config.observability)
