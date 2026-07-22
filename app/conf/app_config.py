"""应用基础设施配置的分层加载与强类型校验。"""

import os
from pathlib import Path
from typing import Literal, Self

from omegaconf import OmegaConf
from omegaconf.errors import OmegaConfBaseException
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    model_validator,
)

from app.conf.environment import load_local_environment

EnvironmentName = Literal["development", "test", "production"]
LogLevel = Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]

project_root = Path(__file__).parents[2]
config_dir = project_root / "conf"


class ConfigurationError(RuntimeError):
    """配置文件无法读取或配置值不符合约束。"""


class FrozenConfigModel(BaseModel):
    """禁止未知字段和运行时修改的配置基类。"""

    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeConfig(FrozenConfigModel):
    app_name: str = Field(min_length=1)
    environment: EnvironmentName
    debug: bool = False


class FileLogConfig(FrozenConfigModel):
    enable: bool = True
    level: LogLevel = "INFO"
    path: str = Field(default="logs", min_length=1)
    rotation: str = Field(default="10 MB", min_length=1)
    retention: str = Field(default="7 days", min_length=1)


class ConsoleLogConfig(FrozenConfigModel):
    enable: bool = True
    level: LogLevel = "INFO"


class LoggingConfig(FrozenConfigModel):
    file: FileLogConfig
    console: ConsoleLogConfig


class DBConfig(FrozenConfigModel):
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    user: str = Field(min_length=1)
    password: SecretStr
    database: str = Field(min_length=1)
    pool_size: int = Field(gt=0)
    max_overflow: int = Field(ge=0)
    pool_recycle: int = Field(gt=0)
    connect_timeout: int = Field(gt=0)


class QdrantConfig(FrozenConfigModel):
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    embedding_size: int = Field(gt=0)
    api_key: SecretStr = SecretStr("")
    timeout: int = Field(gt=0)


class EmbeddingConfig(FrozenConfigModel):
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    model: str = Field(min_length=1)
    timeout: int = Field(gt=0)


class ESConfig(FrozenConfigModel):
    scheme: Literal["http", "https"] = "http"
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    index_name: str = Field(min_length=1)
    username: str = ""
    password: SecretStr = SecretStr("")
    request_timeout: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_auth_pair(self) -> Self:
        has_username = bool(self.username.strip())
        has_password = bool(self.password.get_secret_value().strip())
        if has_username != has_password:
            raise ValueError("ES 用户名和密码必须同时配置")
        return self


class RetrievalDomainConfig(FrozenConfigModel):
    score_threshold: float = Field(ge=0)
    per_query_limit: int = Field(gt=0, le=100)
    final_limit: int = Field(gt=0, le=100)
    rrf_k: int = Field(gt=0)
    exact_match_boost: float = Field(ge=0)


class RetrievalConfig(FrozenConfigModel):
    max_concurrency: int = Field(gt=0, le=50)
    column: RetrievalDomainConfig
    metric: RetrievalDomainConfig
    value: RetrievalDomainConfig


class AppConfig(FrozenConfigModel):
    runtime: RuntimeConfig
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    retrieval: RetrievalConfig

    @model_validator(mode="after")
    def validate_environment_policy(self) -> Self:
        database_passwords = {
            "DB_META_PASSWORD": self.db_meta.password.get_secret_value(),
            "DB_DW_PASSWORD": self.db_dw.password.get_secret_value(),
        }
        missing = [name for name, value in database_passwords.items() if not value]
        if missing:
            raise ValueError("数据库密码未配置：" + ", ".join(missing))

        if self.runtime.environment == "production":
            insecure_values = {"", "change_me", "dili123", "your_password_here"}
            insecure = [
                name
                for name, value in database_passwords.items()
                if value.strip().lower() in insecure_values
            ]
            if insecure:
                raise ValueError(
                    "生产环境禁止使用空值或示例密码：" + ", ".join(insecure)
                )
            if self.runtime.debug:
                raise ValueError("生产环境必须关闭 runtime.debug")
        return self


def load_app_config(environment: str | None = None) -> AppConfig:
    """合并公共配置和环境覆盖配置，再交给 Pydantic 校验。"""

    load_local_environment()
    selected_environment = (
        (environment or os.getenv("APP_ENV", "development")).strip().lower()
    )
    if selected_environment not in {"development", "test", "production"}:
        raise ConfigurationError(
            f"APP_ENV={selected_environment!r} 无效，可选值为 "
            "development、test、production"
        )

    base_file = config_dir / "app_config.yaml"
    environment_file = config_dir / "environments" / f"{selected_environment}.yaml"

    try:
        merged = OmegaConf.merge(
            OmegaConf.load(base_file), OmegaConf.load(environment_file)
        )
        merged.runtime.environment = selected_environment
        raw_config = OmegaConf.to_container(merged, resolve=True)
        return AppConfig.model_validate(raw_config)
    except (OSError, OmegaConfBaseException, ValidationError) as exc:
        raise ConfigurationError(
            f"加载 {selected_environment} 环境配置失败：{exc}"
        ) from exc


app_config = load_app_config()


if __name__ == "__main__":
    print(
        f"configuration ok: app={app_config.runtime.app_name}, "
        f"environment={app_config.runtime.environment}"
    )
