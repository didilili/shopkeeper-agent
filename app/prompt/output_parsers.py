"""Prompt 输出协议和安全解析器。"""

from typing import Any, ClassVar

from langchain_core.output_parsers import BaseOutputParser, JsonOutputParser
from pydantic import RootModel, ValidationError, field_validator

from app.prompt.errors import PromptOutputError
from app.prompt.schemas import PromptOutputType
from app.security.sql_guard import SQLGuard, SQLSafetyError


class StringList(RootModel[list[str]]):
    @field_validator("root")
    @classmethod
    def normalize_items(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            item = value.strip()
            if item and item not in normalized:
                normalized.append(item)
        if len(normalized) > 30:
            raise ValueError("字符串数组最多允许 30 项")
        return normalized


class TableSelection(RootModel[dict[str, list[str]]]):
    @field_validator("root")
    @classmethod
    def validate_selection(cls, values: dict[str, list[str]]) -> dict[str, list[str]]:
        normalized: dict[str, list[str]] = {}
        for table, columns in values.items():
            table_name = table.strip()
            clean_columns = list(
                dict.fromkeys(column.strip() for column in columns if column.strip())
            )
            if not table_name or not clean_columns:
                raise ValueError("每张表都必须包含名称和至少一个字段")
            normalized[table_name] = clean_columns
        return normalized


class StringListOutputParser(BaseOutputParser[list[str]]):
    @property
    def _type(self) -> str:
        return "validated_string_list"

    def parse(self, text: str) -> list[str]:
        try:
            value: Any = JsonOutputParser().parse(text)
            return StringList.model_validate(value).root
        except (ValidationError, ValueError) as exc:
            raise PromptOutputError("模型输出不是有效的字符串数组") from exc


class TableSelectionOutputParser(BaseOutputParser[dict[str, list[str]]]):
    @property
    def _type(self) -> str:
        return "validated_table_selection"

    def parse(self, text: str) -> dict[str, list[str]]:
        try:
            value: Any = JsonOutputParser().parse(text)
            return TableSelection.model_validate(value).root
        except (ValidationError, ValueError) as exc:
            raise PromptOutputError("模型输出不是有效的表字段选择对象") from exc


class ReadOnlySQLOutputParser(BaseOutputParser[str]):
    guard: ClassVar[SQLGuard] = SQLGuard(max_sql_length=20_000)

    @property
    def _type(self) -> str:
        return "validated_readonly_sql"

    def parse(self, text: str) -> str:
        sql = text.strip()
        if sql.startswith("```"):
            lines = sql.splitlines()
            if lines and lines[0].strip().casefold() in {"```", "```sql"}:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            sql = "\n".join(lines).strip()

        try:
            return self.guard.validate(sql)
        except SQLSafetyError as exc:
            raise PromptOutputError(str(exc)) from exc


def get_output_parser(output_type: PromptOutputType) -> BaseOutputParser:
    parsers: dict[PromptOutputType, BaseOutputParser] = {
        "string_list": StringListOutputParser(),
        "table_selection": TableSelectionOutputParser(),
        "readonly_sql": ReadOnlySQLOutputParser(),
    }
    return parsers[output_type]
