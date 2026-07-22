"""结合候选上下文验证模型选择结果，拒绝静默幻觉。"""

from collections.abc import Iterable, Mapping
from typing import Any

from app.prompt.errors import PromptOutputError


def validate_name_selection(
    selected_names: list[str],
    candidates: Iterable[Mapping[str, Any]],
    *,
    label: str,
) -> None:
    allowed = {str(candidate["name"]) for candidate in candidates}
    unknown = set(selected_names) - allowed
    if unknown:
        raise PromptOutputError(
            f"模型返回了候选之外的{label}：" + ", ".join(sorted(unknown))
        )


def validate_table_selection(
    selection: dict[str, list[str]],
    table_infos: Iterable[Mapping[str, Any]],
) -> None:
    allowed = {
        str(table["name"]): {str(column["name"]) for column in table.get("columns", [])}
        for table in table_infos
    }

    unknown_tables = set(selection) - set(allowed)
    if unknown_tables:
        raise PromptOutputError(
            "模型返回了候选之外的表：" + ", ".join(sorted(unknown_tables))
        )

    for table_name, columns in selection.items():
        unknown_columns = set(columns) - allowed[table_name]
        if unknown_columns:
            raise PromptOutputError(
                f"模型为表 {table_name!r} 返回了候选之外的字段："
                + ", ".join(sorted(unknown_columns))
            )
