"""受控 Embedding 客户端与应用级生命周期管理。"""

import asyncio
import math
from collections.abc import Sequence

from huggingface_hub import AsyncInferenceClient, InferenceClient
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.config.app_config import EmbeddingConfig, app_config
from app.core.log import logger
from app.observability.instrumentation import observe_external


class EmbeddingContractError(RuntimeError):
    """Embedding 服务响应不符合数量、维度或数值契约。"""


class EmbeddingClient:
    """为 TEI 客户端统一提供批处理、超时和响应校验。"""

    def __init__(
        self,
        endpoint: HuggingFaceEndpointEmbeddings,
        *,
        model_name: str,
        dimensions: int,
        batch_size: int,
        timeout: int,
    ):
        self.endpoint = endpoint
        self.model_name = model_name
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.timeout = timeout

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for offset in range(0, len(texts), self.batch_size):
            batch = texts[offset : offset + self.batch_size]
            async with observe_external("embedding", "embed_documents"):
                async with asyncio.timeout(self.timeout):
                    batch_embeddings = await self.endpoint.aembed_documents(batch)
            self._validate_batch(batch, batch_embeddings)
            embeddings.extend(batch_embeddings)
        return embeddings

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]

    def _validate_batch(
        self,
        texts: Sequence[str],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if len(embeddings) != len(texts):
            raise EmbeddingContractError(
                "Embedding 返回数量与输入数量不一致："
                f"expected={len(texts)}, actual={len(embeddings)}"
            )
        for index, embedding in enumerate(embeddings):
            if len(embedding) != self.dimensions:
                raise EmbeddingContractError(
                    "Embedding 向量维度不一致："
                    f"index={index}, expected={self.dimensions}, "
                    f"actual={len(embedding)}"
                )
            if not all(math.isfinite(value) for value in embedding):
                raise EmbeddingContractError(
                    f"Embedding 向量包含非有限数值：index={index}"
                )

    async def close(self) -> None:
        self.endpoint.client.close()
        await self.endpoint.async_client.close()


class EmbeddingClientManager:
    """初始化、校验并复用应用级 Embedding 客户端。"""

    def __init__(self, config: EmbeddingConfig, *, dimensions: int):
        self.client: EmbeddingClient | None = None
        self.config = config
        self.dimensions = dimensions

    def _get_url(self) -> str:
        return f"http://{self.config.host}:{self.config.port}"

    def init(self) -> EmbeddingClient:
        if self.client is not None:
            return self.client

        endpoint_url = self._get_url()
        endpoint = HuggingFaceEndpointEmbeddings(model=endpoint_url)
        endpoint.client = InferenceClient(
            model=endpoint_url,
            timeout=self.config.timeout,
        )
        endpoint.async_client = AsyncInferenceClient(
            model=endpoint_url,
            timeout=self.config.timeout,
        )
        self.client = EmbeddingClient(
            endpoint,
            model_name=self.config.model,
            dimensions=self.dimensions,
            batch_size=self.config.batch_size,
            timeout=self.config.timeout,
        )
        logger.info(
            "Embedding 客户端已初始化：model={}, dimensions={}, batch_size={}",
            self.config.model,
            self.dimensions,
            self.config.batch_size,
        )
        return self.client

    def get_client(self) -> EmbeddingClient:
        if self.client is None:
            raise RuntimeError("Embedding 客户端尚未初始化")
        return self.client

    async def close(self) -> None:
        if self.client is None:
            return
        client, self.client = self.client, None
        await client.close()


embedding_client_manager = EmbeddingClientManager(
    app_config.embedding,
    dimensions=app_config.qdrant.embedding_size,
)


if __name__ == "__main__":

    async def test() -> None:
        client = embedding_client_manager.init()
        try:
            query_result = await client.aembed_query("What is deep learning?")
            print(query_result[:3])
        finally:
            await embedding_client_manager.close()

    asyncio.run(test())
