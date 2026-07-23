"""把任意异常映射为有限、低基数的运行错误类别。"""

import asyncio

from fastapi import HTTPException


def classify_error(error: BaseException) -> str:
    if isinstance(error, asyncio.CancelledError):
        return "cancelled"
    if isinstance(error, TimeoutError):
        return "dependency_timeout"
    if type(error).__name__ == "SQLSafetyError":
        return "sql_safety"
    if type(error).__name__ == "RetrievalError":
        return "retrieval"
    if isinstance(error, HTTPException):
        if error.status_code == 401:
            return "authentication"
        if error.status_code == 429:
            return "rate_limit"
        if error.status_code < 500:
            return "validation"
    if isinstance(error, (ConnectionError, OSError)):
        return "dependency_unavailable"
    dependency_modules = {
        "asyncmy",
        "elastic_transport",
        "elasticsearch",
        "httpx",
        "qdrant_client",
        "sqlalchemy",
    }
    if type(error).__module__.split(".", 1)[0] in dependency_modules:
        return "dependency_unavailable"
    return "internal"
