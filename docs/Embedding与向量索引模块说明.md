# Embedding 与向量索引模块说明

## 1. 模块边界

项目使用 TEI 托管 `BAAI/bge-large-zh-v1.5`，通过统一的 `EmbeddingClient`
为在线召回和离线元数据索引构建提供向量化能力。Qdrant 负责保存字段和指标
向量，Embedding 客户端不直接感知业务实体或 collection。

## 2. 客户端契约

客户端统一实现：

- 按 `EMBEDDING_BATCH_SIZE` 拆分大批量输入；
- HTTP 客户端超时和协程级超时双重保护；
- 返回向量数量必须与输入文本数量一致；
- 每条向量必须与 `QDRANT_EMBEDDING_SIZE` 维度一致；
- 拒绝 `NaN` 和无穷大等非有限数值；
- 显式初始化、未初始化访问报错和异步关闭；
- 应用启动时执行一次最小向量化探测，失败则不进入 ready 状态。

TEI 实例实际加载的模型由容器 `MODEL_ID` 决定。`EMBEDDING_MODEL` 用作部署
模型标识和日志信息，必须与 TEI 的实际模型保持一致。

## 3. 索引构建

字段和指标都会把名称、描述和别名拆成独立语义入口。向量点 ID 根据
collection、业务实体 ID 和文本来源稳定生成，不再使用随机 UUID。

离线构建遵循以下顺序：

```text
准备全部业务点
  -> 分批生成全部向量
  -> 校验数量、维度和数值
  -> 重建对应 Qdrant collection
  -> 严格对齐 id / vector / payload 后批量写入
```

只有全部向量化成功后才会重建 collection，避免 Embedding 请求中途失败时提前
清空现有索引。重建会移除配置中已经删除的字段、指标、描述和别名，因此重复执行
不会累积历史向量点。

重建期间对应 collection 存在短暂不可用窗口。需要无中断更新时，应进一步采用
临时 collection 加 Qdrant alias 原子切换。

## 4. 配置

```text
EMBEDDING_HOST=127.0.0.1
EMBEDDING_PORT=8081
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
EMBEDDING_TIMEOUT=30
EMBEDDING_BATCH_SIZE=20
QDRANT_EMBEDDING_SIZE=1024
```

切换模型时必须同步确认输出维度并重新构建向量索引。

## 5. 自动化验证

测试覆盖批处理、超时配置传递、未初始化访问、返回数量、向量维度、非有限数值、
Qdrant 写入数量对齐、已有 collection 配置和稳定向量 ID。
