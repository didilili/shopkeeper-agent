"""健康检查接口响应结构。"""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "ready", "not_ready"]
    service: str
    environment: str
