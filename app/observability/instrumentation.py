"""Agent、外部依赖和流式查询的统一计时工具。"""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, TypeVar

from app.config.app_config import app_config
from app.observability.errors import classify_error
from app.observability.logging import audit_event
from app.observability.metrics import (
    AGENT_NODE_DURATION,
    AGENT_NODES,
    EXTERNAL_OPERATION_DURATION,
    EXTERNAL_OPERATIONS,
)

T = TypeVar("T")


@asynccontextmanager
async def observe_external(
    service: str,
    operation: str,
) -> AsyncIterator[None]:
    if not (
        app_config.observability.enabled and app_config.observability.metrics_enabled
    ):
        yield
        return
    started = time.perf_counter()
    outcome = "success"
    error_category = "none"
    try:
        yield
    except asyncio.CancelledError:
        outcome = "cancelled"
        error_category = "cancelled"
        raise
    except BaseException as error:
        outcome = "error"
        error_category = classify_error(error)
        raise
    finally:
        duration = time.perf_counter() - started
        EXTERNAL_OPERATIONS.labels(
            service,
            operation,
            outcome,
            error_category,
        ).inc()
        EXTERNAL_OPERATION_DURATION.labels(service, operation, outcome).observe(
            duration
        )


def observe_agent_node(
    node: str,
    function: Callable[..., Awaitable[T]],
) -> Callable[..., Awaitable[T]]:
    @wraps(function)
    async def wrapped(*args: Any, **kwargs: Any) -> T:
        if not app_config.observability.enabled:
            return await function(*args, **kwargs)
        started = time.perf_counter()
        outcome = "success"
        error_category = "none"
        try:
            return await function(*args, **kwargs)
        except asyncio.CancelledError:
            outcome = "cancelled"
            error_category = "cancelled"
            raise
        except BaseException as error:
            outcome = "error"
            error_category = classify_error(error)
            raise
        finally:
            duration = time.perf_counter() - started
            if app_config.observability.metrics_enabled:
                AGENT_NODES.labels(node, outcome, error_category).inc()
                AGENT_NODE_DURATION.labels(node, outcome).observe(duration)
            audit_event(
                "agent_node_completed",
                component="agent",
                operation=node,
                outcome=outcome,
                error_category=error_category,
                duration_ms=round(duration * 1000, 3),
            )

    return wrapped
