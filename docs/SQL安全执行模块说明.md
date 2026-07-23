# SQL 安全执行模块说明

## 1. 改造目标

问数 Agent 生成的 SQL 属于不可信输入。Prompt 协议可以降低模型输出错误概率，
但不能作为数据库执行的唯一安全边界。本次改造在 SQL 进入数仓前增加独立守卫，
并修复“校正后的 SQL 未重新校验就直接执行”的流程缺口。

## 2. 执行链路

```text
模型生成只读 SQL
    -> Prompt 输出协议校验
    -> Repository SQLGuard 再次审计
       -> SQLGlot AST 解析与表级授权
    -> EXPLAIN 数据库校验
       -> 成功：执行前再次 SQLGuard 审计
       -> 失败：在有限预算内让模型修正
                -> 修正后的 SQL 重新进入 SQLGuard + EXPLAIN
                -> 修正预算耗尽后拒绝执行
    -> 应用层查询超时
    -> 最大结果行数截断
    -> SSE 返回 list[dict]
```

## 3. 安全边界

`SQLGuard` 采用保守策略，只接受以 `SELECT` 或 `WITH` 开头的单条查询，并拒绝：

- 多语句和 SQL 注释；
- 写入、DDL、权限和动态执行操作；
- `SLEEP`、`BENCHMARK`、`LOAD_FILE` 和锁函数；
- `INTO OUTFILE`、`FOR UPDATE` 等文件写入或锁定语句；
- 对 MySQL 系统 Schema 的显式访问；
- 超过配置长度的 SQL。

守卫会屏蔽字符串字面量和引用标识符后再检查 SQL 结构，避免把普通文本中的
`DROP` 等单词误判为操作关键字。随后使用 MySQL 方言解析 SQL AST，提取真实
表引用；普通 CTE 别名不会被误判为物理表。

每轮 Agent 查询只能访问 `table_infos` 已提供的物理表，显式引用其他 Schema
或上下文之外的表会在 `EXPLAIN` 和执行前被拒绝。修正后的 SQL 同样经过该边界。
这里的“授权”约束模型只能使用已召回的查询上下文，不代表用户角色、行级或
列级数据权限。

这是一层应用防御。生产环境仍必须使用独立的只读数仓账号，并在数据库或代理层
配置资源组、审计、行列级权限和查询成本限制。

## 4. 有限修正

SQL 状态记录 `correction_attempts`。校验失败后：

1. 未达到 `max_correction_attempts` 时进入 `correct_sql`；
2. 修正完成后返回 `validate_sql`，不会直接进入执行节点；
3. 预算耗尽后进入 `reject_sql`，通过 SSE 返回错误并终止图执行。

该设计同时避免未验证 SQL 执行和无限修正循环。

## 5. 配置

```yaml
sql_execution:
  max_sql_length: 12000
  max_result_rows: 1000
  query_timeout_seconds: 30
  max_correction_attempts: 2
```

对应环境变量：

```text
SQL_MAX_LENGTH=12000
SQL_MAX_RESULT_ROWS=1000
SQL_QUERY_TIMEOUT_SECONDS=30
SQL_MAX_CORRECTION_ATTEMPTS=2
```

`max_result_rows` 限制返回到应用内存和前端的数据量；它不能替代数据库查询成本
治理。`query_timeout_seconds` 限制应用等待时间，数据库端仍应设置对应超时。

## 6. 自动化验证

测试覆盖：

- 单条只读查询和字符串字面量正常通过；
- 多语句、注释、写操作、文件访问、锁、系统 Schema 和耗时函数被拒绝；
- SQL AST 只允许访问当前 Agent 上下文中的表，并正确识别 CTE；
- Repository 在 `EXPLAIN` 和最终执行前都调用守卫；
- 返回结果按配置截断；
- SQL 修正后必须重新进入校验节点；
- 修正预算耗尽后拒绝执行；
- API 拒绝空问题和超长问题。

运行：

```bash
uv run python -m pytest -q
uv run python -m ruff check app tests
uv run python -m ruff format --check app tests
```
