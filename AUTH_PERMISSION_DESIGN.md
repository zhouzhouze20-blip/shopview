# 账号、权限与数据范围设计草案

## 1. 设计目标

本系统建议采用：

- 一套用户主体
- 两种登录方式：账号密码、企业微信
- 功能权限与数据权限分离
- 数据范围以 `门店 -> 部门 -> 柜组 -> 柜位/经营单元` 为主
- `楼层` 作为展示和筛选维度，不作为默认的主权限边界

这样设计是为了适配当前业务场景：

- 同一楼层可能由多个部门主管分别管理
- 不同主管分管不同柜组
- 合同、账单、收益、商户数据最终都应当能回溯到门店、部门和柜组

## 2. 现有模型与建议改造

当前项目已经具备以下基础：

- `users` 已存在，但仍是单字段 `role` 模式
- `counter_groups` 已包含 `store_id`、`department_code`、`department_name`、`group_code`
- `halls` 与 `hall_group_bindings` 已能表达厅房和柜组关系
- `business_units` 已能作为经营单元的稳定业务主键

建议改造方向：

1. `users` 保留为系统唯一用户主体，不再区分“本地用户”和“企业微信用户”
2. 新增 `user_identities`，承载不同登录方式
3. 新增 `roles / permissions / role_permissions / user_roles`
4. 新增 `departments / posts / user_department_posts`
5. 新增 `data_policies / data_policy_items`
6. 将 `counter_groups` 升级为数据权限核心对象之一
7. 让 `contracts / bills / revenue_data / tenants` 的查询都可反推到 `store + department + group`

## 3. 核心边界

### 3.1 认证边界

- 企业微信负责“身份认证”
- 系统内部负责“角色授权”和“数据范围”
- 企业微信部门不直接等于系统角色

### 3.2 授权边界

权限拆成两层：

- 功能权限：决定用户能不能访问模块、按钮、接口
- 数据权限：决定用户能看到或操作哪些业务数据

### 3.3 数据边界

建议默认主边界如下：

1. `store`
2. `department`
3. `group`
4. `unit`

辅助维度：

- `floor`
- `self`

说明：

- `floor` 可用于筛选和展示
- `floor` 不应默认作为最高粒度的数据授权边界

## 4. 推荐表设计

### 4.1 用户与认证

- `users`
  - `id`
  - `username`
  - `full_name`
  - `mobile`
  - `email`
  - `status`
  - `default_store_id`
  - `last_login_at`
  - `created_at`
  - `updated_at`

- `user_identities`
  - `id`
  - `user_id`
  - `identity_type`
  - `identifier`
  - `credential_hash`
  - `corp_id`
  - `wecom_user_id`
  - `union_id`
  - `is_primary`
  - `last_used_at`

说明：

- `identity_type` 取值建议：`password`、`wecom`
- 一个用户可以绑定多个身份

### 4.2 组织与岗位

- `departments`
  - `id`
  - `store_id`
  - `dept_code`
  - `dept_name`
  - `parent_id`
  - `manager_user_id`
  - `is_active`

- `posts`
  - `id`
  - `post_code`
  - `post_name`
  - `level`
  - `is_active`

- `user_department_posts`
  - `id`
  - `user_id`
  - `store_id`
  - `department_id`
  - `post_id`
  - `is_primary`
  - `is_active`

说明：

- 一个用户可兼任多个门店、部门、岗位
- 主管跨部门或跨柜组场景也可表达

### 4.3 功能权限

- `roles`
  - `id`
  - `role_code`
  - `role_name`
  - `role_level`
  - `is_system`
  - `is_active`

- `permissions`
  - `id`
  - `permission_code`
  - `permission_name`
  - `module_code`
  - `action_code`

- `role_permissions`
  - `id`
  - `role_id`
  - `permission_id`

- `user_roles`
  - `id`
  - `user_id`
  - `role_id`
  - `store_id`
  - `expires_at`

说明：

- `user_roles.store_id` 可为空，表示全局角色
- 也可指定到门店级角色

### 4.4 数据权限

- `data_policies`
  - `id`
  - `subject_type`
  - `subject_id`
  - `resource_code`
  - `action_code`
  - `scope_mode`
  - `effect`
  - `priority`
  - `is_active`

- `data_policy_items`
  - `id`
  - `policy_id`
  - `dimension_type`
  - `dimension_value`
  - `include_children`

说明：

- `subject_type`：`ROLE`、`USER`
- `resource_code`：`counter`、`hall`、`tenant`、`contract`、`bill`、`revenue`
- `action_code`：`view`、`edit`、`approve`、`export`
- `scope_mode`：`ALL`、`SELF`、`CUSTOM`
- `effect`：`ALLOW`、`DENY`
- `dimension_type`：`store`、`department`、`group`、`floor`、`unit`

## 5. 现有业务表的建议补强

### 5.1 `counter_groups`

建议：

- 保留 `department_code`、`department_name` 作为 ERP 同步冗余字段
- 新增 `department_id`
- 对 `store_id + group_code` 建唯一约束

### 5.2 `counters`

建议确保具备：

