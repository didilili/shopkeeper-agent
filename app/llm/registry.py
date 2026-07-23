"""读取、校验并解析配置驱动的模型注册表。"""

import os
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import SecretStr, ValidationError

from app.config.environment import load_local_environment
from app.llm.errors import (
    CredentialError,
    LLMConfigurationError,
    ProfileNotFoundError,
)
from app.llm.schemas import (
    ModelRegistryConfig,
    ResolvedCredentials,
    ResolvedModel,
    RuntimeOptions,
)

PROJECT_ROOT = Path(__file__).parents[2]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "config" / "models.yaml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _resolve_registry_path(registry_path: Path | str | None = None) -> Path:
    selected = (
        registry_path or os.getenv("MODEL_REGISTRY_PATH") or DEFAULT_REGISTRY_PATH
    )
    return Path(selected).expanduser().resolve()


def load_model_registry(
    registry_path: Path | str | None = None,
) -> ModelRegistryConfig:
    path = _resolve_registry_path(registry_path)
    try:
        with path.open("r", encoding="utf-8") as file:
            raw_config = yaml.safe_load(file)
    except OSError as exc:
        raise LLMConfigurationError(f"无法读取模型注册表：{path}") from exc

    if not isinstance(raw_config, dict):
        raise LLMConfigurationError(f"模型注册表顶层必须是对象：{path}")

    try:
        return ModelRegistryConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise LLMConfigurationError(f"模型注册表校验失败：{path}") from exc


@lru_cache(maxsize=1)
def get_model_registry() -> ModelRegistryConfig:
    return load_model_registry()


def _resolve_credentials(
    registry: ModelRegistryConfig, deployment_name: str
) -> ResolvedCredentials:
    load_local_environment()
    reference = registry.deployments[deployment_name].credentials.api_key
    if reference is None:
        return ResolvedCredentials()

    value = os.getenv(reference.env)
    if value is None or not value.strip() or value == "your_api_key_here":
        if reference.required:
            raise CredentialError(
                f"部署 {deployment_name!r} 缺少有效环境变量 {reference.env}"
            )
        return ResolvedCredentials()
    return ResolvedCredentials(api_key=SecretStr(value))


def resolve_model(
    profile_name: str | None = None,
    *,
    registry: ModelRegistryConfig | None = None,
) -> ResolvedModel:
    selected_registry = registry or get_model_registry()
    selected_profile = profile_name or selected_registry.default_profile
    profile = selected_registry.profiles.get(selected_profile)
    if profile is None:
        available = ", ".join(sorted(selected_registry.profiles))
        raise ProfileNotFoundError(
            f"未知模型角色 {selected_profile!r}；可选角色：{available}"
        )

    deployment = selected_registry.deployments[profile.deployment]
    if not deployment.enabled:
        raise LLMConfigurationError(f"部署 {profile.deployment!r} 已被禁用")

    options = _deep_merge(
        selected_registry.defaults.model_dump(),
        deployment.options.model_dump(exclude_none=True),
    )
    return ResolvedModel(
        profile_name=selected_profile,
        deployment_name=profile.deployment,
        adapter=deployment.adapter,
        provider=deployment.provider,
        model=deployment.model,
        base_url=deployment.base_url,
        credentials=_resolve_credentials(selected_registry, profile.deployment),
        options=RuntimeOptions.model_validate(options),
        description=deployment.description,
        tags=deployment.tags,
    )


def clear_model_caches() -> None:
    get_model_registry.cache_clear()
