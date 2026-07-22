"""模型注册表的 Pydantic 强类型结构。"""

from typing import Any, Literal, Self

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SecretReference(FrozenModel):
    env: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    required: bool = True


class CredentialReferences(FrozenModel):
    api_key: SecretReference | None = None


class ResolvedCredentials(FrozenModel):
    api_key: SecretStr | None = None


class RuntimeOptions(FrozenModel):
    temperature: float = Field(default=0, ge=0, le=2)
    timeout: float = Field(default=60, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    max_tokens: int | None = Field(default=None, gt=0)
    extra_kwargs: dict[str, Any] = Field(default_factory=dict)


class RuntimeOptionOverrides(FrozenModel):
    temperature: float | None = Field(default=None, ge=0, le=2)
    timeout: float | None = Field(default=None, gt=0)
    max_retries: int | None = Field(default=None, ge=0, le=10)
    max_tokens: int | None = Field(default=None, gt=0)
    extra_kwargs: dict[str, Any] | None = None


class ModelDeployment(FrozenModel):
    adapter: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: AnyHttpUrl | None = None
    credentials: CredentialReferences = Field(default_factory=CredentialReferences)
    options: RuntimeOptionOverrides = Field(default_factory=RuntimeOptionOverrides)
    enabled: bool = True
    description: str = ""
    tags: tuple[str, ...] = ()


class ModelProfile(FrozenModel):
    deployment: str = Field(min_length=1)
    description: str = ""


class ModelRegistryConfig(FrozenModel):
    version: Literal[1]
    default_profile: str = Field(min_length=1)
    defaults: RuntimeOptions = Field(default_factory=RuntimeOptions)
    profiles: dict[str, ModelProfile]
    deployments: dict[str, ModelDeployment]

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        if self.default_profile not in self.profiles:
            raise ValueError(f"default_profile 不存在：{self.default_profile}")

        missing = {
            profile.deployment
            for profile in self.profiles.values()
            if profile.deployment not in self.deployments
        }
        if missing:
            raise ValueError("业务角色引用了未知部署：" + ", ".join(sorted(missing)))
        return self


class ResolvedModel(FrozenModel):
    profile_name: str
    deployment_name: str
    adapter: str
    provider: str
    model: str
    base_url: AnyHttpUrl | None
    credentials: ResolvedCredentials
    options: RuntimeOptions
    description: str
    tags: tuple[str, ...]
