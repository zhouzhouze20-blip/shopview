# 中心年中庆活动页面与积分查询优化设计

## 背景

现有 `积分活动核对` 页面用于核对购物中心黑金、黑钻会员的多倍积分。管理员代看白海燕 `user_id=606` 和王薇 `user_id=667` 时，页面能够显示菜单，但 `/api/activity-analysis/points/dashboard` 的积分汇总 SQL 超过数据库 30 秒语句超时，页面最终显示“积分数据加载失败”。

只读核对已经确认：

- 白海燕具有 `mall_planning` 角色、`activity_analysis.points.view` 权限以及门店 `1/2/3/4` 数据范围。
- 王薇具有 `store_director + contract_viewer` 角色、`activity_analysis.points.view` 权限以及门店 `1` 数据范围。
- 两人的有效门店范围都覆盖购物中心 ERP 市场 `601`，当前失败不是空权限，而是积分汇总查询超时。
- `salegoodslist` 约 15 GB、`salehead` 约 3.7 GB。当前查询在大表上使用 `h.rqsj::date`，无法充分利用时间索引；页面还会同时执行部门选项和仪表板两次重查询。

本活动从 `2026-07-09` 开始，不需要读取该日期以前的业务数据。

## 目标

本次只调整现有积分活动页面：

1. 左侧菜单、顶部页签和页面主标题统一显示为 **中心年中庆活动**。
2. 保留内部模块 ID `points-activity-analysis`、权限编码 `activity_analysis.points.view` 和现有 API 路径，不影响已经配置的角色权限。
3. 后台查询硬性限定从 `2026-07-09` 开始，不扫描活动开始日前的销售、付款或积分数据。
4. 重写积分汇总查询并取消页面重复请求，使 `2026-07-09` 至 `2026-07-10` 的查询目标控制在 10 秒内。
5. 将该积分接口的数据库查询超时和 Nginx 读取超时提高到 60 秒，作为优化后的安全兜底，而不是依靠延长超时解决性能问题。
6. 明确区分无权限、权限范围内无数据和后端查询异常。

## 非目标

- 不修改白海燕、王薇或其他用户的角色和数据范围。
- 不修改 `activity_analysis.points.view` 的授权含义。
- 不扩展到销售看板、合同或其他活动分析页面。
- 不建设每日预汇总表或异步 ETL。
- 不在本次新增大表索引；查询先利用现有的时间、小票和主键索引完成优化。
- 不删除 `/api/activity-analysis/points/department-options`，保留它供现有调用兼容，但新页面不再单独请求它。

## 页面命名与日期边界

界面显示名称统一为 `中心年中庆活动`：

- `client/src/lib/navigation-items.ts` 中的左侧菜单来源。
- `client/src/pages/main-dashboard.tsx` 中 `MODULE_LABELS` 的工作区页签标题来源。
- `client/src/pages/activity-analysis/points.tsx` 中的页面主标题。

内部模块 ID、查询 key、路由、API 和权限编码保持不变。

日期规则：

- 前端开始日期默认值固定为 `2026-07-09`，结束日期默认值为当前本地日期。
- 开始日期和结束日期输入框的最小可选日期均为 `2026-07-09`。
- 如果当前日期早于 `2026-07-09`，结束日期使用 `2026-07-09`，避免产生倒置区间。
- 后端以同一个常量定义活动开始日。请求的开始日期早于活动开始日时，实际开始日期取 `2026-07-09`。
- 后端先校验原始开始日期是否晚于结束日期；若是则返回 HTTP 400，并提示日期范围无效。
- 原始日期顺序有效但结束日期早于 `2026-07-09` 时，接口直接返回结构完整的空响应，不访问 `salehead`、`salegoods`、`salegoodslist`、`sellpaygoods` 或 `order_point`。

## 前端数据流

当前页面并发请求：

```text
/api/activity-analysis/points/department-options
/api/activity-analysis/points/dashboard
```

两个接口都构建积分基础数据，造成同一时间范围和权限范围被重复查询。优化后页面只请求 dashboard：

```text
日期、部门、柜组、会员筛选
  -> /api/activity-analysis/points/dashboard
  -> summary + department_options + departments + groups + members + tickets
  -> 同一次响应渲染筛选项、汇总和明细
```

`DashboardResponse` 增加现有后端已经返回的 `department_options` 类型。部门下拉框直接读取 dashboard 响应，不再创建独立的 `departmentOptions` React Query。刷新按钮只刷新 dashboard。

部门筛选变化后，dashboard 仍返回未应用部门筛选的权限内部门选项，因此切换部门不会丢失可选列表。现有后端已经从 `base_point_rows` 生成 `department_options`，而部门筛选只应用于 `filtered_point_rows`，该行为保持不变。

## 后端查询结构

保留 `/api/activity-analysis/points/dashboard` 的参数和返回结构，重写 `_points_base_sql` 及 dashboard 使用的数据流。

### 1. 先限定有效日期和权限范围

在进入业务大表查询前计算：

```text
effective_start_date = max(requested_start_date, 2026-07-09)
effective_end_exclusive = requested_end_date + 1 day
```

销售时间条件使用可索引的半开区间：

```sql
h.rqsj >= CAST(:effective_start_date AS date)
AND h.rqsj < CAST(:effective_end_exclusive AS date)
```

不再在过滤条件中对 `h.rqsj` 使用 `::date`。市场 `601`、会员等级、作废单据和业务数据范围也在最早阶段应用。

### 2. 建立权限内相关小票集合

先从日期范围内的 `salehead` 取得候选小票，再连接 `sellpaygoods`、`salegoods` 和 `manaframe` 生成权限内的 `scoped_bill_groups`。该集合只保留后续计算需要的：

