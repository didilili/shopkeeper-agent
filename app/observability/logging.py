"""结构化审计日志与敏感内容摘要。"""

import hashlib
from typing import Any

from app.config.app_config import app_config
from app.core.log import logger
from app.observability.errors import classify_error


def sql_fingerprint(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def audit_event(event: str, *, level: str = "INFO", **fields: Any) -> None:
    if not app_config.observability.enabled:
        return
    logger.bind(event=event, **fields).log(level, event)


def log_failure(component: str, operation: str, error: BaseException) -> None:
    audit_event(
        "operation_failed",
        level="ERROR",
        component=component,
        operation=operation,
        error_category=classify_error(error),
        error_type=type(error).__name__,
    )
