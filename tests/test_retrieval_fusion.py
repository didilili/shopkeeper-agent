"""多查询候选融合与重排序测试。"""

from dataclasses import dataclass

from app.retrieval.fusion import fuse_rankings
from app.retrieval.schemas import SearchHit


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    aliases: tuple[str, ...] = ()


def test_candidate_matched_by_multiple_queries_ranks_first() -> None:
    first = Item("a", "订单金额")
    second = Item("b", "购买数量")
    third = Item("c", "商品品类")
    query_results = [
        ("销售额", [SearchHit(first, 0.9), SearchHit(second, 0.8)]),
        ("成交金额", [SearchHit(first, 0.85), SearchHit(third, 0.82)]),
    ]

    ranked = fuse_rankings(
        query_results,
        key=lambda item: item.id,
        searchable_terms=lambda item: [item.name, *item.aliases],
        rrf_k=60,
        exact_match_boost=0.05,
        final_limit=10,
    )

    assert ranked[0].item == first
    assert ranked[0].matched_queries == ("销售额", "成交金额")
    assert ranked[0].best_rank == 1


def test_exact_name_or_alias_receives_boost() -> None:
    generic = Item("a", "成交金额")
    exact = Item("b", "Gross Merchandise Value", ("GMV",))
    query_results = [
        ("GMV", [SearchHit(generic, 0.95), SearchHit(exact, 0.8)]),
    ]

    ranked = fuse_rankings(
        query_results,
        key=lambda item: item.id,
        searchable_terms=lambda item: [item.name, *item.aliases],
        rrf_k=60,
        exact_match_boost=0.05,
        final_limit=10,
    )

    assert ranked[0].item == exact


def test_duplicate_vector_points_only_contribute_once_per_query() -> None:
    first = Item("a", "订单金额")
    duplicated = Item("b", "购买数量")
    query_results = [
        (
            "成交金额",
            [
                SearchHit(first, 0.9),
                SearchHit(duplicated, 0.8),
                SearchHit(duplicated, 0.7),
                SearchHit(duplicated, 0.6),
            ],
        )
    ]

    ranked = fuse_rankings(
        query_results,
        key=lambda item: item.id,
        searchable_terms=lambda item: [item.name],
        rrf_k=60,
        exact_match_boost=0,
        final_limit=10,
    )

    assert [candidate.item.id for candidate in ranked] == ["a", "b"]
    assert ranked[1].best_rank == 2


def test_ties_are_deterministic_and_final_limit_is_applied() -> None:
    query_results = [
        ("first-query", [SearchHit(Item("b", "B"), 0.8)]),
        ("second-query", [SearchHit(Item("a", "A"), 0.8)]),
    ]

    ranked = fuse_rankings(
        query_results,
        key=lambda item: item.id,
        searchable_terms=lambda item: [item.name],
        rrf_k=60,
        exact_match_boost=0,
        final_limit=1,
    )

    assert [candidate.item.id for candidate in ranked] == ["a"]