- 小票号、市场编码、销售时间和销售日期。
- 会员号和会员等级。
- 柜组、部门和门店维度。

门店、部门和柜组权限继续使用 `_points_business_scope_filter_sql`，不得因为性能优化绕过或扩大范围。

### 3. 所有大表只处理相关小票

- `order_point` 先与 `relevant_bills` 连接，再按相关小票汇总实际积分，不再聚合整张 `order_point`。
- `salegoodslist` 先按相关小票号连接，再按市场、销售日期和柜组匹配会计销售额。
- `sellpaygoods` 的付款分摊只针对相关小票聚合。
- `salegoods` 只通过相关小票和行号参与计算。
- 积分倍率、付款方式和券种规则维持现有口径。

### 4. 一次物化，多处汇总

权限内、日期内的积分结果形成一次 `base_point_rows AS MATERIALIZED`。部门、柜组、会员、小票和部门选项均从该小结果集汇总。销售等级汇总也复用已经限定日期和权限的相关小票，不再单独扫描完整日期范围。

当前 `_point_rule_source_status` 会在每次响应末尾对各源表执行精确 `COUNT(*)`。优化后改为从 PostgreSQL 系统目录读取表是否存在及 `reltuples` 估算行数，不再为状态展示扫描 `salegoodslist`、`order_point` 等业务表。

返回字段保持现状，包括：

- `summary`
- `department_options`
- `departments`
- `groups`
- `members`
- `tickets`
- `source_status`

## 超时策略

- 保持 `python_app/models/database.py` 的全局 30 秒语句超时不变，避免无关接口被整体放宽。
- 积分 dashboard 和保留的 department-options 接口在当前事务内将 `statement_timeout` 设置为 60 秒，只影响本次积分请求。
- `config/nginx.conf` 为 `/api/activity-analysis/points/` 增加更具体的 location，将 `proxy_read_timeout` 设置为 60 秒；其他 `/api/` 请求继续使用 30 秒。
- 通过 `gw.princesky.com:8020` 直接访问应用时不会经过该 Nginx location，因此数据库 60 秒是直接访问路径的兜底。
- 正常验收目标仍为 10 秒内完成。60 秒只用于避免短暂负载波动立即失败。

## 权限与错误处理

权限顺序保持不变：

1. `require_permission(..., "activity_analysis.points.view")` 校验功能权限。
2. `load_business_scope` 加载代看用户或登录用户的业务范围。
3. `_points_business_scope_filter_sql` 将门店、部门和柜组范围写入查询。

页面状态：

- HTTP 403：显示“无中心年中庆活动查看权限”。
- HTTP 200 且部门、柜组、会员和小票均为空：显示“当前日期和权限范围内暂无数据”。
- PostgreSQL `QueryCanceled` 或接口 HTTP 504：显示“中心年中庆活动数据查询超时，请缩短日期范围后重试”。
- 其他请求异常：显示“中心年中庆活动数据加载失败，请稍后重试或检查后端服务”。
- 请求失败时不使用全零汇总伪装成功结果。

后端捕获本接口的语句超时后回滚当前只读事务并返回 HTTP 504；其他数据库错误继续按现有异常链路处理，避免把真实 SQL 错误误报为权限问题。

## 测试与验收

### 前端自动化测试

- 导航配置显示 `中心年中庆活动`，模块 ID 仍为 `points-activity-analysis`。
- 页面主标题显示 `中心年中庆活动`。
- 默认开始日期为 `2026-07-09`，日期输入最小值为 `2026-07-09`。
- 页面只创建 dashboard 查询，不再请求 department-options。
- dashboard 的 `department_options` 能渲染部门下拉框。
- 403、504、其他错误和成功空响应显示不同提示。
- 权限编码和 API 路径保持不变。

### 后端自动化测试

- 早于 `2026-07-09` 的开始日期被收敛到活动开始日。
- 结束日期早于活动开始日时返回空响应，且不执行积分业务 SQL。
- 开始日期晚于结束日期时返回 HTTP 400。
- SQL 使用半开时间区间，不再包含 `h.rqsj::date BETWEEN`。
- `order_point`、`salegoodslist` 和付款分摊均由相关小票集合限定。
- `source_status` 只读取系统目录元数据，不再对业务源表执行 `COUNT(*)`。
- 门店、部门和柜组权限参数仍进入所有积分与销售等级计算路径。
- dashboard 返回结构与现有前端兼容。
- 积分接口局部语句超时为 60 秒，其他接口全局超时仍为 30 秒。

### 只读实库验收

使用现有数据库和以下身份范围执行，不修改权限数据：

- 白海燕 `user_id=606`：门店 `1/2/3/4`，另有部门 `6010108`。
- 王薇 `user_id=667`：门店 `1`。

验收时间范围为 `2026-07-09` 至 `2026-07-10`：

- 两位用户均通过功能权限和数据范围校验。
- dashboard 对每位用户的执行时间目标小于 10 秒。
- 两位用户的响应均不触发 60 秒数据库超时。
- 部门选项、汇总和明细来自同一次 dashboard 响应。
- 白海燕和王薇在相同购物中心范围下的结果口径一致；白海燕的其他门店范围不会扩大本页固定市场 `601` 的结果。

## 交付边界

实施完成后交付：

- 页面显示名称调整。
- 前端单请求数据流。
- `2026-07-09` 活动起始日期硬边界。
- 积分 SQL 查询重写。
- 积分接口局部 60 秒超时与 Nginx 专用 60 秒读取超时。
- 自动化测试和白海燕、王薇的只读实库性能记录。

本次不直接部署服务器，也不修改线上角色、权限或数据范围；部署仍按 ShopView 现有发布流程单独执行。
