"""底层仓储保留检索分数的契约测试。"""

import asyncio
from types import SimpleNamespace

from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository


def test_qdrant_repository_preserves_similarity_score() -> None:
    class FakeClient:
        async def query_points(self, **kwargs):
            assert kwargs["score_threshold"] == 0.7
            assert kwargs["limit"] == 3
            return SimpleNamespace(
                points=[
                    SimpleNamespace(
                        score=0.91,
                        payload={
                            "id": "fact_order.order_amount",
                            "name": "order_amount",
                            "type": "FLOAT",
                            "role": "measure",
                            "examples": [8999],
                            "description": "订单金额",
                            "alias": ["销售额"],
                            "table_id": "fact_order",
                        },
                    )
                ]
            )

    repository = ColumnQdrantRepository(FakeClient())
    hits = asyncio.run(repository.search([0.1, 0.2], score_threshold=0.7, limit=3))

    assert hits[0].item.id == "fact_order.order_amount"
    assert hits[0].score == 0.91


def test_elasticsearch_repository_preserves_text_score() -> None:
    class FakeClient:
        async def search(self, **kwargs):
            assert kwargs["min_score"] == 0.5
            assert kwargs["size"] == 4
            return {
                "hits": {
                    "hits": [
                        {
                            "_score": 3.2,
                            "_source": {
                                "id": "dim_region.region_name.华东",
                                "value": "华东",
                                "column_id": "dim_region.region_name",
                            },
                        }
                    ]
                }
            }

    repository = ValueESRepository(FakeClient())
    hits = asyncio.run(repository.search("华东", score_threshold=0.5, limit=4))

    assert hits[0].item.value == "华东"
    assert hits[0].score == 3.2