- `store_id`
- `floor_id`
- `group_code`
- `department_id` 或通过 `group_code` 可回溯到 `department_id`

### 5.3 `business_units`

建议补充：

- `store_id`
- `department_id`
- `group_code`

这样 `business_units` 就能作为“图纸层”和“权限层”的衔接点。

### 5.4 `contracts / bills / revenue_data`

建议查询时都能回溯出：

- `store_id`
- `department_id`
- `group_code`

如果历史数据结构不方便立刻加字段，可以先通过关联查询推导。

## 6. 授权判定规则

建议固定规则如下：

1. 先判功能权限
2. 再判数据权限
3. 同一条策略内多个维度取交集
4. 多条策略之间取并集
5. `DENY` 优先级高于 `ALLOW`

示例：

- 策略 A：`contract.view`，`store=601`，`department=女装部`
- 策略 B：`contract.view`，`group=G001,G002`

如果 A 和 B 是两条独立策略，最终可见范围是两者并集。

如果一条策略中同时写了：

- `store=601`
- `department=女装部`
- `group=G001`

则该策略表达的是三者交集。

## 7. 推荐角色模板

- `super_admin`
  - 全功能、全数据

- `system_admin`
  - 管理用户、角色、权限、字典、基础配置
  - 不默认拥有全部业务数据

- `store_admin`
  - 指定门店范围内的全业务数据

- `dept_manager`
  - 指定门店 + 指定部门

- `group_manager`
  - 指定门店 + 指定柜组

- `finance`
  - 财务相关功能
  - 数据范围按门店或部门配置

- `viewer`
  - 只读

## 8. 推荐权限码模板

### 8.1 空间与经营单元

- `store.view`
- `floor.view`
- `counter.view`
- `counter.create`
- `counter.edit`
- `counter.delete`
- `hall.view`
- `hall.edit`
- `hall.bind_group`
- `business_unit.view`
- `business_unit.create`
- `business_unit.edit`
- `business_unit.delete`

### 8.2 商户与合同

- `tenant.view`
- `tenant.create`
- `tenant.edit`
- `tenant.delete`
- `contract.view`
- `contract.create`
- `contract.edit`
- `contract.delete`
- `contract.approve`

### 8.3 财务与收益

- `bill.view`
- `bill.create`
- `bill.edit`
- `bill.approve`
- `revenue.view`
- `revenue.export`

### 8.4 系统管理

- `system.user.manage`
- `system.role.manage`
- `system.permission.manage`
- `system.data_policy.manage`
- `system.audit_log.view`

## 9. 数据范围模板

### 9.1 `super_admin`

- `scope_mode = ALL`

### 9.2 `store_admin`

- `dimension_type = store`
- `dimension_value = 指定门店`

### 9.3 `dept_manager`

- `dimension_type = store`
- `dimension_value = 指定门店`
- `dimension_type = department`
- `dimension_value = 指定部门`

### 9.4 `group_manager`

- `dimension_type = store`
- `dimension_value = 指定门店`
- `dimension_type = group`
- `dimension_value = 指定柜组`

### 9.5 `finance`

按实际分配：

- 门店级
- 部门级
- 柜组级

### 9.6 `viewer`

- 与其业务归属保持一致
- 只开放 `view`

## 10. 企业微信接入原则

### 10.1 建议接入范围

- 登录认证
- 通讯录同步

### 10.2 不建议让企业微信直接决定的内容

- 系统角色
- 数据范围
- 审批权限

### 10.3 同步建议

同步字段建议包括：

- 员工姓名
- 手机号
- 邮箱
- 企业微信用户 ID
- 部门归属
- 启停状态

同步策略建议：

- 只同步基础身份信息
- 不自动覆盖系统角色
- 可按规则自动绑定默认部门

## 11. 后端落地建议

登录后建议生成统一的 `auth_context`：

- `user_id`
- `role_codes`
- `permission_codes`
- `allowed_store_ids`
- `allowed_department_ids`
- `allowed_group_codes`
- `allowed_unit_ids`

接口处理顺序：

1. 校验是否登录
2. 校验是否具备功能权限
3. 自动拼装数据范围过滤条件
4. 查询业务数据

注意：

- 前端门店筛选只是 UI 体验，不是安全边界
- 数据范围必须在后端统一收口

## 12. 推荐实施顺序

1. 把现有 `users.role` 升级为 `user_roles + roles + permissions`
2. 新增 `user_identities`
3. 新增 `departments / posts / user_department_posts`
4. 升级 `counter_groups` 为权限核心对象
5. 在 `business_units` 上补足组织归属字段
6. 在后端实现统一 `auth_context`
7. 统一改造查询层，接入数据范围过滤
8. 最后再补前端菜单显隐和权限配置页

## 13. 第一阶段最小可落地版本

建议第一阶段只先做：

- 账号密码登录
- 企业微信登录
- 多角色
- 门店、部门、柜组三级数据范围
- 菜单权限
- 按钮权限
- 后端接口权限
- 登录日志
- 操作日志

先把这层打稳，再继续做更细的岗位、审批流和特殊授权。
