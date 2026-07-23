"""电商问数 Prompt 评测集测试。"""

from pathlib import Path

import pytest

from app.evals.prompt_eval import (
    load_eval_suite,
    run_prompt_evals,
    score_prompt_output,
)

PROJECT_ROOT = Path(__file__).parents[1]
EVAL_SUITE = PROJECT_ROOT / "resources" / "evals" / "prompt_cases.yaml"


def test_offline_eval_suite_passes_all_contracts() -> None:
    suite = load_eval_suite(str(EVAL_SUITE))

    report = run_prompt_evals(suite, mode="offline")

    assert report.total == 10
    assert report.passed == 10
    assert report.failed == 0
    assert report.score == 1


def test_eval_suite_covers_all_registered_prompt_types() -> None:
    suite = load_eval_suite(str(EVAL_SUITE))

    covered_prompts = {case.prompt for case in suite.cases}

    assert covered_prompts == {
        "extend_keywords_for_column_recall",
        "extend_keywords_for_metric_recall",
        "extend_keywords_for_value_recall",
        "filter_metric_info",
        "filter_table_info",
        "generate_sql",
        "correct_sql",
    }


def test_eval_suite_can_filter_single_prompt() -> None:
    suite = load_eval_suite(str(EVAL_SUITE))

    report = run_prompt_evals(suite, mode="offline", prompt_name="generate_sql")

    assert report.total == 2
    assert all(case.prompt == "generate_sql" for case in report.cases)


def test_live_scorer_checks_exact_metric_selection() -> None:
    suite = load_eval_suite(str(EVAL_SUITE))
    case = next(case for case in suite.cases if case.id == "metric_filter_select_gmv")

    assert score_prompt_output(case, ["GMV"]) == ["exact_list"]
    with pytest.raises(AssertionError, match="期望列表"):
        score_prompt_output(case, ["AOV"])


def test_live_scorer_checks_sql_requirements() -> None:
    suite = load_eval_suite(str(EVAL_SUITE))
    case = next(case for case in suite.cases if case.id == "generate_sql_member_aov")
    sql = (
        "SELECT c.member_level, AVG(o.order_amount) AS AOV "
        "FROM fact_order o JOIN dim_customer c "
        "ON o.customer_id = c.customer_id GROUP BY c.member_level"
    )

    checks = score_prompt_output(case, sql)

    assert checks == ["sql_contains", "sql_excludes"]
