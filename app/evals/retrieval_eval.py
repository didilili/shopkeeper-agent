"""召回评测集模型、排名指标与在线执行器。"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.conf.app_config import app_config
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.retrieval.service import (
    retrieve_text_candidates,
    retrieve_vector_candidates,
)

RetrievalDomain = Literal["column", "metric", "value"]
MetricName = Literal["recall", "mrr", "ndcg"]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RetrievalEvalCase(FrozenModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    domain: RetrievalDomain
    description: str = Field(min_length=1)
    queries: list[str] = Field(min_length=1)
    relevant_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_values(self):
        if len(self.queries) != len(set(self.queries)):
            raise ValueError("queries 不允许重复")
        if len(self.relevant_ids) != len(set(self.relevant_ids)):
            raise ValueError("relevant_ids 不允许重复")
        return self


class QualityGate(FrozenModel):
    domain: RetrievalDomain | Literal["overall"] = "overall"
    metric: MetricName
    k: int = Field(gt=0)
    minimum: float = Field(ge=0, le=1)


class RetrievalEvalSuite(FrozenModel):
    version: Literal[1]
    k_values: list[int] = Field(min_length=1)
    quality_gates: list[QualityGate] = Field(default_factory=list)
    cases: list[RetrievalEvalCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_suite(self):
        if self.k_values != sorted(set(self.k_values)) or any(
            value <= 0 for value in self.k_values
        ):
            raise ValueError("k_values 必须是升序且不重复的正整数")
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("评测 case id 不允许重复")
        unknown_k = {gate.k for gate in self.quality_gates} - set(self.k_values)
        if unknown_k:
            raise ValueError(f"质量门禁使用了未声明的 K：{sorted(unknown_k)}")
        return self


class CutoffMetrics(FrozenModel):
    k: int
    recall: float
    mrr: float
    ndcg: float


class RetrievalCaseResult(FrozenModel):
    id: str
    domain: RetrievalDomain
    ranked_ids: list[str]
    relevant_ids: list[str]
    metrics: list[CutoffMetrics]


class RetrievalSummary(FrozenModel):
    domain: RetrievalDomain | Literal["overall"]
    cases: int
    metrics: list[CutoffMetrics]


class QualityGateResult(FrozenModel):
    gate: QualityGate
    actual: float
    passed: bool


class RetrievalEvalReport(FrozenModel):
    mode: Literal["live"] = "live"
    total: int
    summaries: list[RetrievalSummary]
    gates: list[QualityGateResult]
    passed: bool
    cases: list[RetrievalCaseResult]


def load_retrieval_eval_suite(path: str | Path) -> RetrievalEvalSuite:
    with Path(path).open(encoding="utf-8") as file:
        return RetrievalEvalSuite.model_validate(yaml.safe_load(file))


def calculate_ranking_metrics(
    relevant_ids: list[str], ranked_ids: list[str], k: int
) -> CutoffMetrics:
    """计算二元相关性下的 Recall@K、MRR@K 和 nDCG@K。"""

    relevant = set(relevant_ids)
    ranking = list(dict.fromkeys(ranked_ids))[:k]
    hits = [1 if item_id in relevant else 0 for item_id in ranking]
    recall = sum(hits) / len(relevant)

    first_hit = next((index for index, hit in enumerate(hits, start=1) if hit), None)
    mrr = 1 / first_hit if first_hit else 0.0

    dcg = sum(hit / math.log2(rank + 1) for rank, hit in enumerate(hits, start=1))
    ideal_hits = min(len(relevant), k)
    idcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    ndcg = dcg / idcg if idcg else 0.0

    return CutoffMetrics(
        k=k,
        recall=round(recall, 4),
        mrr=round(mrr, 4),
        ndcg=round(ndcg, 4),
    )


def evaluate_retrieval_rankings(
    suite: RetrievalEvalSuite, rankings: dict[str, list[str]]
) -> RetrievalEvalReport:
    missing = {case.id for case in suite.cases} - set(rankings)
    if missing:
        raise ValueError(f"缺少评测结果：{sorted(missing)}")

    results = [
        RetrievalCaseResult(
            id=case.id,
            domain=case.domain,
            ranked_ids=list(dict.fromkeys(rankings[case.id])),
            relevant_ids=case.relevant_ids,
            metrics=[
                calculate_ranking_metrics(case.relevant_ids, rankings[case.id], cutoff)
                for cutoff in suite.k_values
            ],
        )
        for case in suite.cases
    ]
    summaries = [_summarize("overall", results, suite.k_values)]
    summaries.extend(
        _summarize(domain, results, suite.k_values)
        for domain in ("column", "metric", "value")
        if any(result.domain == domain for result in results)
    )

    summary_lookup = {summary.domain: summary for summary in summaries}
    gates: list[QualityGateResult] = []
    for gate in suite.quality_gates:
        summary = summary_lookup[gate.domain]
        cutoff = next(metric for metric in summary.metrics if metric.k == gate.k)
        actual = getattr(cutoff, gate.metric)
        gates.append(
            QualityGateResult(
                gate=gate,
                actual=actual,
                passed=actual >= gate.minimum,
            )
        )

    return RetrievalEvalReport(
        total=len(results),
        summaries=summaries,
        gates=gates,
        passed=all(gate.passed for gate in gates),
        cases=results,
    )


def _summarize(
    domain: RetrievalDomain | Literal["overall"],
    results: list[RetrievalCaseResult],
    k_values: list[int],
) -> RetrievalSummary:
    selected = [
        result for result in results if domain == "overall" or result.domain == domain
    ]
    metrics: list[CutoffMetrics] = []
    for cutoff in k_values:
        values = [
            next(metric for metric in result.metrics if metric.k == cutoff)
            for result in selected
        ]
        metrics.append(
            CutoffMetrics(
                k=cutoff,
                recall=round(sum(value.recall for value in values) / len(values), 4),
                mrr=round(sum(value.mrr for value in values) / len(values), 4),
                ndcg=round(sum(value.ndcg for value in values) / len(values), 4),
            )
        )
    return RetrievalSummary(domain=domain, cases=len(selected), metrics=metrics)


def describe_retrieval_suite(suite: RetrievalEvalSuite) -> dict:
    """离线验证后返回可读的数据集摘要。"""

    return {
        "version": suite.version,
        "total": len(suite.cases),
        "domains": dict(Counter(case.domain for case in suite.cases)),
        "k_values": suite.k_values,
        "quality_gates": len(suite.quality_gates),
        "status": "valid",
    }


async def run_live_retrieval_evals(
    suite: RetrievalEvalSuite,
) -> RetrievalEvalReport:
    """连接真实 Embedding、Qdrant 和 Elasticsearch 执行评测。"""

    domains = {case.domain for case in suite.cases}
    needs_vector = bool(domains & {"column", "metric"})
    needs_text = "value" in domains
    qdrant_initialized = False
    es_initialized = False
    rankings: dict[str, list[str]] = {}

    try:
        column_repository = None
        metric_repository = None
        value_repository = None
        embedding_client = None

        if needs_vector:
            embedding_client_manager.init()
            qdrant_client_manager.init()
            qdrant_initialized = True
            embedding_client = embedding_client_manager.client
            qdrant_client = qdrant_client_manager.client
            if embedding_client is None or qdrant_client is None:
                raise RuntimeError("向量召回客户端初始化失败")
            column_repository = ColumnQdrantRepository(qdrant_client)
            metric_repository = MetricQdrantRepository(qdrant_client)

        if needs_text:
            es_client_manager.init()
            es_initialized = True
            es_client = es_client_manager.client
            if es_client is None:
                raise RuntimeError("全文召回客户端初始化失败")
            value_repository = ValueESRepository(es_client)

        for case in suite.cases:
            if case.domain == "column":
                if embedding_client is None or column_repository is None:
                    raise RuntimeError("字段召回依赖未初始化")
                candidates = await retrieve_vector_candidates(
                    case.queries,
                    embedding_client=embedding_client,
                    search=column_repository.search,
                    config=app_config.retrieval.column,
                    max_concurrency=app_config.retrieval.max_concurrency,
                    key=lambda item: item.id,
                    searchable_terms=lambda item: [item.name, *item.alias],
                )
            elif case.domain == "metric":
                if embedding_client is None or metric_repository is None:
                    raise RuntimeError("指标召回依赖未初始化")
                candidates = await retrieve_vector_candidates(
                    case.queries,
                    embedding_client=embedding_client,
                    search=metric_repository.search,
                    config=app_config.retrieval.metric,
                    max_concurrency=app_config.retrieval.max_concurrency,
                    key=lambda item: item.id,
                    searchable_terms=lambda item: [item.name, *item.alias],
                )
            else:
                if value_repository is None:
                    raise RuntimeError("值域召回依赖未初始化")
                candidates = await retrieve_text_candidates(
                    case.queries,
                    search=value_repository.search,
                    config=app_config.retrieval.value,
                    max_concurrency=app_config.retrieval.max_concurrency,
                    key=lambda item: item.id,
                    searchable_terms=lambda item: [item.value],
                )
            rankings[case.id] = [candidate.item.id for candidate in candidates]
    finally:
        if qdrant_initialized:
            await qdrant_client_manager.close()
        if es_initialized:
            await es_client_manager.close()

    return evaluate_retrieval_rankings(suite, rankings)
