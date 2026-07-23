"""批量向量化、受控并发检索和融合重排服务。"""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

from app.clients.embedding_client_manager import EmbeddingClient
from app.config.app_config import RetrievalDomainConfig
from app.core.log import logger
from app.retrieval.errors import RetrievalError
from app.retrieval.fusion import fuse_rankings
from app.retrieval.schemas import RankedCandidate, SearchHit

T = TypeVar("T")


def stable_unique(values: Iterable[str], *, limit: int | None = None) -> list[str]:
    """清理空白、按首次出现顺序去重，并可限制最终数量。"""

    unique_values = list(
        dict.fromkeys(value.strip() for value in values if value.strip())
    )
    return unique_values[:limit]


def _successful_query_results(
    queries: list[str],
    results: list[tuple[str, list[SearchHit[T]]] | BaseException],
) -> list[tuple[str, list[SearchHit[T]]]]:
    """保留成功查询；部分失败时降级，全部失败时中止召回。"""

    successful: list[tuple[str, list[SearchHit[T]]]] = []
    failures: list[tuple[str, Exception]] = []
    for query, result in zip(queries, results, strict=True):
        if isinstance(result, asyncio.CancelledError):
            raise result
        if isinstance(result, Exception):
            failures.append((query, result))
        elif isinstance(result, BaseException):
            raise result
        else:
            successful.append(result)

    if failures:
        logger.warning(
            "召回子查询失败：failure_count={}, error_types={}",
            len(failures),
            sorted({type(error).__name__ for _, error in failures}),
        )
    if not successful:
        raise RetrievalError("全部召回子查询失败") from failures[0][1]
    return successful


async def retrieve_vector_candidates(
    queries: Iterable[str],
    *,
    embedding_client: EmbeddingClient,
    search: Callable[..., Awaitable[list[SearchHit[T]]]],
    config: RetrievalDomainConfig,
    max_concurrency: int,
    max_queries: int,
    key: Callable[[T], str],
    searchable_terms: Callable[[T], Iterable[str]],
) -> list[RankedCandidate[T]]:
    unique_queries = stable_unique(queries, limit=max_queries)
    if not unique_queries:
        return []

    embeddings = await embedding_client.aembed_documents(unique_queries)
    if len(embeddings) != len(unique_queries):
        raise RetrievalError(
            "Embedding 返回数量与查询词数量不一致："
            f"expected={len(unique_queries)}, actual={len(embeddings)}"
        )
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

    raw_results = await asyncio.gather(
        *(
            search_one(query, embedding)
            for query, embedding in zip(unique_queries, embeddings, strict=True)
        ),
        return_exceptions=True,
    )
    query_results = _successful_query_results(unique_queries, raw_results)
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
    max_queries: int,
    key: Callable[[T], str],
    searchable_terms: Callable[[T], Iterable[str]],
) -> list[RankedCandidate[T]]:
    unique_queries = stable_unique(queries, limit=max_queries)
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

    raw_results = await asyncio.gather(
        *(search_one(query) for query in unique_queries),
        return_exceptions=True,
    )
    query_results = _successful_query_results(unique_queries, raw_results)
    return fuse_rankings(
        query_results,
        key=key,
        searchable_terms=searchable_terms,
        rrf_k=config.rrf_k,
        exact_match_boost=config.exact_match_boost,
        final_limit=config.final_limit,
    )
