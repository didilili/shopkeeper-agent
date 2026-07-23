"""
问数查询服务

负责把 API 层传入的自然语言问题转换成一次 LangGraph 工作流执行：
创建初始 State、组装 Runtime Context、消费 graph.astream 的流式输出，
并统一包装成 SSE 文本返回给路由层。
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import EmbeddingClient
from app.config.app_config import app_config
from app.core.context import request_id_ctx_var
from app.observability.errors import classify_error
from app.observability.logging import audit_event
from app.observability.metrics import QUERY_STREAM_DURATION, QUERY_STREAMS
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class QueryService:
    """封装一次问数查询所需的业务编排逻辑"""

    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        embedding_client: EmbeddingClient,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
        agent_graph: Any = graph,
    ):
        # MySQL 仓储分别负责元数据补全和真实数仓环境信息读取
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository

        # 召回链路依赖的向量检索、Embedding 和全文检索能力由依赖层注入
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository
        self.agent_graph = agent_graph

    async def query(
        self, query: str, *, request_id: str | None = None
    ) -> AsyncIterator[str]:
        """执行一次问数工作流，并逐段产出 SSE 消息"""

        selected_request_id = request_id or request_id_ctx_var.get()
        token = request_id_ctx_var.set(selected_request_id)
        # State 只放会被图节点读写和合并的业务数据，外部工具对象不塞进 State
        state = DataAgentState(query=query)
        # Context 保存本次图执行需要复用的外部依赖，节点通过 runtime.context 读取
        context = DataAgentContext(
            column_qdrant_repository=self.column_qdrant_repository,
            embedding_client=self.embedding_client,
            metric_qdrant_repository=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
        )
        started = time.perf_counter()
        outcome = "success"
        error_category = "none"
        try:
            # stream_mode="custom" 对应节点内部 writer(...) 写出的进度消息
            async for chunk in self.agent_graph.astream(
                input=state, context=context, stream_mode="custom"
            ):
                # SSE 要求每条消息以 data: 开头，并以两个换行符结束
                # ensure_ascii=False 保留中文进度文案，default=str 兜底处理日期等非 JSON 类型
                yield _encode_sse(chunk)
        except asyncio.CancelledError:
            outcome = "cancelled"
            error_category = "cancelled"
            audit_event(
                "query_stream_cancelled",
                component="query",
                operation="stream",
                outcome=outcome,
            )
            raise
        except Exception as error:
            outcome = "error"
            error_category = classify_error(error)
            audit_event(
                "query_stream_failed",
                level="ERROR",
                component="query",
                operation="stream",
                outcome=outcome,
                error_category=error_category,
                error_type=type(error).__name__,
            )
            error = {
                "type": "error",
                "message": "查询处理失败，请使用 request_id 联系管理员。",
                "request_id": selected_request_id,
            }
            yield _encode_sse(error)
        finally:
            duration = time.perf_counter() - started
            if (
                app_config.observability.enabled
                and app_config.observability.metrics_enabled
            ):
                QUERY_STREAMS.labels(outcome, error_category).inc()
                QUERY_STREAM_DURATION.labels(outcome).observe(duration)
                audit_event(
                    "query_stream_completed",
                    component="query",
                    operation="stream",
                    outcome=outcome,
                    error_category=error_category,
                    duration_ms=round(duration * 1000, 3),
                    slow=duration
                    >= app_config.observability.slow_query_threshold_seconds,
                )
            request_id_ctx_var.reset(token)


def _encode_sse(event: Any) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
