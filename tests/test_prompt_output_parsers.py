"""Prompt 强类型输出和只读 SQL 安全测试。"""

import pytest

from app.prompt.errors import PromptOutputError
from app.prompt.output_parsers import (
    ReadOnlySQLOutputParser,
    StringListOutputParser,
    TableSelectionOutputParser,
)


def test_string_list_is_normalized_and_deduplicated() -> None:
    parser = StringListOutputParser()

    result = parser.parse('["销售额", " 销售额 ", "GMV"]')

    assert result == ["销售额", "GMV"]


def test_empty_selections_are_allowed() -> None:
    assert StringListOutputParser().parse("[]") == []
    assert TableSelectionOutputParser().parse("{}") == {}


def test_table_selection_requires_non_empty_columns() -> None:
    parser = TableSelectionOutputParser()

    with pytest.raises(PromptOutputError, match="表字段选择对象"):
        parser.parse('{"fact_order": []}')


@pytest.mark.parametrize(
    ("raw_sql", "expected"),
    [
        ("SELECT 1;", "SELECT 1"),
        ("```sql\nSELECT * FROM fact_order\n```", "SELECT * FROM fact_order"),
        (
            "WITH recent AS (SELECT * FROM fact_order) SELECT * FROM recent",
            "WITH recent AS (SELECT * FROM fact_order) SELECT * FROM recent",
        ),
    ],
)
def test_readonly_sql_accepts_single_query(raw_sql: str, expected: str) -> None:
    assert ReadOnlySQLOutputParser().parse(raw_sql) == expected


@pytest.mark.parametrize(
    "unsafe_sql",
    [
        "DELETE FROM fact_order",
        "SELECT * FROM fact_order; DROP TABLE fact_order",
        "UPDATE fact_order SET amount = 0",
        "SELECT SLEEP(10)",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM fact_order -- ignore policy",
        "这里是查询结果：SELECT 1",
    ],
)
def test_readonly_sql_rejects_unsafe_output(unsafe_sql: str) -> None:
    with pytest.raises(PromptOutputError):
        ReadOnlySQLOutputParser().parse(unsafe_sql)
