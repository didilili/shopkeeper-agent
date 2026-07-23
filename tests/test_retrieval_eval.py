import asyncio
import math
from pathlib import Path

import pytest

import app.evals.retrieval_eval as retrieval_eval_module
from app.entities.value_info import ValueInfo
from app.evals.retrieval_eval import (
    QualityGate,
    RetrievalEvalCase,
    RetrievalEvalSuite,
    calculate_ranking_metrics,
    describe_retrieval_suite,
    evaluate_retrieval_rankings,
    load_retrieval_eval_suite,
    run_live_retrieval_evals,
)
from app.retrieval.schemas import SearchHit

PROJECT_ROOT = Path(__file__).parents[1]


def test_calculate_ranking_metrics_for_multiple_relevant_items():
    metrics = calculate_ranking_metrics(["a", "b"], ["x", "a", "b"], 3)

    expected_dcg = 1 / math.log2(3) + 1 / math.log2(4)
    expected_idcg = 1 + 1 / math.log2(3)
    assert metrics.recall == 1.0
    assert metrics.mrr == 0.5
    assert metrics.ndcg == pytest.approx(expected_dcg / expected_idcg, abs=1e-4)


def test_duplicate_ranked_ids_do_not_inflate_metrics():
    metrics = calculate_ranking_metrics(["a", "b"], ["a", "a", "x"], 3)

    assert metrics.recall == 0.5
    assert metrics.mrr == 1.0


def test_evaluate_rankings_applies_quality_gate():
    suite = RetrievalEvalSuite(
        version=1,
        k_values=[1, 3],
        quality_gates=[
            QualityGate(domain="overall", metric="recall", k=3, minimum=1.0)
        ],
        cases=[
            RetrievalEvalCase(
                id="column_case",
                domain="column",
                description="test",
                queries=["金额"],
                relevant_ids=["amount"],
            )
        ],
    )

    report = evaluate_retrieval_rankings(suite, {"column_case": ["x", "amount"]})

    assert report.passed is True
    assert report.gates[0].actual == 1.0
    assert report.summaries[0].domain == "overall"


def test_missing_ranking_is_rejected():
    suite = RetrievalEvalSuite(
        version=1,
        k_values=[1],
        cases=[
            RetrievalEvalCase(
                id="metric_case",
                domain="metric",
                description="test",
                queries=["GMV"],
                relevant_ids=["GMV"],
            )
        ],
    )

    with pytest.raises(ValueError, match="缺少评测结果"):
        evaluate_retrieval_rankings(suite, {})


def test_repository_retrieval_suite_is_valid():
    suite = load_retrieval_eval_suite(
        PROJECT_ROOT / "resources/evals/retrieval_cases.yaml"
    )
    description = describe_retrieval_suite(suite)

    assert description["total"] == 13
    assert description["domains"] == {"column": 6, "metric": 2, "value": 5}
    assert description["status"] == "valid"


def test_value_only_live_eval_does_not_initialize_vector_clients(monkeypatch):
    class ForbiddenManager:
        def init(self):
            raise AssertionError("不应初始化向量客户端")

    class FakeESManager:
        client = object()
        closed = False

        def init(self):
            return None

        async def close(self):
            self.closed = True

    class FakeValueRepository:
        def __init__(self, client):
            assert client is fake_es_manager.client

        async def search(self, keyword, *, score_threshold, limit):
            assert keyword == "华东"
            return [
                SearchHit(
                    item=ValueInfo(
                        id="dim_region.region_name.华东",
                        value="华东",
                        column_id="dim_region.region_name",
                    ),
                    score=1.0,
                )
            ]

    fake_es_manager = FakeESManager()
    monkeypatch.setattr(
        retrieval_eval_module, "embedding_client_manager", ForbiddenManager()
    )
    monkeypatch.setattr(
        retrieval_eval_module, "qdrant_client_manager", ForbiddenManager()
    )
    monkeypatch.setattr(retrieval_eval_module, "es_client_manager", fake_es_manager)
    monkeypatch.setattr(retrieval_eval_module, "ValueESRepository", FakeValueRepository)
    suite = RetrievalEvalSuite(
        version=1,
        k_values=[1],
        cases=[
            RetrievalEvalCase(
                id="value_case",
                domain="value",
                description="test",
                queries=["华东"],
                relevant_ids=["dim_region.region_name.华东"],
            )
        ],
    )

    report = asyncio.run(run_live_retrieval_evals(suite))

    assert report.cases[0].metrics[0].recall == 1.0
    assert fake_es_manager.closed is True
