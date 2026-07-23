"""数仓仓储 SQL 安全、超时配置和结果上限测试。"""

import asyncio

import pytest

from app.config.app_config import SQLExecutionConfig
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.security.sql_guard import SQLSafetyError


class FakeMappings:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def fetchmany(self, size: int):
        return self.rows[:size]


class FakeResult:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def mappings(self):
        return FakeMappings(self.rows)


class FakeSession:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []
        self.executed: list[str] = []

    async def execute(self, statement):
        self.executed.append(str(statement))
        return FakeResult(self.rows)


class SlowSession(FakeSession):
    async def execute(self, statement):
        await asyncio.sleep(0.05)
        return await super().execute(statement)


def execution_config(**overrides) -> SQLExecutionConfig:
    values = {
        "max_sql_length": 500,
        "max_result_rows": 2,
        "query_timeout_seconds": 1,
        "max_correction_attempts": 2,
    }
    values.update(overrides)
    return SQLExecutionConfig(**values)


def test_validate_runs_guard_before_explain() -> None:
    session = FakeSession()
    repository = DWMySQLRepository(session, execution_config())

    asyncio.run(repository.validate("SELECT 1"))

    assert session.executed == ["explain SELECT 1"]


def test_run_rechecks_guard_and_never_executes_unsafe_sql() -> None:
    session = FakeSession()
    repository = DWMySQLRepository(session, execution_config())

    with pytest.raises(SQLSafetyError):
        asyncio.run(repository.run("SELECT SLEEP(10)"))

    assert session.executed == []


def test_run_truncates_rows_at_configured_limit() -> None:
    session = FakeSession([{"id": 1}, {"id": 2}, {"id": 3}])
    repository = DWMySQLRepository(session, execution_config(max_result_rows=2))

    rows = asyncio.run(repository.run("SELECT id FROM fact_order"))

    assert rows == [{"id": 1}, {"id": 2}]
    assert session.executed == ["SELECT id FROM fact_order"]


def test_run_enforces_application_timeout() -> None:
    repository = DWMySQLRepository(
        SlowSession(),
        execution_config(query_timeout_seconds=0.01),
    )

    with pytest.raises(TimeoutError):
        asyncio.run(repository.run("SELECT id FROM fact_order"))
