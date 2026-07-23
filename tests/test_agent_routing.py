"""SQL 校验后的有限修正路由测试。"""

from app.agent.routing import route_after_sql_validation


def test_valid_sql_routes_to_execution() -> None:
    assert (
        route_after_sql_validation(
            {"error": None, "correction_attempts": 0},
            max_correction_attempts=2,
        )
        == "run_sql"
    )


def test_invalid_sql_routes_to_correction_within_budget() -> None:
    assert (
        route_after_sql_validation(
            {"error": "unknown column", "correction_attempts": 1},
            max_correction_attempts=2,
        )
        == "correct_sql"
    )


def test_invalid_sql_is_rejected_after_budget_is_exhausted() -> None:
    assert (
        route_after_sql_validation(
            {"error": "unknown column", "correction_attempts": 2},
            max_correction_attempts=2,
        )
        == "reject_sql"
    )


def test_corrected_sql_returns_to_validation_before_execution() -> None:
    from app.agent.graph import graph

    edges = {(edge.source, edge.target) for edge in graph.get_graph().edges}

    assert ("correct_sql", "validate_sql") in edges
    assert ("correct_sql", "run_sql") not in edges
