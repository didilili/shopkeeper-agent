"""
应用主配置模块

定义 conf/app_config.yaml 在程序中的结构化配置对象，
项目启动后会在这里一次性完成配置文件加载和类型化转换，其他模块只需要导入 app_config，
就可以按属性方式读取日志 MySQL Qdrant Embedding Elasticsearch 和 LLM 配置
"""

from dataclasses import dataclass
from pathlib import Path

from omegaconf import OmegaConf


# 文件日志配置
# 对应 logging.file 这一组参数
@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


# 控制台日志配置
# 对应 logging.console 这一组参数
@dataclass
class Console:
    enable: bool
    level: str


# 把 file 和 console 两组日志配置再组合成 logging 总配置
@dataclass
class LoggingConfig:
    file: File
    console: Console


# 数据库配置
# 同一份结构同时服务于元数据库 db_meta 和数仓模拟库 db_dw
@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int


# Embedding 服务配置
# 对应 YAML 里的 embedding 分组
@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str


# Elasticsearch 配置
# 对应 YAML 里的 es 分组
@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str


# 大模型配置
# 对应 YAML 里的 llm 分组
@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str


# AppConfig 是整个项目配置的总入口
# 字段名需要和 app_config.yaml 的顶层字段保持一致
@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig


# 从当前文件位置回到项目根目录，再定位到 conf/app_config.yaml
config_file = Path(__file__).parents[2] / "conf" / "app_config.yaml"

# 读取 YAML 配置内容
context = OmegaConf.load(config_file)

# 根据 AppConfig 生成结构化配置 schema
schema = OmegaConf.structured(AppConfig)

# 把配置结构和配置值合并，再转换成可以直接按属性访问的对象
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

if __name__ == "__main__":
    # 简单测试：验证配置是否能正常读取
    print(app_config.es.host)
