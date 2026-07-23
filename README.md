<div align='center'>
  <h1 style="margin-top: 15px;">「电商问数」智能数据分析 Agent</h1>
  <h4><b>shopkeeper-agent</b></h4>
  <p><em>可能是全网最适合用于系统学习 LangGraph 的智能问数实战项目，配套系统性文字教程与对应章节分支，带你打通混合检索、多阶段推理、SQL 生成与执行全链路</em></p>
</div>

<div align='center'>

![AI](https://img.shields.io/badge/AI-Agent-00c853?style=flat)
![Python](https://img.shields.io/badge/Python-3.14-3776AB.svg?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20Workflow-1C3C3C.svg)
![Stars](https://img.shields.io/github/stars/didilili/shopkeeper-agent?logo=github&style=flat)
[![Read Online](https://img.shields.io/badge/在线教程-点击访问-blue?logo=bookstack)](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/0-%E5%89%8D%E8%A8%80)

</div>

**📢 说明**：本套实战项目已更新完成，配套教程、章节分支和前后端代码均可对照学习。

如果你正在找一个适合学习 `LangGraph`、`Qdrant`、`MySQL`、`FastAPI` 和 AI Agent 工程开发的实战项目，「电商问数」很可能是最适合你的项目。

它不是只调用一次大模型接口，也不是写几个 Prompt 演示 SQL 生成结果。这个项目围绕电商数仓问数场景，先构建元数据知识库，再做字段、指标、字段取值的混合检索，随后用 LangGraph 编排多阶段问数流程，完成 SQL 生成、校验、修正、执行和前端流式展示。换句话说，你学到的不是某一个框架 API，而是一条 AI 应用从数据准备、检索增强、智能体编排、接口交付到前端联调的完整项目主线。

> 本套仓库是 [ai-agents-from-zero](https://github.com/didilili/ai-agents-from-zero) 教程体系中的 [实战项目-电商问数](https://github.com/didilili/ai-agents-from-zero/tree/main/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0) 配套源码仓库，除了可直接运行和二次开发的项目代码之外，也提供了与教程章节对应的 Git 分支演进过程，以及完整的在线图文讲义入口。
> 如果你想系统学习「AI智能体 大模型应用开发」，也可直接从系统教程 [AI 智能体实战速成指南-大模型入门](https://didilili.github.io/ai-agents-from-zero/#/) 开始。

![电商问数前端首页：样例问题、自然语言输入和智能数据分析 Agent 界面](docs/images/shopkeeper-agent-home.jpg)

## 📖 项目介绍

在真实问数场景里，业务同学通常不会写 SQL，数据分析同学也很难随时记住所有表结构、字段含义、指标口径和字段取值。单纯把自然语言问题直接交给大模型，很容易出现表选错、字段选错、指标理解错和 SQL 幻觉等问题。

`电商问数` 要解决的就是这个问题：

- 用户用自然语言提问
- 系统自动召回相关字段、指标和字段取值
- 大模型基于上下文进行分步推理
- 生成 SQL 并查询数据仓库
- 以流式方式返回分析结果

## ✨ 项目亮点

- **检索 + 推理 + 生成，而不是模型直出 SQL**
    - 先围绕问题召回相关字段、指标和值域，再组织上下文生成 SQL，整体链路更稳、更可控。
- **面向企业问数场景的混合检索**
    - `Qdrant` 负责字段和指标的语义召回。
    - `Elasticsearch` 负责字段取值的全文检索。
    - `MySQL` 负责保存完整、权威的结构化元数据。
- **支持字段、指标、取值三类信息协同召回**
    - 比单纯做表级或字段级检索更贴近真实企业分析流程。
- **从检索到执行的完整可运行链路**
    - 不停留在 Prompt 设计，而是会真实生成 SQL、执行查询，并以流式方式返回结果。
- **工程化后端结构清晰**
    - 基于 `FastAPI + LangGraph + Repository + Client Manager` 组织配置、客户端、仓储层、服务层与智能体流程，便于维护和扩展。
- **不仅有实战代码，还有完整配套教程文档**
    - 项目配有一套系统化、持续更新、完全免费的教程讲义，适合按章节从数仓基础、元数据知识库到问数智能体流程逐步学习。
- **兼顾学习价值与可扩展性**
    - 既可以按教程章节逐步理解，也可以在此基础上继续扩展权限控制、SQL 审核、结果可视化等能力。

这套课程十分适合这些场景：

- 想系统学习 `LangGraph`，但不想只停留在几个玩具节点。
- 想把 `MySQL`、`Qdrant`、`Elasticsearch` 和大模型放到同一个业务场景里理解。
- 想做一个比简单模型调用更接近实际开发的 AI Agent 项目。
- 想把项目写进简历，并且能说清楚数据层、检索层、智能体层、服务层和前端层分别做了什么。

## 🏗️ 系统架构

![电商问数系统架构图：前端通过 FastAPI 和 SSE 连接后端，LangGraph 问数智能体基于 Jieba、MySQL、Qdrant、Elasticsearch 和 LLM 完成召回、SQL 生成校验执行与结果返回](docs/images/shopkeeper-agent-system-architecture.svg)

项目围绕两条主线展开：

| 主线             | 做什么                                                                   | 涉及模块                                     |
| ---------------- | ------------------------------------------------------------------------ | -------------------------------------------- |
| 元数据知识库构建 | 抽取教学数仓中的表、字段、指标和字段取值，写入结构化库、向量库和全文索引 | `MySQL` / `Qdrant` / `Elasticsearch` / `TEI` |
| 自然语言问数     | 基于用户问题完成召回、上下文整理、SQL 生成校验执行，并把过程流式返回前端 | `LangGraph` / `FastAPI` / `SSE` / `React`    |

![电商问数查询结果页：LangGraph 执行流程、SQL 校验执行和查询结果表格](docs/images/shopkeeper-agent-query-result.jpg)

## 🛠️ 项目技术栈

| 模块       | 技术                              | 作用                                           |
| ---------- | --------------------------------- | ---------------------------------------------- |
| 教学数仓   | `MySQL`                           | 模拟事实表、维度表和分析型查询环境             |
| 元数据库   | `MySQL` / `SQLAlchemy`            | 保存表、字段、指标、字段指标关系等结构化元数据 |
| 向量检索   | `Qdrant`                          | 保存字段和指标向量，支持语义召回               |
| 全文检索   | `Elasticsearch`                   | 保存字段真实取值，支持关键词和值域检索         |
| Embedding  | `TEI` / `BAAI/bge-large-zh-v1.5`  | 将字段、指标、问题等文本转成向量               |
| 智能体编排 | `LangGraph`                       | 组织多阶段问数工作流                           |
| 模型接入   | `LangChain`                       | 封装 LLM 与 Embedding 调用                     |
| 后端接口   | `FastAPI`                         | 提供问数 API、依赖注入和生命周期管理           |
| 流式协议   | `SSE`                             | 实时返回节点进度、查询结果和错误消息           |
| 前端       | `React` / `Vite` / `Tailwind CSS` | 提供聊天式问数界面和流程展示                   |
| 日志追踪   | `ContextVar` / `loguru`           | 为并发请求注入 request_id，便于排查链路        |
| 依赖管理   | `uv` / `pnpm`                     | 管理 Python 后端和前端依赖                     |

## 📁 项目结构

```text
shopkeeper-agent/
├── .github/workflows/    # 后端与前端持续集成门禁
├── app/
│   ├── agent/            # LangGraph 图、状态、上下文和各类节点
│   ├── api/              # FastAPI 路由、依赖注入、生命周期和请求结构
│   ├── clients/          # MySQL、Qdrant、Elasticsearch、Embedding 客户端管理
│   ├── config/           # Pydantic 配置模型与本地环境加载
│   ├── core/             # 日志、request_id 上下文等通用能力
│   ├── entities/         # 更贴近业务语义的数据对象
│   ├── llm/              # 模型注册表、工厂和协议适配器
│   ├── models/           # SQLAlchemy ORM 模型
│   ├── prompt/           # Prompt 注册表、工厂、输出协议和候选校验
│   ├── retrieval/        # 并发召回、候选去重与 RRF 重排序
│   ├── repositories/     # MySQL、Qdrant、Elasticsearch 数据访问层
│   ├── security/         # Agent SQL 只读安全策略与执行边界
│   ├── scripts/          # 元数据知识库构建脚本
│   └── services/         # 元数据构建服务和问数查询服务
├── config/               # YAML 环境配置、模型注册表和业务元数据资产
├── docker/               # Docker Compose、MySQL 初始化 SQL、ES 插件、Embedding 挂载目录
├── frontend/             # React + Vite + Tailwind CSS 前端项目
├── resources/            # Prompt 模板与离线评测数据等运行时资产
│   ├── evals/            # 基于真实电商 Schema 的评测集
│   └── prompts/          # SQL、召回、过滤等 Prompt 模板
├── tests/                # 配置与模型注册表自动化测试
├── app/main.py           # FastAPI 应用入口
└── pyproject.toml        # Python 项目依赖与工具配置
```

## 🚀 快速开始

当前仓库已经包含一套可直接启动的本地开发环境，你可以按照以下顺序启动项目。

Prompt 修改后可先运行不调用模型的契约评测：

```bash
uv run python -m app.scripts.evaluate_prompts --mode offline
```

配置真实 `LLM_API_KEY` 后，运行在线语义评测：

```bash
uv run python -m app.scripts.evaluate_prompts --mode live
```

召回评测集可以先离线校验结构；基础服务和元数据知识库准备完成后，再运行
真实的 Recall@K、MRR@K 与 nDCG@K 评测：

```bash
uv run python -m app.scripts.evaluate_retrieval --mode validate
uv run python -m app.scripts.evaluate_retrieval --mode live \
  --output reports/retrieval-live.json
```

### 1. 准备环境

- Python `>= 3.14`
- `uv`
- Docker 与 Docker Compose
- Node.js 与 `pnpm`

### 2. 克隆项目

```bash
git clone https://github.com/didilili/shopkeeper-agent.git
cd shopkeeper-agent
```

### 3. 安装后端依赖

```bash
uv sync
```

### 4. 配置运行环境

```bash
cp .env.example .env
```

项目采用“公共基线 + 环境覆盖 + 环境变量”的分层配置：

- `config/app_config.yaml`：各环境共享的默认结构
- `config/environments/development.yaml`：本地开发覆盖项
- `config/environments/test.yaml`：自动化测试覆盖项
- `config/environments/production.yaml`：生产环境覆盖项
- `config/models.yaml`：模型角色、部署和协议适配器注册表
- `config/prompts.yaml`：Prompt 版本、模板、变量、模型角色和输出协议
- `.env`：仅用于本地注入连接信息和密钥，不会提交到 Git

首次启动时，把 `.env` 中的 `LLM_API_KEY` 替换成真实密钥：

```bash
APP_ENV=development
LLM_API_KEY=your_real_api_key
```

本地开发默认关闭查询接口认证。生产环境必须启用 API Key，并设置至少 32
字符的随机密钥：

```bash
API_AUTH_ENABLED=true
API_AUTH_KEY=replace_with_a_random_secret_of_at_least_32_chars
API_RATE_LIMIT_REQUESTS=60
API_RATE_LIMIT_WINDOW_SECONDS=60
```

调用 `POST /api/query` 时通过 `X-API-Key` 请求头传入密钥。存活和就绪检查保持
匿名访问，便于容器编排平台探测。

基础设施配置按运行环境区分；模型配置独立采用
`Profile -> Deployment -> Adapter` 结构。业务节点只依赖稳定的
`sql_agent` 模型角色：

```yaml
profiles:
  sql_agent:
    deployment: siliconflow_glm

deployments:
  siliconflow_glm:
    adapter: openai_compatible
    provider: siliconflow
    model: Pro/zai-org/GLM-5.1
    credentials:
      api_key:
        env: LLM_API_KEY
        required: true
```

应用配置和模型注册表都使用 Pydantic 强校验，密码和 API Key 使用
`SecretStr` 脱敏。生产部署设置 `APP_ENV=production`，并由部署平台注入
数据库密码和模型密钥；配置错误时程序会在建立外部连接前终止启动。

字段、指标和值域召回参数统一位于 `config/app_config.yaml` 的 `retrieval`
配置段，可通过环境变量覆盖。召回层会稳定去重查询词、批量生成向量、
并发访问检索仓储，再使用 RRF 融合多路结果；底层相似度分数与命中词会
保留在排序过程和日志中。设计与调参说明见
[`docs/召回与重排序模块说明.md`](docs/召回与重排序模块说明.md)。

Embedding 客户端统一执行配置化批处理、超时、数量和维度校验；字段与指标
向量索引使用稳定 ID，并在离线重建时清理历史点，避免重复构建累积。设计边界见
[`docs/Embedding与向量索引模块说明.md`](docs/Embedding与向量索引模块说明.md)。

Agent 生成和修正的 SQL 会在数据库边界再次经过只读安全审计和 AST 表级授权，
只允许访问本轮元数据上下文已经提供的表，并通过有限修正循环重新执行
`EXPLAIN` 校验；查询等待时间、SQL 长度和结果行数均可配置。
设计边界见
[`docs/SQL安全执行模块说明.md`](docs/SQL安全执行模块说明.md)。

API 层会为每个请求生成或透传 `X-Request-ID`，对查询接口实施可配置 API Key
认证和单进程固定窗口限流，对 SSE 异常进行脱敏，并提供存活与资源初始化状态
端点。接口语义和 CI 门禁见
[`docs/API交付层说明.md`](docs/API交付层说明.md)。

### 5. 准备 Embedding 模型

项目通过 `TEI` 加载 `BAAI/bge-large-zh-v1.5`。模型文件体积较大，无法再仓库中进行提交，需要先下载到 Docker 挂载目录：

```bash
uv run hf download BAAI/bge-large-zh-v1.5 --local-dir docker/embedding/bge-large-zh-v1.5
```

如果手动下载，请解压到：`docker/embedding/bge-large-zh-v1.5`路径下。

### 6. 启动 Docker 基础服务

```bash
docker compose -f docker/docker-compose.yaml up -d
```

默认端口：

| 服务          | 端口   |
| ------------- | ------ |
| MySQL         | `3306` |
| Elasticsearch | `9200` |
| Kibana        | `5601` |
| Qdrant        | `6333` |
| Embedding     | `8081` |

> `docker/mysql/meta.sql` 和 `docker/mysql/dw.sql` 会在 MySQL 容器首次启动时自动初始化元数据库和教学数仓。

### 7. 构建元数据知识库

```bash
uv run python -m app.scripts.build_meta_knowledge -c config/meta_config.yaml
```

这一步会把表字段元数据写入 MySQL，把字段和指标向量写入 Qdrant，并把字段真实取值写入 Elasticsearch。

### 8. 启动后端

```bash
uv run fastapi dev app/main.py
```

后端接口：

```text
POST http://127.0.0.1:8000/api/query
```

健康检查：

```text
GET http://127.0.0.1:8000/api/health/live
GET http://127.0.0.1:8000/api/health/ready
```

请求示例：

```json
{
    "query": "统计华北地区的销售总额"
}
```

SSE 消息类型：

| 类型       | 含义         |
| ---------- | ------------ |
| `progress` | 节点执行进度 |
| `result`   | 最终查询结果 |
| `error`    | 全局异常消息 |

### 9. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端默认通过 Vite 代理把 `/api` 转发到 `http://127.0.0.1:8000`。如需修改：

```bash
cd frontend
cp .env.example .env
```

```bash
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000
```

## 📚 配套教程目录

教程总入口：[电商问数完整教程](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/0-%E5%89%8D%E8%A8%80)

| 章节 | 标题                                                                                                                                                                                                                                                                              | 学习重点                                                                 | 对应分支                           |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------- |
| 0    | [前言](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/0-%E5%89%8D%E8%A8%80)                                                                                                                           | 项目定位、学习价值与能力边界                                             | `-`                                |
| 1    | [项目概述与数仓基础](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/1-%E9%A1%B9%E7%9B%AE%E6%A6%82%E8%BF%B0%E4%B8%8E%E6%95%B0%E4%BB%93%E5%9F%BA%E7%A1%80)                                              | 业务库、数仓、事实表、维度表与教学数仓设计                               | `-`                                |
| 2    | [项目整体架构与智能体流程](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/2-%E9%A1%B9%E7%9B%AE%E6%95%B4%E4%BD%93%E6%9E%B6%E6%9E%84%E4%B8%8E%E6%99%BA%E8%83%BD%E4%BD%93%E6%B5%81%E7%A8%8B)             | MySQL、Qdrant、Elasticsearch、LLM 与 Agent 工作流如何协作                | `-`                                |
| 3    | [开发环境与基础服务准备](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/3-%E5%BC%80%E5%8F%91%E7%8E%AF%E5%A2%83%E4%B8%8E%E5%9F%BA%E7%A1%80%E6%9C%8D%E5%8A%A1%E5%87%86%E5%A4%87)                        | uv、Docker Compose、MySQL、Qdrant、Elasticsearch、Kibana、Embedding 服务 | `03-env-services`                  |
| 4    | [项目结构与基础服务配置管理](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/4-%E9%A1%B9%E7%9B%AE%E7%BB%93%E6%9E%84%E4%B8%8E%E5%9F%BA%E7%A1%80%E6%9C%8D%E5%8A%A1%E9%85%8D%E7%BD%AE%E7%AE%A1%E7%90%86)  | 工程结构、YAML 配置、OmegaConf 与 dataclass 配置加载                     | `04-structure-config`              |
| 5    | [Qdrant 与 ES 快速入门与接入](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/5-Qdrant%E4%B8%8EES%E5%BF%AB%E9%80%9F%E5%85%A5%E9%97%A8%E4%B8%8E%E6%8E%A5%E5%85%A5)                                      | 向量检索、全文检索与客户端管理                                           | `05-qdrant-es`                     |
| 6    | [MySQL、Embedding 接入与日志管理](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/6-MySQL%E3%80%81Embedding%E4%B8%8E%E6%97%A5%E5%BF%97%E7%AE%A1%E7%90%86)                                              | 异步 MySQL、TEI Embedding、loguru 日志                                   | `06-mysql-embedding-log`           |
| 7    | [元数据知识库总览与构建入口](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/7-%E5%85%83%E6%95%B0%E6%8D%AE%E7%9F%A5%E8%AF%86%E5%BA%93%E6%80%BB%E8%A7%88%E4%B8%8E%E6%9E%84%E5%BB%BA%E5%85%A5%E5%8F%A3)  | 元数据知识库产物、存储分工和构建入口                                     | `07-metadata-base-overview`        |
| 8    | [表与字段信息同步到元数据库](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/8-%E8%A1%A8%E4%B8%8E%E5%AD%97%E6%AE%B5%E4%BF%A1%E6%81%AF%E5%90%8C%E6%AD%A5%E5%88%B0%E5%85%83%E6%95%B0%E6%8D%AE%E5%BA%93)  | Service、Repository、Mapper、ORM 如何配合入库                            | `08-metadata-table-column-sync`    |
| 9    | [字段与指标检索能力构建](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/9-%E5%AD%97%E6%AE%B5%E4%B8%8E%E6%8C%87%E6%A0%87%E6%A3%80%E7%B4%A2%E8%83%BD%E5%8A%9B%E6%9E%84%E5%BB%BA)                        | 字段向量索引、字段值全文索引和指标向量索引                               | `09-metadata-retrieval-capability` |
| 10   | [问数智能体总览与工作流骨架](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/10-%E9%97%AE%E6%95%B0%E6%99%BA%E8%83%BD%E4%BD%93%E6%80%BB%E8%A7%88%E4%B8%8E%E5%B7%A5%E4%BD%9C%E6%B5%81%E9%AA%A8%E6%9E%B6) | LangGraph 工作流骨架与节点设计                                           | `10-agent-workflow-skeleton`       |
| 11   | [关键词抽取与多路召回](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/11-%E5%85%B3%E9%94%AE%E8%AF%8D%E6%8A%BD%E5%8F%96%E4%B8%8E%E5%A4%9A%E8%B7%AF%E5%8F%AC%E5%9B%9E)                                  | 关键词抽取，字段、指标和字段取值并行召回                                 | `11-agent-keyword-multi-recall`    |
| 12   | [召回信息合并与上下文构建](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/12-%E5%8F%AC%E5%9B%9E%E4%BF%A1%E6%81%AF%E5%90%88%E5%B9%B6%E4%B8%8E%E4%B8%8A%E4%B8%8B%E6%96%87%E6%9E%84%E5%BB%BA)            | 召回结果合并、依赖字段补齐和值域上下文构建                               | `12-agent-merge-retrievals`        |
| 13   | [SQL 生成前的信息过滤与补全](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/13-SQL%E7%94%9F%E6%88%90%E5%89%8D%E7%9A%84%E4%BF%A1%E6%81%AF%E8%BF%87%E6%BB%A4%E4%B8%8E%E8%A1%A5%E5%85%A8)                | 候选表字段过滤、指标过滤、日期和数据库上下文补齐                         | `13-agent-filter-extra-context`    |
| 14   | [SQL 生成与执行闭环](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/14-SQL%E7%94%9F%E6%88%90%E4%B8%8E%E6%89%A7%E8%A1%8C%E9%97%AD%E7%8E%AF)                                                            | SQL 生成、EXPLAIN 校验、错误修正和最终执行                               | `14-agent-sql-loop`                |
| 15   | [API 接口基础与 FastAPI 入门](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/15-API%E6%8E%A5%E5%8F%A3%E5%9F%BA%E7%A1%80%E4%B8%8EFastAPI%E5%85%A5%E9%97%A8)                                            | `/api/query`、StreamingResponse 和 SSE 基础                              | `15-api-streaming-basics`          |
| 16   | [查询接口实现与依赖组装](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/16-%E6%9F%A5%E8%AF%A2%E6%8E%A5%E5%8F%A3%E5%AE%9E%E7%8E%B0%E4%B8%8E%E4%BE%9D%E8%B5%96%E7%BB%84%E8%A3%85)                       | QueryService、依赖注入和应用生命周期资源管理                             | `16-api-query-service`             |
| 17   | [前后端联调与日志追踪](https://didilili.github.io/ai-agents-from-zero/#/%E5%AE%9E%E6%88%98%E9%A1%B9%E7%9B%AE-%E7%94%B5%E5%95%86%E9%97%AE%E6%95%B0/17-%E5%89%8D%E5%90%8E%E7%AB%AF%E8%81%94%E8%B0%83%E4%B8%8E%E6%97%A5%E5%BF%97%E8%BF%BD%E8%B8%AA)                                  | SSE 消息协议、前端展示、异常兜底和 request_id 日志追踪                   | `17-api-integration-logging`       |

可以用分支切换对照每一阶段的代码演进：

```bash
git checkout 04-structure-config
git checkout main
```

`main` 分支保留当前完整闭环版本。

> 本项目基于尚硅谷「大模型智能体掌柜问数」项目，并在此基础上整理完善。

## 🚧 能力边界

这套项目主要关注智能问数的学习流程，不刻意覆盖生产治理能力，例如：

- 用户登录、角色权限和数据权限控制
- 多租户隔离
- 数据库代理审计、行列级权限和查询成本治理
- 分布式限流、查询缓存和跨实例性能治理
- 大规模生产评测集、人工标注平台和线上反馈闭环
- 监控告警、链路追踪平台和灰度发布
- 更复杂的多轮问数记忆、追问改写和会话管理

这些能力适合在基础流程跑通之后继续扩展。`shopkeeper-agent` 更适合承担一个清晰角色：先把智能问数最关键、最必要、最值得学习的工程链路讲清楚、跑起来，并为后续扩展企业级能力打基础。
