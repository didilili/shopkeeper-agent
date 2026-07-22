"""验证召回评测集或连接真实检索服务执行效果评测。"""

import argparse
import asyncio
import json
from pathlib import Path

from app.evals.retrieval_eval import (
    RetrievalEvalSuite,
    describe_retrieval_suite,
    load_retrieval_eval_suite,
    run_live_retrieval_evals,
)

PROJECT_ROOT = Path(__file__).parents[2]
DEFAULT_SUITE = PROJECT_ROOT / "evals" / "retrieval_cases.yaml"


def _filter_domain(suite: RetrievalEvalSuite, domain: str | None) -> RetrievalEvalSuite:
    if domain is None:
        return suite
    cases = [case for case in suite.cases if case.domain == domain]
    gates = [gate for gate in suite.quality_gates if gate.domain in {"overall", domain}]
    return suite.model_copy(update={"cases": cases, "quality_gates": gates})


def main() -> None:
    parser = argparse.ArgumentParser(description="运行电商问数召回评测")
    parser.add_argument("--mode", choices=["validate", "live"], default="validate")
    parser.add_argument("--suite", default=str(DEFAULT_SUITE))
    parser.add_argument("--domain", choices=["column", "metric", "value"])
    parser.add_argument("--output", help="可选的 JSON 报告保存路径")
    args = parser.parse_args()

    suite = _filter_domain(load_retrieval_eval_suite(args.suite), args.domain)
    if args.mode == "validate":
        payload = describe_retrieval_suite(suite)
        exit_code = 0
    else:
        report = asyncio.run(run_live_retrieval_evals(suite))
        payload = report.model_dump()
        exit_code = 0 if report.passed else 1

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    print(serialized)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized + "\n", encoding="utf-8")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
