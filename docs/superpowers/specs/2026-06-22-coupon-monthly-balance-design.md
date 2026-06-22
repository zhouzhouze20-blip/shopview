# 卡券月结余额设计

## 背景

凭证匹配页面已经可以把卡券业务汇总行和财务凭证明细确认匹配。财务接下来需要按门店、券种和月份计算卡券实际销售收入余额，并据此在 NC 中手工做结转。NC 手工结转完成后，ShopView 需要登记这笔结转金额，并从卡券余额中扣减。

第一版目标是把月结口径固化到 ShopView：已确认凭证匹配产生卡券收入变动，财务在 ShopView 手工登记 NC 结转，系统生成并确认月度余额快照。第一版不做 NC 凭证自动识别、不做审批流、不生成 NC 凭证草稿。

## 业务口径

每日卡券收入变动来源于 `activity_coupon_voucher_match` 中已确认的匹配行，确认状态只包含 `AUTO_CONFIRMED` 和 `MANUAL_CONFIRMED`。

系统按 `business_date + market_code + coupon_type` 读取 `activity_coupon_revenue_rate_snapshot.effective_revenue_rate`。实际销售收入变动额为：

```text
actual_revenue_amount = business_amount * effective_revenue_rate
```

匹配方向含义如下：

- `CREDIT_BUY`：买券或充值类贷方，增加卡券收入余额。
- `DEBIT_USE`：用券类借方，减少卡券收入余额。

月度余额公式为：

```text
ending_balance =
  opening_balance
  + current_month_increase
  - current_month_decrease
  - current_month_nc_carryover_amount
```

其中 `current_month_nc_carryover_amount` 来自财务在 ShopView 手工登记的 NC 结转金额。系统允许同一月份、门店、券种登记多笔 NC 结转，月结时汇总扣减。

如果找不到收入占比，相关每日变动进入异常状态，不允许确认该门店券种对应月份的月结。

## 数据模型

### activity_coupon_revenue_movement

保存每日卡券收入变动明细。建议字段：

- `id`
- `business_date`
- `period_month`
- `market_code`
- `business_store_code`
- `coupon_type`
- `coupon_name`
- `match_type`
- `voucher_match_id`
- `voucher_detail_id`
- `business_amount`
- `revenue_rate`
- `actual_revenue_amount`
- `rate_snapshot_date`
- `rate_status`
- `movement_direction`
- `created_at`
- `updated_at`

约束和索引：

- `voucher_match_id` 唯一，避免同一匹配行重复生成变动。
- 按 `period_month, market_code, coupon_type` 建索引，服务月结聚合。
- 按 `rate_status` 建索引，服务异常检查。

### activity_coupon_nc_carryover

保存 NC 手工结转登记。建议字段：

- `id`
- `period_month`
- `market_code`
- `coupon_type`
- `coupon_name`
- `nc_voucher_no`
- `carryover_amount`
- `carryover_date`
- `remark`
- `created_by`
- `created_at`
- `updated_at`

约束和索引：

- 允许同一月份、门店、券种多笔结转。
- 按 `period_month, market_code, coupon_type` 建索引，服务月结扣减汇总。

### activity_coupon_monthly_balance

保存月度余额快照。建议字段：

- `id`
- `period_month`
- `market_code`
- `coupon_type`
- `coupon_name`
- `opening_balance`
- `current_month_increase`
- `current_month_decrease`
- `nc_carryover_amount`
- `ending_balance`
- `missing_rate_count`
- `movement_count`
- `status`
- `confirmed_by`
- `confirmed_at`
- `created_at`
- `updated_at`

约束和索引：

- `period_month, market_code, coupon_type` 唯一。
- `status` 第一版只需要 `DRAFT` 和 `CONFIRMED`。
- 已确认月结不被普通刷新覆盖。

## 后端接口

新增接口放在活动分析模块下，沿用现有权限 `ACTIVITY_ANALYSIS_PERMISSION`。

### POST /api/activity-analysis/coupon-revenue-movements/rebuild

按月份和可选门店，从已确认凭证匹配行重建每日收入变动草稿。

处理规则：

- 只读取 `AUTO_CONFIRMED` 和 `MANUAL_CONFIRMED`。
- 对同一个 `voucher_match_id` 使用 upsert。
- 找到收入占比时写入 `rate_status = OK`。
- 找不到收入占比时写入 `rate_status = MISSING_RATE`，`actual_revenue_amount` 置为 0。
- 如果对应月结已经确认，接口拒绝覆盖。

### GET /api/activity-analysis/coupon-monthly-balances

查询月度余额。支持月份、门店、券种、状态筛选。

返回月结金额、缺失收入占比行数、变动行数、NC 结转金额和确认信息。

### POST /api/activity-analysis/coupon-monthly-balances/rebuild

汇总指定月份的每日变动和 NC 结转，生成或刷新月结草稿。

处理规则：

- 上月期末余额读取上一期间 `CONFIRMED` 或最新草稿的 `ending_balance`。如果没有历史记录，期初为 0。
- `CREDIT_BUY` 汇总到 `current_month_increase`。
- `DEBIT_USE` 汇总到 `current_month_decrease`。
- NC 结转登记汇总到 `nc_carryover_amount`。
- 如果目标月结已确认，接口拒绝覆盖。

### POST /api/activity-analysis/coupon-nc-carryovers

登记 NC 手工结转。

必填字段：

- `period_month`
- `market_code`
- `coupon_type`
- `carryover_amount`
- `nc_voucher_no`

如果目标月份、门店、券种已经确认月结，第一版拒绝新增或修改登记，避免破坏已确认快照。

### POST /api/activity-analysis/coupon-monthly-balances/confirm

确认月结快照。

确认前校验：

- 不存在 `missing_rate_count > 0` 的行。
- 指定月份的每日变动已经重建。
- 指定月份的余额草稿已经生成。

确认后写入 `status = CONFIRMED`、`confirmed_by`、`confirmed_at`。

## 前端页面

在活动分析区域新增“卡券月结”页面，放在“凭证匹配”旁边。

第一版页面包含：

- 月份筛选。
- 门店筛选。
- 刷新每日变动按钮。
- 生成或刷新月结草稿按钮。
- 月结汇总表。
- 登记 NC 结转弹窗。
- 确认月结按钮。

月结汇总表字段：

- 门店。
- 券字母。
- 券名称。
- 上月余额。
- 本月增加。
- 本月减少。
- NC 结转。
- 期末余额。
- 缺收入占比行数。
- 变动行数。
- 状态。
- 确认人。
- 确认时间。

异常展示：

- 缺收入占比的行用醒目状态标识，并禁止确认月结。
- 期末余额为负时标识为风险，但不禁止确认。

## 测试范围

后端测试：

- 已确认匹配行生成每日变动。
- 未确认和已排除匹配行不参与计算。
- 缺收入占比时写入异常并阻止确认月结。
- 多笔 NC 结转按月份、门店、券种汇总扣减。
- 已确认月结不能被刷新覆盖。

前端测试：

- 月份、门店筛选参数正确。
- NC 结转登记成功后刷新余额。
- 缺收入占比时确认按钮不可用或提交被后端拒绝并展示错误。

## 非目标

第一版不做以下事项：

- 从 NC 凭证明细自动识别结转凭证。
- 生成 NC 凭证草稿。
- 审批流。
- 历史月结自动冲销。
- 图表和复杂趋势分析。
