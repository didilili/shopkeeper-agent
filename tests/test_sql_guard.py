"""SQL 执行边界的只读安全策略测试。"""

import pytest

from app.security.sql_guard import SQLGuard, SQLSafetyError


@pytest.fixture
def guard() -> SQLGuard:
    return SQLGuard(max_sql_length=200)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT order_id FROM fact_order",
        "WITH recent AS (SELECT 1 AS id) SELECT id FROM recent;",
        "SELECT 'DROP TABLE is plain text' AS description",
    ],
)
def test_guard_accepts_readonly_single_query(guard: SQLGuard, sql: str) -> None:
    assert guard.validate(sql).startswith(("SELECT", "WITH"))


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; SELECT 2",
        "SELECT * FROM fact_order -- bypass",
        "WITH changed AS (DELETE FROM fact_order) SELECT 1",
        "SELECT SLEEP(10)",
        "SELECT LOAD_FILE('/etc/passwd')",
        "SELECT * FROM fact_order INTO OUTFILE '/tmp/orders'",
        "SELECT * FROM fact_order FOR UPDATE",
        "SELECT * FROM information_schema.tables",
    ],
)
def test_guard_rejects_high_risk_sql(guard: SQLGuard, sql: str) -> None:
    with pytest.raises(SQLSafetyError):
        guard.validate(sql)


def test_guard_rejects_overlong_sql(guard: SQLGuard) -> None:
    with pytest.raises(SQLSafetyError, match="长度超过限制"):
        guard.validate("SELECT " + "x" * 200)


def test_guard_allows_only_tables_in_query_scope() -> None:
    guard = SQLGuard(max_sql_length=500, allowed_schema="dw_test")

    sql = (
        "SELECT f.order_id FROM dw_test.fact_order f "
        "JOIN dim_date d ON f.date_id = d.date_id"
    )

    assert (
        guard.validate(
            sql,
            allowed_tables={"fact_order", "dim_date"},
        )
        == sql
    )


def test_guard_rejects_unauthorized_join_table() -> None:
    guard = SQLGuard(max_sql_length=500, allowed_schema="dw_test")

    with pytest.raises(SQLSafetyError, match="dim_customer"):
        guard.validate(
            "SELECT * FROM fact_order JOIN dim_customer USING (customer_id)",
            allowed_tables={"fact_order"},
        )


def test_guard_excludes_cte_aliases_from_real_table_scope() -> None:
    guard = SQLGuard(max_sql_length=500, allowed_schema="dw_test")
    sql = "WITH recent AS (SELECT order_id FROM fact_order) SELECT order_id FROM recent"

    assert guard.validate(sql, allowed_tables={"fact_order"}) == sql


def test_guard_rejects_other_schema_even_when_table_name_matches() -> None:
    guard = SQLGuard(max_sql_length=500, allowed_schema="dw_test")

    with pytest.raises(SQLSafetyError, match="other.fact_order"):
        guard.validate(
            "SELECT * FROM other.fact_order",
            allowed_tables={"fact_order"},
        )
