# API 交付层说明

## 1. 改造目标

问数工作流通过 SSE 长连接返回进度和结果。流式响应开始后无法再修改 HTTP
状态码，因此 API 层需要同时解决请求追踪、错误脱敏、客户端取消和运行状态探测。

## 2. 请求追踪

服务接受格式安全、长度不超过 64 字符的 `X-Request-ID`。缺失或不合法时生成
新的 32 位十六进制 ID，并通过响应头返回。

请求 ID 同时写入 FastAPI `request.state`、日志使用的 `ContextVar` 和 SSE
错误事件。中间件与流式生成器结束时都会恢复各自的上下文 Token，避免并发
请求之间串号。

## 3. 查询访问控制

`POST /api/query` 支持 `X-API-Key` 请求头认证。开发和测试环境默认关闭认证，
生产环境配置校验会强制要求 `API_AUTH_ENABLED=true`，且密钥不少于 32 个字符。
密钥使用常量时间比较，日志和访问主体中只保留不可逆摘要，不记录原始值。

查询接口同时使用固定窗口限流，默认每个访问主体 60 秒内 60 次请求：

```text
API_AUTH_ENABLED=false
API_AUTH_KEY=
API_RATE_LIMIT_REQUESTS=60
API_RATE_LIMIT_WINDOW_SECONDS=60
```

认证开启时，访问主体由 API Key 摘要标识；关闭时使用客户端地址。超过限制返回
HTTP 429 和 `Retry-After`。当前实现保存在单个应用进程内，适合本地开发和单实例
部署；多进程或多副本部署应在 API 网关或 Redis 中使用共享限流状态。

API Key 是服务端密钥，不应写入浏览器构建产物。生产环境中的 Web 前端应通过
同源 BFF 或 API 网关完成用户认证，再由可信服务注入 `X-API-Key`；当前前端
直连模式仅适用于关闭认证的本地开发环境。

健康检查不要求 API Key，保证容器和负载均衡器可以持续探测。

## 4. SSE 错误边界

正常事件继续使用原有 `progress` 和 `result` 协议。工作流异常时，服务端日志
保留完整堆栈，客户端只收到脱敏错误和 `request_id`：

```text
data: {"type":"error","message":"查询处理失败，请使用 request_id 联系管理员。","request_id":"..."}
```

客户端断开触发的 `CancelledError` 会继续向上传播，不会被误包装成业务错误。
响应关闭代理缓冲并禁用缓存，确保进度事件及时送达。

## 5. 健康检查

- `GET /api/health/live`：HTTP 进程能够响应即返回 200。
- `GET /api/health/ready`：应用生命周期已完成客户端和连接池初始化时返回 200，
  未完成或正在关闭时返回 503。

应用启动时会执行一次最小 Embedding 向量化探测，通过后才进入 `ready`。该状态
仍不是对 MySQL、Qdrant、Elasticsearch 和 Embedding 服务的持续深度探测；
外部依赖 SLA 应由独立监控或后续诊断端点负责。

## 6. 生命周期与测试

应用在初始化全部资源后才把 `app.state.ready` 设置为 `True`。关闭时按初始化
逆序释放资源；单个资源关闭失败会记录异常，但不会阻止其余资源继续释放。

`create_app()` 允许测试关闭真实 lifespan，从而在没有基础设施的环境下验证
中间件、健康检查、输入校验和 SSE 协议。

## 7. CI

`.github/workflows/ci.yml` 包含两个独立任务：

- backend：Ruff、格式、108 个测试、Prompt 离线评测、召回评测集校验；
- frontend：锁文件安装、TypeScript 检查和 Vite 生产构建。

外部服务在线评测不进入默认 PR 门禁，避免 CI 依赖生产密钥和长生命周期服务。
