# 招商规划模块设计

日期：2026-06-07

## 背景

ShopView 已有收益地图、经营单元、合同台账、合同柜位绑定和收益汇总能力。下一阶段需要在收益图基础上扩展招商规划，用数据支撑两类招商场景：

- 某个厅房或局部区域有空铺、低效铺位，需要快速补位或替换。
- 某个楼层或多个楼层空置，需要做整层、片区级招商方案和收益测算。

第一版选择“独立招商规划模块 + 双模式 MVP + 招商机会闭环”的路线。

## 目标

- 新增与收益地图同级的“招商规划”模块。
- 支持“铺位补位”和“整层/片区规划”两种模式。
- 复用收益地图的门店、楼层、柜位、面积、当前收益、当前合同数据。
- 按手填新合同条件估算未来收益，并和当前收益对比。
- 将招商机会沉淀为可跟进事项，支持状态、负责人和跟进记录。

## 非目标

- 第一版不做自动招商推荐模型。
- 第一版不做业态默认合同模板库。
- 第一版不强制从相似历史合同复制条件。
- 第一版不替代正式合同审批和签约系统。
- 第一版不自动写入 ERP 合同主数据。

## 模块结构

左侧导航新增“招商规划”，与“收益地图”同级。

模块内包含四个页面：

1. 规划总览
   - 展示待招商、洽谈中、已签约、放弃机会数量。
   - 展示预计收益提升、空置面积、即将到期面积、重点楼层。
   - 展示最近跟进记录。

2. 铺位补位
   - 面向单铺位、厅房局部补位、低效铺位替换。
   - 支持从收益地图选中柜位后跳转进入。
   - 带入门店、楼层、铺位、面积、当前品牌、当前合同、当前收益。
   - 手填新合同条件后生成招商机会。

3. 整层/片区规划
   - 面向楼层、多楼层或片区整体招商。
   - 选择门店和一个或多个楼层。
   - 批量列出空置、低效、到期铺位。
   - 勾选铺位后形成规划项目，并汇总项目收益测算。

4. 招商机会池
   - 管理所有招商机会。
   - 支持按状态、门店、楼层、负责人筛选。
   - 点击机会打开详情抽屉，支持改状态、加跟进记录、更新测算方案。

## 与收益地图联动

收益地图继续负责展示现状和铺位收益。招商规划负责把现状转成行动。

收益地图选中柜位后，增加“创建招商机会”入口。点击后跳转到招商规划的铺位补位表单，并携带：

- store_id
- floor_id
- unit_id
- unit_code
- unit_area
- current_brand
- current_contract_id
- current_revenue
- selected_date_range

招商规划读取这些参数后，初始化铺位补位表单。

## 数据模型

### merchant_planning_projects

用于整层/片区规划。

核心字段：

- id
- name
- store_id
- floor_ids
- scope_type：FLOOR、MULTI_FLOOR、AREA
- target_description
- owner_user_id
- status：DRAFT、ACTIVE、COMPLETED、CANCELLED
- current_annual_revenue
- estimated_annual_revenue
- estimated_lift_amount
- estimated_lift_rate
- total_area
- created_by
- created_at
- updated_at

### merchant_opportunities

用于单铺位机会，也可归属到规划项目。

核心字段：

- id
- project_id，可为空
- source_type：REVENUE_MAP、MANUAL、PROJECT
- store_id
- floor_id
- unit_id
- unit_code
- unit_area
- current_brand
- current_contract_id
- current_annual_revenue
- target_category
- target_brand
- owner_user_id
- status：TODO、NEGOTIATING、SIGNED、ABANDONED
- expected_sign_date
- priority：P0、P1、P2
- estimated_annual_revenue
- estimated_lift_amount
- remark
- created_by
- created_at
- updated_at

状态含义：

- TODO：待招商
- NEGOTIATING：洽谈中
- SIGNED：已签约
- ABANDONED：放弃

### merchant_calculation_scenarios

保存测算方案和合同条件。

核心字段：

- id
- opportunity_id
- cooperation_mode：LEASE、JOINT_OPERATION、OTHER
- monthly_rent
- rent_unit_price
- commission_rate
- guaranteed_amount
- expected_monthly_sales
- manual_monthly_revenue
- decoration_days
- vacancy_days
- contract_start_date
- contract_end_date
- estimated_monthly_revenue
- estimated_annual_revenue
- estimated_lift_amount
- calculation_snapshot
- created_by
- created_at
- updated_at

