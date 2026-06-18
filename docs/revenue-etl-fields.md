# 收益 ETL 写入说明

收益按日入账，月份由数据库触发器按 `revenue_date` 自动生成。销售、收费均使用不含税口径。

## 销售毛利明细

写入表：`unit_revenue_sales_detail`

最小字段：

```sql
INSERT INTO unit_revenue_sales_detail (
  store_id,
  floor_id,
  unit_id,
  unit_code,
  revenue_date,
  source_group_code,
  source_group_name,
  operation_mode,
  supplier_code,
  supplier_name,
  contract_code,
  sales_qty,
  tax_excluded_sales_amount,
  tax_excluded_profit_amount,
  etl_batch_id,
  raw_payload
) VALUES (...);
```

核心口径：

- `revenue_date`：销售发生日期，由 ETL 补入。
- `tax_excluded_sales_amount`：不含税销售。
- `tax_excluded_profit_amount`：不含税销售毛利，汇总时进入销售毛利收益。
- `source_group_code/source_group_name`：富基/ERP 导出的柜组编码和名称。
- `unit_id/unit_code`：匹配到经营单元后写入；未能唯一匹配的数据不要写入汇总明细，写入未匹配收益池。

## 收费明细

写入表：`unit_revenue_fee_detail`

最小字段：

```sql
INSERT INTO unit_revenue_fee_detail (
  id,
  store_id,
  floor_id,
  unit_id,
  unit_code,
  revenue_date,
  source_group_code,
  source_group_name,
  contract_code,
  contract_name,
  fee_type_code,
  fee_type_name,
  tax_included_amount,
  tax_excluded_amount,
  etl_batch_id,
  raw_payload
) VALUES (...);
```

核心口径：

- `revenue_date`：实际收费日期；哪一天收费，就算哪一天收益。
- `tax_excluded_amount`：不含税/去税金额，汇总时进入收费收益。
- `tax_included_amount`：含税金额，仅做明细展示和对账参考。
- `id`：收费明细主键，`VARCHAR(50)`，由 ETL 传入稳定唯一值。

## 未匹配收益池

写入表：`unmatched_revenue_items`

用于柜组无法唯一匹配经营单元，尤其是超市等暂未确定分摊规则的数据。

```sql
INSERT INTO unmatched_revenue_items (
  store_id,
  revenue_date,
  source_category,
  source_group_code,
  source_group_name,
  contract_code,
  supplier_code,
  supplier_name,
  amount,
  reason,
  etl_batch_id,
  raw_payload
) VALUES (...);
```

字段说明：

- `source_category`：`SALES`、`FEE`、`EXTRA`。
- `amount`：对应不含税金额。
- `reason`：建议填 `UNMATCHED_UNIT`、`MULTI_UNIT_PENDING_SPLIT` 等。
- `status`：默认 `PENDING`。

## 重算日汇总

ETL 写完明细后，调用接口重算：

```http
POST /api/revenue-map/recalculate
```

请求体：

```json
{
  "start_date": "2026-06-01",
  "end_date": "2026-06-30"
}
```

重算后写入 `unit_daily_revenue_summary`：

```text
total_amount = sales_gross_profit_amount + fee_amount + extra_amount
```
