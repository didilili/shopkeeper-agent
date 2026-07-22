"""检索仓储和融合重排之间使用的通用数据结构。"""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SearchHit(Generic[T]):
    item: T
    score: float


@dataclass(frozen=True)
class RankedCandidate(Generic[T]):
    item: T
    score: float
    matched_queries: tuple[str, ...]
    best_rank: int
    max_source_score: float
