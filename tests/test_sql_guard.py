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
