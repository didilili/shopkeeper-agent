"""受保护的运行诊断和 Prometheus 指标端点。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.security import AccessPrincipal, require_query_access
from app.config.app_config import app_config
from app.observability.health import dependency_health_service
from app.observability.metrics import render_metrics

observability_router = APIRouter(tags=["observability"])


@observability_router.get("/api/diagnostics")
async def diagnostics(
    _principal: Annotated[AccessPrincipal, Depends(require_query_access)],
):
    if not (
        app_config.observability.enabled
        and app_config.observability.diagnostics_enabled
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return (await dependency_health_service.check()).to_dict()


@observability_router.get("/metrics", response_class=Response)
async def metrics(
    _principal: Annotated[AccessPrincipal, Depends(require_query_access)],
) -> Response:
    if not (
        app_config.observability.enabled and app_config.observability.metrics_enabled
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    content, content_type = render_metrics()
    return Response(content=content, headers={"Content-Type": content_type})
