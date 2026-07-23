"""Embedding 客户端、索引构建和 Qdrant 契约测试。"""

import asyncio
from types import SimpleNamespace

import pytest
from qdrant_client.models import Distance, VectorParams

import app.clients.embedding_client_manager as embedding_module
from app.clients.embedding_client_manager import (
    EmbeddingClient,
    EmbeddingClientManager,
    EmbeddingContractError,
)
from app.config.app_config import EmbeddingConfig
from app.repositories.qdrant.vector_contract import (
    VectorStoreContractError,
    ensure_vector_collection,
    validate_vector_batch,
)
from app.services.meta_knowledge_service import MetaKnowledgeService


class FakeEndpoint:
    def __init__(self, responses: list[list[float]]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return self.responses[: len(texts)]


def test_embedding_client_applies_configured_batch_size() -> None:
    endpoint = FakeEndpoint([[1.0, 0.0], [0.0, 1.0]])
    client = EmbeddingClient(
        endpoint,
        model_name="test-model",
        dimensions=2,
        batch_size=2,
        timeout=5,
    )

    embeddings = asyncio.run(client.aembed_documents(["a", "b", "c"]))

    assert endpoint.calls == [["a", "b"], ["c"]]
    assert embeddings == [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]


@pytest.mark.parametrize(
    ("responses", "message"),
    [
        ([[1.0, 0.0]], "返回数量"),
        ([[1.0], [0.0]], "向量维度"),
        ([[float("nan"), 0.0], [0.0, 1.0]], "非有限数值"),
    ],
)
def test_embedding_client_rejects_invalid_responses(
    responses: list[list[float]],
    message: str,
) -> None:
    client = EmbeddingClient(
        FakeEndpoint(responses),
        model_name="test-model",
        dimensions=2,
        batch_size=2,
        timeout=5,
    )

    with pytest.raises(EmbeddingContractError, match=message):
        asyncio.run(client.aembed_documents(["a", "b"]))


def test_embedding_manager_requires_initialization() -> None:
    manager = EmbeddingClientManager(
        EmbeddingConfig(
            host="127.0.0.1",
            port=8081,
            model="test-model",
            timeout=5,
            batch_size=2,
        ),
        dimensions=2,
    )

    with pytest.raises(RuntimeError, match="尚未初始化"):
        manager.get_client()


def test_embedding_manager_applies_http_timeout(monkeypatch) -> None:
    created_clients: list[tuple[str, int]] = []

    class FakeLangChainEndpoint:
        def __init__(self, *, model: str) -> None:
            self.model = model
            self.client = None
            self.async_client = None

    class FakeInferenceClient:
        def __init__(self, *, model: str, timeout: int) -> None:
            created_clients.append((model, timeout))

    monkeypatch.setattr(
        embedding_module,
        "HuggingFaceEndpointEmbeddings",
        FakeLangChainEndpoint,
    )
    monkeypatch.setattr(embedding_module, "InferenceClient", FakeInferenceClient)
    monkeypatch.setattr(embedding_module, "AsyncInferenceClient", FakeInferenceClient)
    manager = EmbeddingClientManager(
        EmbeddingConfig(
            host="embedding.internal",
            port=8081,
            model="test-model",
            timeout=17,
            batch_size=4,
        ),
        dimensions=2,
    )

    client = manager.init()

    assert created_clients == [
        ("http://embedding.internal:8081", 17),
        ("http://embedding.internal:8081", 17),
    ]
    assert client.batch_size == 4
    assert client.model_name == "test-model"


def test_vector_batch_rejects_silent_zip_truncation() -> None:
    with pytest.raises(VectorStoreContractError, match="数量不一致"):
        validate_vector_batch(
            ["one", "two"],
            [[1.0, 0.0]],
            [{"id": "one"}, {"id": "two"}],
            dimensions=2,
        )


def test_existing_collection_dimension_is_validated() -> None:
    class FakeQdrant:
        async def collection_exists(self, name: str) -> bool:
            return True

        async def get_collection(self, name: str):
            return SimpleNamespace(
                config=SimpleNamespace(
                    params=SimpleNamespace(
                        vectors=VectorParams(size=3, distance=Distance.COSINE)
                    )
                )
            )

    with pytest.raises(VectorStoreContractError, match="向量配置不一致"):
        asyncio.run(
            ensure_vector_collection(
                FakeQdrant(),
                "test_collection",
                dimensions=2,
            )
        )


def test_vector_point_ids_are_stable() -> None:
    arguments = {
        "collection_name": "column_info_collection",
        "entity_id": "fact_order.order_amount",
        "payload": {"id": "fact_order.order_amount"},
        "texts": [("name", "order_amount"), ("alias:0", "销售额")],
    }

    first = MetaKnowledgeService._vector_points(**arguments)
    second = MetaKnowledgeService._vector_points(**arguments)

    assert [point["id"] for point in first] == [point["id"] for point in second]
