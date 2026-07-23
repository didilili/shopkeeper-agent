"""
FastAPI 应用包入口

负责创建后端应用实例，注册应用生命周期函数，并把各业务模块中的 router
挂载到同一个 app 上。HTTP 请求会先进入这里创建的 app，再按路由分发到
具体的接口处理函数。
"""

import re
import uuid

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.health_router import health_router
from app.api.routers.query_router import query_router
from app.config.app_config import app_config
from app.core.context import request_id_ctx_var

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


def _select_request_id(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID", "").strip()
    if supplied and REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


def create_app(*, lifespan_handler=lifespan) -> FastAPI:
    """创建应用实例；测试可关闭真实基础设施生命周期。"""

    application = FastAPI(
        title=app_config.runtime.app_name,
        version="0.1.0",
        lifespan=lifespan_handler,
    )
    application.state.ready = False
    application.include_router(health_router)
    application.include_router(query_router)

    @application.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = _select_request_id(request)
        request.state.request_id = request_id
        token = request_id_ctx_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_ctx_var.reset(token)

    return application


app = create_app()
