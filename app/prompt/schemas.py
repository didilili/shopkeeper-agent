"""Prompt 注册表的 Pydantic 配置结构。"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PromptOutputType = Literal["string_list", "table_selection", "readonly_sql"]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PromptDefinition(FrozenModel):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str = Field(min_length=1)
    system_template: str = Field(pattern=r"^prompts/.+\.prompt$")
    user_template: str = Field(pattern=r"^prompts/.+\.prompt$")
    model_profile: str = Field(min_length=1)
    input_variables: tuple[str, ...]
    output_type: PromptOutputType

    @field_validator("input_variables")
    @classmethod
    def validate_input_variables(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("input_variables 不能重复")
        if any(not value.isidentifier() for value in values):
            raise ValueError("input_variables 必须是合法 Python 标识符")
        return values


class PromptRegistryConfig(FrozenModel):
    version: Literal[1]
    prompts: dict[str, PromptDefinition]

    @model_validator(mode="after")
    def validate_prompt_names(self) -> Self:
        if not self.prompts:
            raise ValueError("至少需要注册一个 Prompt")
        invalid = [name for name in self.prompts if not name.isidentifier()]
        if invalid:
            raise ValueError("Prompt 名称不合法：" + ", ".join(sorted(invalid)))
        return self
