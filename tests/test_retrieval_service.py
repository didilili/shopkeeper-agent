"""批量向量化、稳定去重和并发检索测试。"""

import asyncio
from dataclasses import dataclass

import pytest

from app.config.app_config import RetrievalDomainConfig
from app.retrieval.errors import RetrievalError
from app.retrieval.schemas import SearchHit
from app.retrieval.service import (
    retrieve_text_candidates,
    retrieve_vector_candidates,
    stable_unique,
)


@dataclass(frozen=True)
class Item:
    id: str
    name: str


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(index)] for index, _ in enumerate(texts, start=1)]


def retrieval_config() -> RetrievalDomainConfig:
    return RetrievalDomainConfig(
        score_threshold=0.6,
        per_query_limit=5,
        final_limit=5,
        rrf_k=60,
        exact_match_boost=0.05,
    )


def test_stable_unique_preserves_first_occurrence() -> None:
    assert stable_unique([" GMV ", "成交额", "GMV", ""]) == ["GMV", "成交额"]


def test_stable_unique_applies_limit_after_deduplication() -> None:
    assert stable_unique(["GMV", "GMV", "成交额", "销售额"], limit=2) == [
        "GMV",
        "成交额",
    ]


def test_vector_retrieval_batches_embeddings_and_runs_searches_concurrently() -> None:
    embeddings = FakeEmbeddings()
    active = 0
    max_active = 0

    async def search(vector, *, score_threshold, limit):
        nonlocal active, max_active
        assert score_threshold == 0.6
        assert limit == 5
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        item = Item(str(int(vector[0])), f"item-{int(vector[0])}")
        return [SearchHit(item, 0.8)]

    ranked = asyncio.run(
        retrieve_vector_candidates(
            ["销售额", "成交额", "销售额"],
            embedding_client=embeddings,
            search=search,
            config=retrieval_config(),
            max_concurrency=2,
            max_queries=12,
            key=lambda item: item.id,
            searchable_terms=lambda item: [item.name],
        )
    )

    assert embeddings.calls == [["销售额", "成交额"]]
    assert max_active == 2
    assert len(ranked) == 2


def test_text_retrieval_keeps_partial_results_when_one_query_fails() -> None:
    async def search(query, *, score_threshold, limit):
        if query == "bad":
            raise ConnectionError("temporary outage")
        return [SearchHit(Item(query, query), 0.8)]

    ranked = asyncio.run(
        retrieve_text_candidates(
            ["good", "bad"],
            search=search,
            config=retrieval_config(),
            max_concurrency=2,
            max_queries=12,
            key=lambda item: item.id,
            searchable_terms=lambda item: [item.name],
        )
    )

    assert [candidate.item.id for candidate in ranked] == ["good"]


def test_text_retrieval_raises_domain_error_when_all_queries_fail() -> None:
    async def search(query, *, score_threshold, limit):
        raise ConnectionError(f"{query} unavailable")

    with pytest.raises(RetrievalError, match="全部召回子查询失败"):
        asyncio.run(
            retrieve_text_candidates(
                ["first", "second"],
                search=search,
                config=retrieval_config(),
                max_concurrency=2,
                max_queries=12,
                key=lambda item: item.id,
                searchable_terms=lambda item: [item.name],
            )
        )


def test_vector_retrieval_rejects_incomplete_embedding_response() -> None:
    class IncompleteEmbeddings:
        async def aembed_documents(self, texts):
            return [[1.0]]

    async def search(vector, *, score_threshold, limit):
        return []

    with pytest.raises(RetrievalError, match="Embedding 返回数量"):
        asyncio.run(
            retrieve_vector_candidates(
                ["first", "second"],
                embedding_client=IncompleteEmbeddings(),
                search=search,
                config=retrieval_config(),
                max_concurrency=2,
                max_queries=12,
                key=lambda item: item.id,
                searchable_terms=lambda item: [item.name],
            )
        )
