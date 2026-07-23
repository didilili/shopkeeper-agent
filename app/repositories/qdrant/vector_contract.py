"""Qdrant collection 与向量写入的共享契约。"""

import math
from collections.abc import Sequence
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams


class VectorStoreContractError(RuntimeError):
    """Qdrant collection 或待写入向量不符合当前模型契约。"""


def validate_vector_batch(
    ids: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    payloads: Sequence[dict[str, Any]],
    *,
    dimensions: int,
) -> None:
    sizes = (len(ids), len(embeddings), len(payloads))
    if len(set(sizes)) != 1:
        raise VectorStoreContractError(
            "向量写入数量不一致："
            f"ids={sizes[0]}, embeddings={sizes[1]}, payloads={sizes[2]}"
        )
    for index, embedding in enumerate(embeddings):
        if len(embedding) != dimensions:
            raise VectorStoreContractError(
                "待写入向量维度不一致："
                f"index={index}, expected={dimensions}, actual={len(embedding)}"
            )
        if not all(math.isfinite(value) for value in embedding):
            raise VectorStoreContractError(f"待写入向量包含非有限数值：index={index}")


async def ensure_vector_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    *,
    dimensions: int,
) -> None:
    if not await client.collection_exists(collection_name):
        await _create_vector_collection(
            client,
            collection_name,
            dimensions=dimensions,
        )
        return

    collection = await client.get_collection(collection_name)
    vectors = collection.config.params.vectors
    if not isinstance(vectors, VectorParams):
        raise VectorStoreContractError(
            f"collection {collection_name} 使用了不受支持的命名向量配置"
        )
    if vectors.size != dimensions or vectors.distance != Distance.COSINE:
        raise VectorStoreContractError(
            f"collection {collection_name} 向量配置不一致："
            f"expected=({dimensions}, Cosine), "
            f"actual=({vectors.size}, {vectors.distance})"
        )


async def recreate_vector_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    *,
    dimensions: int,
) -> None:
    if await client.collection_exists(collection_name):
        await client.delete_collection(collection_name)
    await _create_vector_collection(
        client,
        collection_name,
        dimensions=dimensions,
    )


async def _create_vector_collection(
    client: AsyncQdrantClient,
    collection_name: str,
    *,
    dimensions: int,
) -> None:
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=dimensions,
            distance=Distance.COSINE,
        ),
    )
