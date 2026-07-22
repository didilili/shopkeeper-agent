"""运行 Prompt 评测集并输出 JSON 报告。"""

import argparse
import json
from pathlib import Path

from app.evals.prompt_eval import load_eval_suite, run_prompt_evals

PROJECT_ROOT = Path(__file__).parents[2]
DEFAULT_SUITE = PROJECT_ROOT / "evals" / "prompt_cases.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="运行电商问数 Prompt 评测")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--suite", default=str(DEFAULT_SUITE))
    parser.add_argument("--prompt", help="只评测指定 Prompt")
    args = parser.parse_args()

    suite = load_eval_suite(args.suite)
    report = run_prompt_evals(suite, mode=args.mode, prompt_name=args.prompt)
    print(json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
