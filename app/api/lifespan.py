"""
FastAPI 应用生命周期管理

负责在服务启动时初始化外部客户端，在服务关闭时释放连接资源。
这些客户端是应用级资源，适合在 lifespan 中创建一次并复用，而不是每个请求
重复初始化。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用启动和关闭两个阶段的外部资源"""

    app.state.ready = False
    initialized = []
    try:
        qdrant_client_manager.init()
        initialized.append(qdrant_client_manager)
        embedding_client_manager.init()
        es_client_manager.init()
        initialized.append(es_client_manager)
        meta_mysql_client_manager.init()
        initialized.append(meta_mysql_client_manager)
        dw_mysql_client_manager.init()
        initialized.append(dw_mysql_client_manager)
        app.state.ready = True
        yield
    finally:
        app.state.ready = False
        for manager in reversed(initialized):
            try:
                await manager.close()
            except Exception:
                logger.exception("关闭应用资源失败：{}", type(manager).__name__)
