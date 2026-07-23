"""
指标向量仓储

管理指标向量集合，并把 Service 层准备好的指标 point 批量写入 Qdrant

字段和指标虽然都用向量检索，但它们是两类不同对象
所以指标单独使用 metric_info_collection，避免后续召回时和字段结果混在一起
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.config.app_config import app_config
from app.entities.metric_info import MetricInfo
from app.observability.instrumentation import observe_external
from app.repositories.qdrant.vector_contract import (
    ensure_vector_collection,
    recreate_vector_collection,
    validate_vector_batch,
)
from app.retrieval.schemas import SearchHit


class MetricQdrantRepository:
    """负责指标向量集合的创建 写入和基础检索"""

    collection_name = "metric_info_collection"

    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def ensure_collection(self):
        """确保指标向量集合存在，并按当前 Embedding 维度初始化"""
        await ensure_vector_collection(
            self.client,
            self.collection_name,
            dimensions=app_config.qdrant.embedding_size,
        )

    async def recreate_collection(self) -> None:
        """重建离线索引 collection，确保删除已失效的历史向量点。"""
        await recreate_vector_collection(
            self.client,
            self.collection_name,
            dimensions=app_config.qdrant.embedding_size,
        )

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
        batch_size: int = 10,
    ):
        """分批 upsert 指标向量点，避免一次提交过多 point"""
        validate_vector_batch(
            ids,
            embeddings,
            payloads,
            dimensions=app_config.qdrant.embedding_size,
        )
        points: list[PointStruct] = [
            PointStruct(id=id, vector=embedding, payload=payload)
            for id, embedding, payload in zip(
                ids,
                embeddings,
                payloads,
                strict=True,
            )
        ]
        for i in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.collection_name, points=points[i : i + batch_size]
            )

    async def search(
        self, embedding: list[float], score_threshold: float = 0.6, limit: int = 20
    ) -> list[SearchHit[MetricInfo]]:
        """按向量相似度检索指标元数据，并保留底层相似度分数。"""

        async with observe_external("qdrant", "search_metric"):
            result = await self.client.query_points(
                collection_name=self.collection_name,
                query=embedding,
                limit=limit,
                score_threshold=score_threshold,
            )
        return [
            SearchHit(
                item=MetricInfo(**(point.payload or {})),
                score=float(point.score),
            )
            for point in result.points
        ]
