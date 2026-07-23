"""应用存活与资源初始化状态接口。"""

from fastapi import APIRouter, Request, Response, status

from app.api.schemas.health_schema import HealthResponse
from app.config.app_config import app_config
from app.observability.health import dependency_health_service

health_router = APIRouter(prefix="/api/health", tags=["health"])


@health_router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """进程能够处理 HTTP 请求即视为存活。"""

    return HealthResponse(
        status="ok",
        service=app_config.runtime.app_name,
        environment=app_config.runtime.environment,
    )


@health_router.get("/ready", response_model=HealthResponse)
async def readiness(request: Request, response: Response) -> HealthResponse:
    """报告应用级资源是否完成生命周期初始化。"""

    ready = bool(getattr(request.app.state, "ready", False))
    if ready and app_config.observability.enabled:
        snapshot = await dependency_health_service.check()
        ready = snapshot.status == "healthy"
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ready" if ready else "not_ready",
        service=app_config.runtime.app_name,
        environment=app_config.runtime.environment,
    )
