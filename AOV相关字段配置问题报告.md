# AOV 相关字段配置问题报告

## 1. 问题

`conf/meta_config.yaml` 中 AOV 的配置写的是：

```yaml
- name: AOV
  description: 全称Average Order Value，表示所有订单的成交金额平均值。
  relevant_columns:
    - fact_order.order_quantity   # 数量字段
```

但 AOV 的定义是“订单成交金额的平均值”，应依赖金额字段 `fact_order.order_amount`，而不是数量字段 `order_quantity`。本 PR 修正这一行配置，并附上分析报告。

## 2. 为什么最终 SQL 仍然是对的

以实测问题「查询 2025 年 1 月 1 号到 3 号的订单成交平均额」为例，链路实际是这样走的：

1. `merge_retrieved_info` 第 2 步会按 `AOV.relevant_columns` 把 `fact_order.order_quantity` 补进候选表 `fact_order`。这一步由程序完成，所以 **合并后的候选表上下文里确实有 `order_quantity`**。
2. `filter_table` 把 `query + table_infos` 交给模型裁剪字段。该节点的输入里 **没有 `metric_infos`**，模型不知道 `order_quantity` 是指标依赖字段，只看到它的描述是“订单中商品的购买数量”，与“平均额”无关，于是把它删掉。
3. `filter_metric` 只按名称筛选指标，不修改任何字段，AOV 被保留下来。
4. `generate_sql` 拿到的表上下文是 `order_id`、`date_id`、`order_amount`（`order_id` 作为主键被兜底保留）。提示词规定“只允许使用数据表中真实存在的字段”，模型只能使用 `order_amount`，最终生成：

```sql
SELECT AVG(order_amount) AS `订单成交平均额` FROM fact_order WHERE date_id BETWEEN 20250101 AND 20250103;
```

结果符合 AOV 的本意。

## 3. 结论

**SQL 正确是两个问题相互抵消的结果，并不是链路正确处理了 AOV 口径：**

- 配置错误：AOV 依赖了数量字段 `order_quantity`；
- 链路缺陷：`filter_table` 不知道指标依赖关系，把它当成无关字段裁掉了，错误配置因此没有进入 `generate_sql` 的上下文。

但也不能反过来理解成“配置错了，SQL 一定会算错”：

- 当问题同时涉及金额和数量（例如“成交平均金额和平均每个订单的商品数量”）时，`filter_table` 会保留 `order_quantity`，它会进入 `generate_sql`；此时生成的 SQL 仍然正确，`AVG(order_amount)` 和 `AVG(order_quantity)` 各归各位。
- 隔离实验（跳过 `filter_table`，直接把 `order_quantity` 放进 `generate_sql`，模拟上述分支）：
  - AOV 描述和别名保持原文时，7 种金额类问法全部按 `order_amount` 生成；
  - 把描述改成中性（“衡量订单维度的平均水平”）、去掉别名后，2/2 生成 `AVG(order_quantity)`。

说明：描述明确时，模型会按语义纠正；描述不明确时，错误的 `relevant_columns` 就会成为唯一依据并直接决定 SQL。因此这是一个**潜在风险**，不是当前必然出错的缺陷：改描述、换模型、增加指标或问题措辞变化，都可能让错误配置真正生效。

## 4. 附带发现（不在本 PR 范围内）

`filter_table` 的输入只有 `query` 和 `table_infos`，没有 `metric_infos`，也没有“指标依赖字段必须保留”的保护。结果是：指标依赖字段是否进入 `generate_sql`，取决于问题里有没有相关表述，而不是取决于指标本身。建议后续在 `filter_table` 裁剪后增加程序兜底：把 `metric_infos` 中 `relevant_columns` 对应的字段强制保留（或做一致性校验），避免指标口径字段被模型裁掉。

## 5. 修改配置后的生效方式

运行时使用的 `relevant_columns` 来自 Qdrant `metric_info_collection` 的 payload，`column_metric` 关系来自 Meta MySQL，二者都由构建脚本写入：

```powershell
uv run python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
```

只改 YAML 不重建索引，问数链路仍会读到旧的 `order_quantity`。另外构建脚本是按主键 INSERT、Qdrant 也使用新的随机 id upsert，重复执行前需要先清空相关元数据表并重建 collection，否则会出现主键冲突或重复向量点。

重建后再问「2025 年 1 月 1 日到 3 日的 AOV 是多少」，预期 SQL 仍为 `AVG(order_amount)`，且 `generate_sql` 上下文里的 `AOV.relevant_columns` 应为 `fact_order.order_amount`；纯金额问题不应再因为这个指标额外带入 `order_quantity`。
