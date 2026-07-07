# 确认收入占比日报设计

## 背景

财务人员在 `凭证匹配` 页面确认卡券业务与财务凭证明细后，需要每天查看这些已确认明细按销售收入占比折算后的确认收入金额，快速判断当天已经确认了多少钱、占当天销售收入多少。

现有 `卡券月结` 已经通过 `activity_coupon_revenue_movement` 固化了已确认凭证匹配行的每日收入变动口径。新页面第一版只做查看，不重新计算、不刷新每日变动、不确认月结，避免把日报查看页做成另一个操作入口。

## 目标

新增只读页面 **确认收入占比**，放在 `财务管理 > 活动结算` 下，和 `凭证匹配`、`卡券月结` 同组。

页面采用汇总优先布局：

- 先显示当天确认收入金额、业务金额、销售收入和确认收入占比。
- 再显示按门店聚合的确认收入。
- 最后显示已确认收入变动明细，便于追溯到门店、券种和凭证匹配来源。

## 业务口径

数据来源以 `activity_coupon_revenue_movement` 为主。该表由 `卡券月结` 的每日变动重建流程生成，来源包括 `activity_coupon_voucher_match` 中已经确认的匹配行。

页面筛选日期按财务确认发生日期计算，即关联 `activity_coupon_voucher_match.confirmed_at` 后过滤确认时间；明细中的 `business_date` 仍作为卡券业务发生日展示。这样页面回答的是“财务当天确认了多少钱”，而不是“某个业务发生日有多少卡券收入变动”。

确认收入金额沿用卡券月结口径：

```text
confirmed_revenue_amount = business_amount * revenue_rate
```

其中：

- `business_amount` 来自已确认凭证匹配行的业务金额。
- `revenue_rate` 来自每日门店券种收入占比快照。
- `actual_revenue_amount` 是后端已保存的折算结果，页面和接口直接汇总这个字段。

缺收入占比的行保持 `rate_status = MISSING_RATE`，`actual_revenue_amount` 按现有月结口径为 0。页面需要单独展示缺占比行数和异常状态，避免财务把 0 元误解为真实收入。

确认收入占比按页面筛选范围计算：

```text
confirmed_revenue_ratio = confirmed_revenue_amount / sales_revenue_amount
```

`sales_revenue_amount` 第一版建议从同一口径的收入占比快照或其可用销售收入字段汇总。如果当前快照表没有可直接汇总的销售收入字段，接口返回 `null`，页面显示 `--`，但不影响确认收入金额和明细展示。

## 后端接口

新增只读接口：

```http
GET /api/activity-analysis/coupon-confirmed-revenue-daily
```

查询参数：

- `start_date`：必填，财务确认日期起始，按 `activity_coupon_voucher_match.confirmed_at` 过滤。
- `end_date`：可选，财务确认日期结束；为空时等于 `start_date`。
- `market_code`：可选，门店编码；为空时查询全部门店。
- `coupon_type`：可选，券种；第一版可先预留参数，前端不展示筛选。

权限：

- 新增 `activity_settlement.confirmed_revenue.view`。
- 这是只读权限，不包含刷新每日变动、月结确认或 NC 结转登记权限。

返回结构建议：

```json
{
  "summary": {
    "movement_count": 12,
    "missing_rate_count": 1,
    "business_amount": 128600.0,
    "confirmed_revenue_amount": 31240.0,
    "sales_revenue_amount": 842000.0,
    "confirmed_revenue_ratio": 0.0371
  },
  "store_summary": [
    {
      "market_code": "603",
      "store_name": "新世纪",
      "movement_count": 3,
      "missing_rate_count": 0,
      "business_amount": 5600.0,
      "confirmed_revenue_amount": 1260.0,
      "sales_revenue_amount": 120000.0,
      "confirmed_revenue_ratio": 0.0105
    }
  ],
  "rows": [
    {
      "id": 101,
      "business_date": "2026-06-28",
      "period_month": "2026-06",
      "market_code": "603",
      "store_name": "新世纪",
      "coupon_type": "Q",
      "coupon_name": "后台赠券",
      "match_type": "DEBIT_USE",
      "movement_direction": "DECREASE",
      "confirmed_at": "2026-06-28T15:30:00",
      "confirmed_by_name": "财务人员",
      "business_amount": 5600.0,
      "revenue_rate": 0.225,
      "actual_revenue_amount": 1260.0,
      "rate_status": "OK",
      "voucher_match_id": 88,
      "voucher_detail_id": "..."
    }
  ]
}
```

## 前端页面

新增页面文件建议：

```text
client/src/pages/activity-analysis/confirmed-revenue-daily.tsx
```

导航位置：

- `财务管理 > 活动结算 > 确认收入占比`
- 可放在 `凭证匹配` 之后、`卡券月结` 之前，表示从确认明细到日报查看再到月结。

页面内容：

- 筛选区：开始日期、结束日期、门店、刷新。
- 汇总卡片：确认收入金额、业务金额、当天销售收入、确认收入占比、明细行数、缺占比行。
- 门店汇总表：门店、行数、缺占比行、业务金额、确认收入金额、销售收入、确认收入占比。
- 明细表：确认时间、业务发生日、门店、券种、匹配方向、业务金额、收入占比、确认收入金额、状态、凭证匹配 ID、凭证明细 ID。

页面不包含：

- 刷新每日变动按钮。
- 月结草稿生成按钮。
- 月结确认按钮。
- NC 结转登记入口。

## 错误和空状态

- 如果没有任何每日收入变动，页面显示空状态，提示先在 `卡券月结` 页面刷新每日变动。
- 如果存在缺收入占比行，汇总卡片和对应明细行展示异常状态。
- 如果销售收入金额不可用，确认收入占比显示 `--`，同时保留确认收入金额和明细。
- 接口缺表时返回清晰错误，说明需要先执行卡券月结相关迁移或刷新流程。

## 测试范围

后端测试：

- 只汇总 `activity_coupon_revenue_movement` 中关联匹配确认日期和门店范围命中的行。
- `actual_revenue_amount` 汇总为确认收入金额，不在日报接口中重新计算业务收入。
- `MISSING_RATE` 行计入缺占比行数，确认收入金额按 0 汇总。
- 门店汇总和总汇总一致。
- 无销售收入金额时占比返回 `null`。

前端测试：

- 页面请求参数包含日期和门店筛选。
- 汇总卡片展示确认收入金额、业务金额和缺占比行。
- 缺收入占比行展示异常状态。
- 页面不渲染刷新每日变动、月结确认或 NC 结转按钮。

## 非目标

第一版不做以下事项：

- 不从 `activity_coupon_voucher_match` 即时重算日报。
- 不触发每日收入变动重建。
- 不生成或确认卡券月结。
- 不登记 NC 结转。
- 不做趋势图和跨月分析。
