"""Prompt 离线契约评测和可选在线语义评测。"""

from __future__ import annotations

from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.prompt.factory import build_chat_prompt, build_prompt_chain
from app.prompt.registry import get_prompt_definition


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExpectedResult(FrozenModel):
    exact_list: list[str] | None = None
    required_concepts: list[list[str]] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    required_mapping: dict[str, list[str]] = Field(default_factory=dict)
    forbidden_keys: list[str] = Field(default_factory=list)
    sql_contains: list[str] = Field(default_factory=list)
    sql_excludes: list[str] = Field(default_factory=list)


class PromptEvalCase(FrozenModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    prompt: str
    description: str
    inputs: dict[str, str]
    expected: ExpectedResult


class PromptEvalSuite(FrozenModel):
    version: Literal[1]
    fixtures: dict[str, Any] = Field(default_factory=dict)
    cases: list[PromptEvalCase]


class CaseResult(FrozenModel):
    id: str
    prompt: str
    passed: bool
    checks: list[str]
    error: str | None = None
    output: Any = None


class EvalReport(FrozenModel):
    mode: Literal["offline", "live"]
    total: int
    passed: int
    failed: int
    score: float
    cases: list[CaseResult]


def load_eval_suite(path: str) -> PromptEvalSuite:
    with open(path, encoding="utf-8") as file:
        return PromptEvalSuite.model_validate(yaml.safe_load(file))


def _contains_concept(output: list[str], alternatives: list[str]) -> bool:
    normalized_output = [item.casefold() for item in output]
    return any(
        alternative.casefold() in item or item in alternative.casefold()
        for alternative in alternatives
        for item in normalized_output
    )


def score_prompt_output(case: PromptEvalCase, output: Any) -> list[str]:
    expected = case.expected
    checks: list[str] = []

    if expected.exact_list is not None:
        if not isinstance(output, list) or set(output) != set(expected.exact_list):
            raise AssertionError(f"期望列表 {expected.exact_list}，实际为 {output}")
        checks.append("exact_list")

    if expected.required_concepts:
        if not isinstance(output, list):
            raise AssertionError("required_concepts 只能用于列表输出")
        for alternatives in expected.required_concepts:
            if not _contains_concept(output, alternatives):
                raise AssertionError(f"缺少概念组：{alternatives}")
        checks.append("required_concepts")

    if expected.forbidden_terms:
        serialized = str(output).casefold()
        found = [
            term for term in expected.forbidden_terms if term.casefold() in serialized
        ]
        if found:
            raise AssertionError(f"包含禁止内容：{found}")
        checks.append("forbidden_terms")

    if expected.required_mapping:
        if not isinstance(output, dict):
            raise AssertionError("required_mapping 只能用于对象输出")
        for table, columns in expected.required_mapping.items():
            if table not in output or not set(columns).issubset(set(output[table])):
                raise AssertionError(f"缺少表字段：{table} -> {columns}")
        checks.append("required_mapping")

    if expected.forbidden_keys:
        if not isinstance(output, dict):
            raise AssertionError("forbidden_keys 只能用于对象输出")
        found = set(expected.forbidden_keys) & set(output)
        if found:
            raise AssertionError(f"包含禁止表：{sorted(found)}")
        checks.append("forbidden_keys")

    if expected.sql_contains or expected.sql_excludes:
        if not isinstance(output, str):
            raise AssertionError("SQL 断言只能用于字符串输出")
        normalized = output.casefold()
        missing = [
            term for term in expected.sql_contains if term.casefold() not in normalized
        ]
        forbidden = [
            term for term in expected.sql_excludes if term.casefold() in normalized
        ]
        if missing:
            raise AssertionError(f"SQL 缺少片段：{missing}")
        if forbidden:
            raise AssertionError(f"SQL 包含禁止片段：{forbidden}")
        checks.extend(["sql_contains", "sql_excludes"])

    return checks


def _run_offline_case(case: PromptEvalCase) -> CaseResult:
    try:
        definition = get_prompt_definition(case.prompt)
        if set(case.inputs) != set(definition.input_variables):
            raise AssertionError(
                f"输入变量不一致：期望 {definition.input_variables}，实际 {tuple(case.inputs)}"
            )
        messages = build_chat_prompt(case.prompt).invoke(case.inputs).messages
        if [message.type for message in messages] != ["system", "human"]:
            raise AssertionError("Prompt 必须渲染为 system + human 两条消息")
        return CaseResult(
            id=case.id,
            prompt=case.prompt,
            passed=True,
            checks=["registry", "variables", "render", "message_roles"],
        )
    except Exception as exc:
        return CaseResult(
            id=case.id,
            prompt=case.prompt,
            passed=False,
            checks=[],
            error=str(exc),
        )


def _run_live_case(case: PromptEvalCase) -> CaseResult:
    try:
        output = build_prompt_chain(case.prompt).invoke(case.inputs)
        checks = score_prompt_output(case, output)
        return CaseResult(
            id=case.id,
            prompt=case.prompt,
            passed=True,
            checks=checks,
            output=output,
        )
    except Exception as exc:
        return CaseResult(
            id=case.id,
            prompt=case.prompt,
            passed=False,
            checks=[],
            error=str(exc),
        )


def run_prompt_evals(
    suite: PromptEvalSuite,
    *,
    mode: Literal["offline", "live"] = "offline",
    prompt_name: str | None = None,
) -> EvalReport:
    cases = [
        case
        for case in suite.cases
        if prompt_name is None or case.prompt == prompt_name
    ]
    runner = _run_offline_case if mode == "offline" else _run_live_case
    results = [runner(case) for case in cases]
    passed = sum(result.passed for result in results)
    total = len(results)
    return EvalReport(
        mode=mode,
        total=total,
        passed=passed,
        failed=total - passed,
        score=round(passed / total, 4) if total else 0,
        cases=results,
    )