### merchant_follow_ups

保存机会跟进记录。

核心字段：

- id
- opportunity_id
- follow_up_at
- follow_up_type
- content
- next_action
- next_follow_up_at
- created_by
- created_at

## 测算逻辑

第一版按手填新合同条件估算，不引入复杂模型。

### 租赁

年收益 = 月租金 x 第一年度有效经营月数

如果只填写租金单价，则：

月租金 = 租金单价 x 铺位面积

### 联营

月收益 = max(预计月销售额 x 扣点, 保底金额)

年收益 = 月收益 x 第一年度有效经营月数

### 其他

使用手填预计月收益：

年收益 = 手填预计月收益 x 第一年度有效经营月数

### 装修期和空置期

第一年度有效经营月数 = 12 - ceil((装修期天数 + 空置期天数) / 30)

最小值为 0，最大值为 12。

### 当前收益基准

当前收益使用收益地图同口径铺位历史收益，并按当前筛选周期折算年化值。

例如筛选周期为 N 天：

当前年化收益 = 周期收益 / N x 365

整层/片区规划的收益测算为所选铺位机会的汇总。

## 候选铺位口径

候选铺位来自现有经营单元、合同绑定、合同台账和收益地图汇总。

- 空置：筛选日期范围内没有有效合同绑定，或合同绑定状态不是 ACTIVE。
- 到期：有效合同结束日期在筛选基准日后 90 天内。
- 低效：当前年化收益低于同楼层铺位年化收益中位数的 60%，且该铺位有有效收益数据。

低效阈值第一版作为后端常量实现，后续再做成参数库配置。

## 接口设计

新增后端路由：`/api/merchant-planning`

接口：

- `GET /overview`
  - 返回机会状态分布、收益提升汇总、重点楼层、最近跟进。

- `GET /candidates`
  - 返回候选铺位。
  - 支持门店、楼层、状态类型过滤：空置、低效、到期。

- `POST /projects`
  - 创建整层/片区规划项目。

- `GET /projects`
  - 查询规划项目列表。

- `GET /projects/{id}`
  - 查询规划项目详情、关联机会和汇总测算。

- `POST /opportunities`
  - 创建招商机会。

- `GET /opportunities`
  - 查询招商机会列表。

- `GET /opportunities/{id}`
  - 查询招商机会详情。

- `PUT /opportunities/{id}`
  - 更新机会状态、负责人、目标业态、目标品牌、预计签约日期等。

- `POST /opportunities/{id}/follow-ups`
  - 新增跟进记录。

- `POST /calculations/preview`
  - 不落库预览测算结果。

## 权限

新增权限：

- `merchant_planning.view`
- `merchant_planning.manage`

查看权限允许进入总览、列表和详情。管理权限允许创建项目、创建机会、更新状态、保存测算、写跟进记录。

## 前端实现范围

新增文件建议：

- `client/src/pages/merchant-planning.tsx`
- `client/src/hooks/useMerchantPlanning.ts`

改动现有文件：

- `client/src/components/navigation-sidebar.tsx`
- `client/src/pages/main-dashboard.tsx`
- `client/src/lib/module-permissions.ts`
- `client/src/pages/revenue-map.tsx`

前端页面先采用现有 ShopView 管理后台风格，避免做营销式页面。布局以表格、筛选、详情抽屉、指标卡、地图联动为主。

## 后端实现范围

新增文件建议：

- `python_app/routers/merchant_planning.py`
- `python_app/alembic/versions/<revision>_create_merchant_planning_tables.py`

改动现有文件：

- `python_app/main.py`
- `python_app/routers/authz.py` 或权限初始化所在模块
- `python_app/models/models.py`
- `python_app/schemas/schemas.py`

后端候选铺位数据应优先复用现有收益地图、经营单元、合同绑定和合同台账查询能力。不要绕过现有 `unit_id` 链路。

## 测试与验证

需要覆盖：

- 租赁、联营、其他三种测算模式。
- 装修期、空置期导致有效经营月数变化。
- 单铺位机会创建和状态流转。
- 整层/片区项目汇总多个机会的收益。
- 收益地图跳转招商规划时参数正确带入。
- 权限不足用户无法管理机会。

建议验证命令：

- `npm run build --prefix client`
- `python3 -m py_compile python_app/routers/merchant_planning.py`
- 如有后端测试框架，补充针对测算函数和接口的单元测试。
