"""Prompt 注册表加载、模板路径保护和变量契约校验。"""

from functools import lru_cache
from pathlib import Path
from string import Formatter

import yaml
from pydantic import ValidationError

from app.prompt.errors import PromptConfigurationError, PromptNotFoundError
from app.prompt.schemas import PromptDefinition, PromptRegistryConfig

PROJECT_ROOT = Path(__file__).parents[2]
PROMPT_ROOT = PROJECT_ROOT / "resources" / "prompts"
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "config" / "prompts.yaml"


def _resolve_template_path(relative_path: str) -> Path:
    path = (PROJECT_ROOT / relative_path).resolve()
    try:
        path.relative_to(PROMPT_ROOT.resolve())
    except ValueError as exc:
        raise PromptConfigurationError(
            f"Prompt 模板必须位于 {PROMPT_ROOT}：{relative_path}"
        ) from exc
    if path.suffix != ".prompt":
        raise PromptConfigurationError(f"Prompt 模板扩展名必须是 .prompt：{path}")
    return path


@lru_cache
def load_template(relative_path: str) -> str:
    path = _resolve_template_path(relative_path)
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise PromptConfigurationError(f"无法读取 Prompt 模板：{path}") from exc


def _extract_variables(template: str) -> set[str]:
    return {
        field_name for _, field_name, _, _ in Formatter().parse(template) if field_name
    }


def _validate_definition(name: str, definition: PromptDefinition) -> None:
    system_template = load_template(definition.system_template)
    user_template = load_template(definition.user_template)
    system_variables = _extract_variables(system_template)
    if system_variables:
        raise PromptConfigurationError(
            f"Prompt {name!r} 的 system_template 不允许包含变量："
            + ", ".join(sorted(system_variables))
        )

    actual_variables = _extract_variables(user_template)
    declared_variables = set(definition.input_variables)
    if actual_variables != declared_variables:
        missing = declared_variables - actual_variables
        undeclared = actual_variables - declared_variables
        details = []
        if missing:
            details.append("模板缺少 " + ", ".join(sorted(missing)))
        if undeclared:
            details.append("存在未声明变量 " + ", ".join(sorted(undeclared)))
        raise PromptConfigurationError(
            f"Prompt {name!r} 变量不一致：{'；'.join(details)}"
        )


def load_prompt_registry(
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> PromptRegistryConfig:
    path = Path(registry_path).expanduser().resolve()
    try:
        with path.open("r", encoding="utf-8") as file:
            raw_config = yaml.safe_load(file)
        registry = PromptRegistryConfig.model_validate(raw_config)
    except OSError as exc:
        raise PromptConfigurationError(f"无法读取 Prompt 注册表：{path}") from exc
    except ValidationError as exc:
        raise PromptConfigurationError(f"Prompt 注册表校验失败：{path}") from exc

    for name, definition in registry.prompts.items():
        _validate_definition(name, definition)
    return registry


@lru_cache(maxsize=1)
def get_prompt_registry() -> PromptRegistryConfig:
    return load_prompt_registry()


def get_prompt_definition(name: str) -> PromptDefinition:
    definition = get_prompt_registry().prompts.get(name)
    if definition is None:
        available = ", ".join(sorted(get_prompt_registry().prompts))
        raise PromptNotFoundError(f"Prompt {name!r} 未注册；可选 Prompt：{available}")
    return definition
