"""批量向量化、受控并发检索和融合重排服务。"""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.conf.app_config import RetrievalDomainConfig
from app.retrieval.fusion import fuse_rankings
from app.retrieval.schemas import RankedCandidate, SearchHit

T = TypeVar("T")


def stable_unique(values: Iterable[str]) -> list[str]:
    """清理空白并按首次出现顺序去重。"""

    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


async def retrieve_vector_candidates(
    queries: Iterable[str],
    *,
    embedding_client: HuggingFaceEndpointEmbeddings,
    search: Callable[..., Awaitable[list[SearchHit[T]]]],
    config: RetrievalDomainConfig,
    max_concurrency: int,
    key: Callable[[T], str],
    searchable_terms: Callable[[T], Iterable[str]],
) -> list[RankedCandidate[T]]:
    unique_queries = stable_unique(queries)
    if not unique_queries:
        return []

    embeddings = await embedding_client.aembed_documents(unique_queries)
    semaphore = asyncio.Semaphore(max_concurrency)

    async def search_one(
        query: str, embedding: list[float]
    ) -> tuple[str, list[SearchHit[T]]]:
        async with semaphore:
            hits = await search(
                embedding,
                score_threshold=config.score_threshold,
                limit=config.per_query_limit,
            )
        return query, hits

    query_results = await asyncio.gather(
        *(
            search_one(query, embedding)
            for query, embedding in zip(unique_queries, embeddings)
        )
    )
    return fuse_rankings(
        query_results,
        key=key,
        searchable_terms=searchable_terms,
        rrf_k=config.rrf_k,
        exact_match_boost=config.exact_match_boost,
        final_limit=config.final_limit,
    )


async def retrieve_text_candidates(
    queries: Iterable[str],
    *,
    search: Callable[..., Awaitable[list[SearchHit[T]]]],
    config: RetrievalDomainConfig,
    max_concurrency: int,
    key: Callable[[T], str],
    searchable_terms: Callable[[T], Iterable[str]],
) -> list[RankedCandidate[T]]:
    unique_queries = stable_unique(queries)
    if not unique_queries:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def search_one(query: str) -> tuple[str, list[SearchHit[T]]]:
        async with semaphore:
            hits = await search(
                query,
                score_threshold=config.score_threshold,
                limit=config.per_query_limit,
            )
        return query, hits

    query_results = await asyncio.gather(
        *(search_one(query) for query in unique_queries)
    )
    return fuse_rankings(
        query_results,
        key=key,
        searchable_terms=searchable_terms,
        rrf_k=config.rrf_k,
        exact_match_boost=config.exact_match_boost,
        final_limit=config.final_limit,
    )
