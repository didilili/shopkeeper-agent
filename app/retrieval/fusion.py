"""使用 Reciprocal Rank Fusion 融合多个查询的候选排名。"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from app.retrieval.schemas import RankedCandidate, SearchHit

T = TypeVar("T")


@dataclass
class _Accumulator(Generic[T]):
    item: T
    rrf_score: float = 0
    matched_queries: list[str] = field(default_factory=list)
    best_rank: int = 2**31 - 1
    max_source_score: float = float("-inf")


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def fuse_rankings(
    query_results: Sequence[tuple[str, Sequence[SearchHit[T]]]],
    *,
    key: Callable[[T], str],
    searchable_terms: Callable[[T], Iterable[str]],
    rrf_k: int,
    exact_match_boost: float,
    final_limit: int,
) -> list[RankedCandidate[T]]:
    """按稳定 id 去重，并融合候选在不同查询中的排名。"""

    accumulators: dict[str, _Accumulator[T]] = {}
    for query, hits in query_results:
        for rank, hit in enumerate(hits, start=1):
            item_key = key(hit.item)
            accumulator = accumulators.setdefault(item_key, _Accumulator(item=hit.item))
            accumulator.rrf_score += 1 / (rrf_k + rank)
            if query not in accumulator.matched_queries:
                accumulator.matched_queries.append(query)
            accumulator.best_rank = min(accumulator.best_rank, rank)
            accumulator.max_source_score = max(accumulator.max_source_score, hit.score)

    ranked: list[RankedCandidate[T]] = []
    for accumulator in accumulators.values():
        terms = {
            _normalize(term) for term in searchable_terms(accumulator.item) if term
        }
        exact_match = any(
            _normalize(query) in terms for query in accumulator.matched_queries
        )
        score = accumulator.rrf_score + (exact_match_boost if exact_match else 0)
        ranked.append(
            RankedCandidate(
                item=accumulator.item,
                score=score,
                matched_queries=tuple(accumulator.matched_queries),
                best_rank=accumulator.best_rank,
                max_source_score=accumulator.max_source_score,
            )
        )

    ranked.sort(
        key=lambda candidate: (
            -candidate.score,
            candidate.best_rank,
            -candidate.max_source_score,
            key(candidate.item),
        )
    )
    return ranked[:final_limit]
