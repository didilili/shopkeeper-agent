"""查询接口输入边界测试。"""

import pytest
from pydantic import ValidationError

from app.api.schemas.query_schema import QuerySchema


def test_query_is_trimmed() -> None:
    assert QuerySchema(query="  查询销售额  ").query == "查询销售额"


@pytest.mark.parametrize("query", ["", "   ", "x" * 2001])
def test_query_rejects_empty_or_overlong_input(query: str) -> None:
    with pytest.raises(ValidationError):
        QuerySchema(query=query)
