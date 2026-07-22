"""模型选择结果与候选上下文交叉验证测试。"""

import pytest

from app.prompt.errors import PromptOutputError
from app.prompt.validators import validate_name_selection, validate_table_selection


def test_metric_selection_rejects_unknown_name() -> None:
    candidates = [{"name": "销售额"}, {"name": "订单量"}]

    with pytest.raises(PromptOutputError, match="退款率"):
        validate_name_selection(["销售额", "退款率"], candidates, label="指标")


def test_table_selection_rejects_unknown_column() -> None:
    candidates = [
        {
            "name": "fact_order",
            "columns": [{"name": "order_id"}, {"name": "amount"}],
        }
    ]

    with pytest.raises(PromptOutputError, match="user_password"):
        validate_table_selection(
            {"fact_order": ["order_id", "user_password"]}, candidates
        )


def test_valid_table_selection_passes() -> None:
    candidates = [
        {
            "name": "fact_order",
            "columns": [{"name": "order_id"}, {"name": "amount"}],
        }
    ]

    validate_table_selection({"fact_order": ["amount"]}, candidates)
