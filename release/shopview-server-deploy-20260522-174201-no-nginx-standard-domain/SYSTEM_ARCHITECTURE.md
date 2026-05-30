# 百货柜位系统架构梳理

> 本文基于当前代码反推整理，主要用于后续接入 ERP、扩展模块和维护待办。若代码与实际业务口径不一致，以业务口径为准，并在本文补充修订。

## 0. 当前进度快照（2026-05-09）

### 已完成 / 已进入代码实现

- [x] 合同台账与合同详情已扩展为第一版业务入口：合同列表、详情、费用条款、关联柜组/经营单元和权限过滤逻辑已落到前后端。
- [x] 统一业务数据范围已进入实现：新增 `business_scope.view` 资源口径，合同、销售可复用 `load_business_scope()` 与 `scope_allows_business()`。
- [x] ERP 权限同步预留已落地：`data_policies` 增加来源字段，提供 `import_erp_contract_scope.py` 从 ERP 用户/范围 Excel 导入用户与业务范围。
- [x] 销售查询第一版已落地：新增 `/api/sales`，支持门店、部门、柜组汇总，小票列表，小票详情，付款方式统计和同期对比。
- [x] POS/销售基础表迁移已补充：新增 `salegoodslist`、`salehead`、`salegoods`、`salepay` 等建表迁移和销售导出工具。
- [x] 旧收益地图/厅房收益路由已清理：删除旧 `revenue_dashboard/revenue_data/halls` 路由与旧页面，主线转向销售看板和新经营单元体系。
- [x] 空间业务楼层外键统一到 `floors.id` 的迁移和接口适配已完成。
- [x] 最新业务主线已确认：销售核心只认 `salegoodslist`；结算金额由 ERP 生成，柜位系统只取数展示；收益分析以铺位为最小单位。

### 当前重点待办

- [ ] 跑通数据库迁移并用真实数据验收合同、权限和销售接口。
- [ ] 确认 `salegoodslist` 与 ERP/POS 生产表的同步方式、增量字段和数据时效；`salehead/salegoods/salepay` 用于小票明细和付款明细补充。
- [ ] 补齐销售模块的退货/冲销/跨月调整口径验证。
- [ ] 接入 ERP 已生成结算单，建立本地结算单查询、关联和收费状态展示。
- [ ] 设计铺位级收益汇总，并把收益地图迁到 `business_units/geo_elements` + 铺位收益汇总表。
- [ ] 补充“其他收益/财务直接收款”登记与凭证草稿能力，用于罚款、供应商直接打款、赔偿等非系统内收益。
- [ ] 今日新增：做登录日志查询，支持按用户、登录结果、身份类型、时间范围筛选。
- [ ] 梳理旧 `contracts/bills/tenants/brands` 与 ERP 副本表的保留或废弃策略。

## 1. 系统定位

百货柜位系统当前承担三类职责：

1. 柜位空间资源管理：门店、楼层、底图、柜位图版本、经营单元、几何元素、厅房、柜组绑定。
2. 业务台账与流程管理：合同台账、供应商、柜位定义、装修流程、用户权限。
3. 经营分析展示：收益仪表盘、柜位收益图、销售/费用/订单明细。

后续接入 ERP 时，建议明确每类数据的主数据源：

| 数据类型 | 建议主系统 | 柜位系统职责 |
| --- | --- | --- |
| 柜位空间图纸、经营单元、底图版本 | 柜位系统 | 主维护、提供空间编码给 ERP 关联 |
| ERP 柜位定义、供应商、合同、销售流水 | ERP | 同步/查询副本，用于展示和关联 |
| 装修流程、附件、节点流转 | 柜位系统 | 主维护，必要时引用 ERP 合同状态 |
| 用户、角色、数据权限 | 柜位系统 | 主维护，后续可对接 OA/企业微信 |

## 2. 技术结构

| 层级 | 当前实现 |
| --- | --- |
| 前端 | React + Vite + TypeScript + Wouter + React Query |
| 后端 | Python + FastAPI |
| 数据库 | SQLAlchemy + Alembic，当前模型以 PostgreSQL 语法为主 |
| 静态资源 | `/static` 前端资源，`/uploads` 上传文件 |
| 认证 | Cookie 登录，`/api/auth/login`、`/api/auth/me`、`/api/auth/logout` |

主要入口：

| 类型 | 文件 |
| --- | --- |
| 前端路由入口 | `client/src/App.tsx` |
| 前端主框架 | `client/src/pages/main-dashboard.tsx` |
| 左侧导航 | `client/src/components/navigation-sidebar.tsx` |
| 后端入口 | `python_app/main.py` |
| 数据库连接 | `python_app/models/database.py` |

## 3. 总体数据流

```text
用户浏览器
  |
  v
React 前端
  |
  | HTTP /api/*
  v
FastAPI 后端
  |
  | SQLAlchemy / SQL
  v
柜位系统数据库
  ^
  |
  | ETL / 增量同步 / CDC / 手工导入
  |
ERP Oracle 11g
```

推荐原则：

1. 前端只访问柜位系统后端 API，不直接访问数据库。
2. 后端优先读柜位系统本地库。
3. ERP 数据先同步到本地 ODS/业务副本表，再供接口查询。
4. 强实时、强一致业务未来通过 ERP API 或事件同步处理，不建议长期直连 ERP 原始表。

## 4. 模块与表关系

### 4.1 登录与权限

| 前端页面/入口 | 后端 API | 核心表 | 说明 |
| --- | --- | --- | --- |
| `login.tsx` | `/api/auth/*` | `users`, `user_identities`, `login_logs` | 登录、当前用户、退出 |
| `system-config.tsx` | `/api/system/*` | `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `departments`, `posts`, `user_department_posts`, `data_policies`, `data_policy_items`, `operation_logs` | 用户、角色、部门、数据权限、合同权限 |
| 登录日志查询 | 待新增 `/api/system/login-logs` | `login_logs`, `users`, `user_identities` | 按时间、用户、账号、身份类型、成功/失败、IP 查询登录记录 |

待补充：

- [ ] 是否接企业微信/OA 单点登录。
- [ ] 是否由 ERP/OA 同步组织、人员、岗位。
- [ ] 合同/柜组/部门权限最终以哪个字段做数据范围控制。
- [ ] 登录日志查询前端入口放在系统配置、审计日志还是独立安全审计页。

### 4.2 门店与楼层基础

| 前端页面/入口 | 后端 API | 核心表 | 说明 |
| --- | --- | --- | --- |
| `stores.tsx` | `/api/stores` | `stores` | 门店维护 |
| `floors.tsx` | `/api/floors` | `floors` | 统一楼层体系，支持门店编码、楼层编码、排序 |
| 旧楼层来源 | 迁移保留 | `store_floors` | 仅作为历史迁移来源保留，不再作为空间业务表外键目标 |

注意：

- 当前空间业务外键已统一指向 `floors.id`。
- `store_floors` 仅保留历史数据和迁移映射，不再承载柜位、厅房、底图、柜位图版本、经营单元的当前楼层关系。

待补充：

- [x] 将空间业务表统一迁移到 `floors.id`。
- [ ] 决定是否清理或归档 `store_floors` 历史表。
- [ ] 明确门店编码 `store_code` 与 ERP market/门店字段的映射。

### 4.3 底图、柜位图版本与经营单元

| 前端页面/入口 | 后端 API | 核心表 | 说明 |
| --- | --- | --- | --- |
| `base-maps.tsx` | `/api/base-maps` | `base_maps`, `floors` | 楼层 SVG 底图上传、激活、删除 |
| `unit-map-versions.tsx` | `/api/unit-map-versions` | `unit_map_versions`, `base_maps`, `geo_elements`, `business_units`, `unit_map_alignments` | 柜位图版本、SVG 导入、图纸对齐 |
| `business-units.tsx` | `/api/business-units` | `business_units`, `floors` | 经营单元维护，柜位业务编号不随图纸变化 |
| `geo_elements` hook/page | `/api/geo-elements` | `geo_elements`, `unit_map_versions`, `business_units` | 柜位 SVG path、中心点、包围盒、面积 |
| `floor-area-report.tsx` | `/api/reports/floor-area-summary` | `floors`, `business_units`, `geo_elements` | 楼层面积统计 |

核心关系：

```text
floors
  -> base_maps
  -> unit_map_versions
  -> geo_elements
  -> business_units
```

关键表：

| 表 | 用途 |
| --- | --- |
| `floors` | 楼层字典 |
| `base_maps` | 静态底图文件与 SVG 元数据 |
| `unit_map_versions` | 柜位图版本 |
| `business_units` | 经营单元主表，业务柜位编号 |
| `geo_elements` | 经营单元在某个图纸版本下的几何形状 |
| `spatial_evolution_log` | 拆分、合并、重构历史 |
| `site_snapshots` | 全场版本快照 |
| `unit_map_alignments` | 图纸对齐参数，当前由接口内建表 |

待补充：

- [ ] ERP 合同表中的柜位编码字段是否统一对应 `business_units.unit_code`。
- [ ] 拆分/合并时 ERP 合同如何迁移或重新挂接。
- [ ] 是否需要将 `business_units` 反向同步给 ERP 作为柜位主数据。

### 4.4 旧柜位、厅房与几何

| 前端页面/入口 | 后端 API | 核心表 | 说明 |
| --- | --- | --- | --- |
| `counters.tsx` | `/api/counters` | `counters`, `stores`, `store_floors`, `counter_geometries`, `counter_geometry_properties` | 旧柜位维护、位置更新 |
| `counter-groups-map.tsx` | `/api/halls`, `/api/counters`, `/api/revenue-dashboard` | `halls`, `counter_groups`, `hall_group_bindings`, `counters` | 柜组/厅房地图 |
| 主框架内 `HallsPage` | `/api/halls` | `halls`, `counter_groups`, `hall_group_bindings` | 厅房维护与柜组绑定 |
| 几何接口 | `/api/geometry`, `/api/polygon-counters` | `counter_geometries`, `counter_geometry_properties`, `counters` | 矩形、多边形、圆形几何 |

关键表：

| 表 | 用途 |
| --- | --- |
| `counters` | 旧柜位主表，含坐标、面积、租金、状态、柜组编码 |
| `halls` | 工程绘制的厅房/空间 |
| `counter_groups` | 柜组数据，标注为 ERP 数据 |
| `hall_group_bindings` | 厅房与柜组绑定 |
| `counter_geometries` | 旧柜位几何主表 |
| `counter_geometry_properties` | 旧柜位几何属性 |

待补充：

- [x] 柜位、厅房楼层外键已迁入 `floors.id`。
- [ ] 新体系 `business_units/geo_elements` 与旧体系 `counters/counter_geometries` 的后续业务合并策略。
- [ ] 厅房是否作为真实业务空间继续保留，还是转为 `business_units` 的一种类型。
- [ ] 柜组 `counter_groups` 的 ERP 来源表和同步频率。

### 4.5 柜位定义、供应商、合同

| 前端页面/入口 | 后端 API | 核心表 | ERP 原始表/脚本 | 说明 |
| --- | --- | --- | --- | --- |
| `manaframe.tsx` | `/api/manaframe` | `manaframe` | `建表/MANAFRAME.txt` | ERP 柜位定义/柜组定义查询 |
| `suppliers.tsx` | `/api/suppliers` | `supplierbase` | `建表/SUPPLIERBASE.txt` | ERP 供应商主数据 |
| `contracts.tsx` | `/api/contracts/by-unit/{unit_id}`, `/api/contracts/detail/{contract_no}` | `contmain`, `contbd`, `contmanaframe`, `contcyclist`, `contsupcharge`, `supplierbase`, `manaframe`, `counter_groups`, `business_units` | `建表/CONTMAIN.txt`, `CONTBD.txt`, `CONTMANAFRAME.txt`, `CONTCYCLIST.txt`, `CONTSUPCHARGE.txt` | ERP 合同台账与经营单元关联 |

当前合同关联口径：

```text
business_units.unit_code
  -> contmanaframe.cmfmfid
  -> contmain.cmcontno = contmanaframe.cmfcontno

兼容：
business_units.unit_code
  -> contmain.cmchar9
```

最新空间/经营/合同建模原则：

```text
铺位 business_units：物理空间最小展示单元，图纸和收益分析都落到这里。
柜组 counter_groups / manaframe：经营单元，可对应普通商铺柜组，也可对应超市内部食品、日化等柜组。
合同 contmain：权责和结算单元，一份合同可挂一个或多个柜组/供应商。
经营绑定 business_unit_bindings：表达某一时间段内铺位、柜组、供应商、品牌、合同的关系。
```

建议新增关系表 `business_unit_bindings`，不要把 `contract_id` 或 `group_code` 直接绑死在铺位表上：

| 字段 | 说明 |
| --- | --- |
| `id` | 系统主键 |
| `business_unit_id` | 铺位/经营单元 ID，对应图纸最小展示单元 |
| `group_code` | 柜组编码，可为空 |
| `supplier_id` | 供应商编码，可为空 |
| `brand_id` | 品牌编码，可为空 |
| `contract_no` | ERP 合同号 |
| `business_type` | 普通商铺、超市联营、租赁、临时经营等 |
| `start_date`, `end_date` | 关系生效周期 |
| `is_primary` | 是否主关系 |
| `status` | 启用、停用、历史 |

普通铺位可表现为“一个铺位 + 一个柜组 + 一个合同”，但系统底层仍按一对多关系处理。超市场景则表现为“一个超市大铺位 + 多个柜组 + 多个供应商 + 多份合同”，收益最终汇总回同一个超市铺位。

合同状态标签：

| ERP 状态 | 显示 |
| --- | --- |
| `B` | 未生效 |
| `Y` | 已生效 |
| `S` | 停用 |
| `N` | 终止 |
| `A` | 已审批 |
| `Q` | 过期 |

待补充：

- [ ] 确认 ERP 11g 同步到本地 PostgreSQL 的方式：定时 ETL、CDC、GoldenGate、Debezium、触发器变更表。
- [x] 合同状态是否需要准实时；当前按后台每 1 小时同步一次。
- [x] `contmain.cmchar9` 与 `contmanaframe.cmfmfid` 哪个是主关联字段；当前以 `contmanaframe.cmfmfid` 为主，兼容 `contmain.cmchar9`。
- [ ] 供应商编码 `cmsupid -> supplierbase.sbid` 是否唯一稳定。

### 4.6 装修管理

| 前端页面/入口 | 后端 API | 核心表 | 说明 |
| --- | --- | --- | --- |
| `decorations.tsx` | `/api/decorations` | `decoration_projects`, `decoration_project_spaces`, `decoration_attachments` | 装修项目、空间、附件 |
| 装修待办 | `/api/decorations/todos` | `workflow_instances`, `workflow_instance_nodes`, `decoration_projects` | 当前用户待处理事项 |
| 装修流程动作 | `/api/decorations/{id}/submit` 等 | `workflow_templates`, `workflow_template_nodes`, `workflow_instances`, `workflow_instance_nodes`, `workflow_actions` | 提交、审批、确认、驳回、退款流程 |
| 专项记录 | 多个流程节点 API | `decoration_property_reviews`, `decoration_deposit_confirms`, `decoration_entry_confirms`, `decoration_acceptances`, `decoration_settlements`, `decoration_refunds` | 审图、保证金、进场、验收、结算、退款 |

装修项目引用关系：

```text
decoration_projects
  -> stores
  -> departments
  -> users
  -> contracts(contract_no 文本关联 ERP 合同号)
  -> decoration_project_spaces
       -> halls 或 business_units
```

待补充：

- [ ] 装修申请前是否必须校验 ERP 合同有效。
- [ ] 保证金缴纳是否要接 ERP/财务实时状态。
- [ ] 装修完成后是否自动更新 `business_units.status`。
- [ ] 附件是否需要接对象存储/文件服务器。

### 4.7 收益与经营分析

| 前端页面/入口 | 后端 API | 核心表 | 说明 |
| --- | --- | --- | --- |
| `dashboard.tsx`, `main-dashboard.tsx` | `/api/dashboard/stats`, `/api/dashboard/stores-stats` | `stores`, `counters`, `tenants`, `contracts`, `bills` | 总览统计 |
| `sales-dashboard.tsx` | `/api/sales/*` | `salegoodslist`, `salehead`, `salegoods`, `salepay`, `counter_groups` | 销售汇总核心只认 `salegoodslist`，小票和付款明细由 `salehead/salegoods/salepay` 补充 |
| ERP 结算单 | 待完善 `/api/erp-settlements/*` | ERP 结算单副本表 | ERP 直接生成结算金额，柜位系统取数、关联铺位、展示和参与收益分析 |
| 其他收益登记 | 待新增 | `other_revenue_entries`, `voucher_drafts` | 财务直接收款、罚款、赔偿、供应商直接打款等非系统内收益，后续生成凭证草稿 |
| 旧收益地图 | 已移除旧入口 | `revenue_data`, `sales_profits`, `fees`, `orders`, `order_items` | 旧柜位收益体系已清理，后续按新经营单元重建 |
| ODS 销售清单 | 兼容回退 | `ods_salegoodslist` | 旧销售清单副本，当前优先使用 `salegoodslist` |

关键表：

| 表 | 用途 |
| --- | --- |
| `unit_monthly_revenue_summary` | 建议新增，铺位级月度收益汇总，作为图纸染色和收益分析主表 |
| `salegoodslist` | 销售事实主表，销售额、成本、毛利优先由此汇总 |
| ERP 结算单副本表 | ERP 已生成结算金额，柜位系统只做查询、关联、展示 |
| `other_revenue_entries` | 建议新增，财务直接收款、罚款、赔偿等其他收益登记 |
| `voucher_drafts` | 建议新增，其他收益确认后生成凭证草稿 |
| `revenue_data` | 旧柜位聚合收益，后续迁移或废弃 |
| `sales_profits` | 旧销售毛利 |
| `fees` | 旧费用/收费 |
| `orders` | 订单 |
| `order_items` | 订单明细 |
| `ods_salegoodslist` | ERP/POS 商品销售 ODS 明细 |

收益分析当前确认三类来源：

```text
铺位收益 = 销售毛利 + 联营/租赁收费 + 其他收益
```

其中：

- 销售毛利来自 `salegoodslist`。
- 联营/租赁收费来自 ERP 已生成结算单、合同收费、租金、扣点、保底、物业费等。
- 其他收益来自财务直接收款登记，例如供应商直接打款、罚款、赔偿、赞助、临时收费等。

待补充：

- [x] 旧收益地图后续是否迁到新图纸体系 `business_units/geo_elements`。
- [x] ODS 销售清单与柜位/柜组的关联字段。
- [ ] 分析数据是实时算、定时汇总，还是两者混合。
- [ ] 新铺位收益汇总表的月度口径、费用归属、分摊和重算机制。
- [ ] 一笔其他收益对应多个铺位时的分摊规则：固定金额、按面积、按销售额或手工分摊。

### 4.8 商户、品牌、账单旧模型

| 前端页面/入口 | 后端 API | 核心表 | 说明 |
| --- | --- | --- | --- |
| `tenants.tsx` | `/api/tenants` | `tenants` | 本地商户档案 |
| 品牌页面/旧组件 | 暂未见独立后端路由 | `brands` | 本地品牌档案 |
| 旧合同模型 | 部分 dashboard 使用 | `contracts` | 本地合同表，与 ERP `contmain` 不同 |
| 旧账单模型 | 暂未见完整页面 | `bills` | 本地账单表 |

注意：

- 当前有本地 `contracts` 表，也有 ERP 同步表 `contmain/contbd/contmanaframe`。
- 当前合同页面主要使用 ERP 合同查询接口。

待补充：

- [ ] 决定是否废弃本地 `contracts/bills`，或作为非 ERP 合同/模拟数据保留。
- [ ] `tenants/brands` 是否由 `supplierbase/contmain` 派生生成。

## 5. 表分组清单

### 5.1 空间与图纸

| 表 | 类型 | 备注 |
| --- | --- | --- |
| `stores` | 本地基础表 | 门店 |
| `floors` | 本地基础表 | 新楼层字典 |
| `store_floors` | 旧本地基础表 | 旧楼层与平面图 |
| `base_maps` | 本地业务表 | SVG 底图 |
| `unit_map_versions` | 本地业务表 | 柜位图版本 |
| `business_units` | 本地业务表 | 经营单元 |
| `geo_elements` | 本地业务表 | 新图纸几何 |
| `spatial_evolution_log` | 本地日志表 | 拆分/合并 |
| `site_snapshots` | 本地快照表 | 全场版本快照 |
| `counters` | 旧本地业务表 | 旧柜位 |
| `counter_geometries` | 旧本地业务表 | 旧几何 |
| `counter_geometry_properties` | 旧本地业务表 | 旧几何属性 |
| `halls` | 本地业务表 | 厅房 |
| `hall_group_bindings` | 本地业务表 | 厅房-柜组绑定 |

### 5.2 ERP 副本/ODS

| 表 | 来源 | 备注 |
| --- | --- | --- |
| `manaframe` | ERP | 柜位/柜组定义 |
| `supplierbase` | ERP | 供应商 |
| `contmain` | ERP | 合同主表 |
| `contbd` | ERP | 合同保底表 |
| `contmanaframe` | ERP | 合同所属柜组表，可与柜组关联 |
| `contcyclist` | ERP | 租赁周期性费用表 |
| `contsupcharge` | ERP | 供应商合同费用表 |
| `salegoodslist` | ERP/POS | 销售单品日汇总，当前销售汇总主表 |
| `salehead` | ERP/POS | 小票主单 |
| `salegoods` | ERP/POS | 小票商品明细 |
| `salepay` | ERP/POS | 小票付款明细 |
| `ods_salegoodslist` | ERP/POS | 旧销售商品清单兼容副本 |
| `counter_groups` | ERP/本地同步 | 柜组/部门/品类/经营方式 |

### 5.3 业务流程

| 表 | 类型 | 备注 |
| --- | --- | --- |
| `decoration_projects` | 本地业务表 | 装修项目主表 |
| `decoration_project_spaces` | 本地业务表 | 装修涉及空间 |
| `decoration_attachments` | 本地业务表 | 装修附件 |
| `workflow_templates` | 本地配置表 | 流程模板 |
| `workflow_template_nodes` | 本地配置表 | 流程模板节点 |
| `workflow_instances` | 本地流程表 | 流程实例 |
| `workflow_instance_nodes` | 本地流程表 | 流程实例节点 |
| `workflow_actions` | 本地日志表 | 流程动作 |
| `decoration_property_reviews` | 本地业务表 | 物业审图 |
| `decoration_deposit_confirms` | 本地业务表 | 保证金确认 |
| `decoration_entry_confirms` | 本地业务表 | 进场确认 |
| `decoration_acceptances` | 本地业务表 | 验收 |
| `decoration_settlements` | 本地业务表 | 结算 |
| `decoration_refunds` | 本地业务表 | 退款 |

### 5.4 权限与日志

| 表 | 类型 | 备注 |
| --- | --- | --- |
| `users` | 本地权限表 | 用户 |
| `user_identities` | 本地权限表 | 登录身份 |
| `departments` | 本地权限表 | 部门 |
| `posts` | 本地权限表 | 岗位 |
| `user_department_posts` | 本地权限表 | 用户组织岗位 |
| `roles` | 本地权限表 | 角色 |
| `permissions` | 本地权限表 | 权限点 |
| `role_permissions` | 本地权限表 | 角色权限 |
| `user_roles` | 本地权限表 | 用户角色 |
| `data_policies` | 本地权限表 | 数据权限策略 |
| `data_policy_items` | 本地权限表 | 数据权限维度 |
| `login_logs` | 本地日志表 | 登录日志 |
| `operation_logs` | 本地日志表 | 操作日志 |
| `system_logs` | 本地日志表 | 旧系统日志 |

## 6. ERP 接入建议

### 6.1 分层同步策略

| 数据 | 实时性 | 建议方式 |
| --- | --- | --- |
| 供应商、柜位定义、柜组 | 低到中 | 定时增量 ETL |
| 合同主数据、合同-柜位关联 | 中到高 | 增量 ETL 或 CDC，按状态变化频率决定 |
| 销售流水/商品清单 | 中 | 批量增量同步到 ODS，再做汇总 |
| 保证金/缴费/审批状态 | 高 | 优先 ERP API 或 CDC/事件表 |

### 6.2 Oracle 11.2.0.4 可选方案

| 方案 | 适合场景 | 备注 |
| --- | --- | --- |
| 定时增量 ETL | 大多数主数据、合同、销售汇总 | 实施简单，先落地 |
| 触发器 + 变更表 | 少量关键表，ERP 允许改库 | 对 ERP 有侵入 |
| LogMiner/Debezium | 准实时 CDC | 需要 DBA 配合归档日志、补充日志、权限 |
| GoldenGate | 生产级实时同步 | 成本高，但最稳 |
| ERP API | 强一致动作 | 最适合付款、审批、状态校验 |

## 7. 后续待办总表

### 架构待办

- [ ] 统一新旧空间模型边界：`business_units/geo_elements` 与 `counters/counter_geometries`。
- [x] 统一楼层模型边界：空间业务统一使用 `floors.id`。
- [ ] 新增或落地 `business_unit_bindings` 关系表，统一表达铺位、柜组、供应商、品牌、合同的时间段绑定。
- [ ] 明确本地 `contracts/bills` 与 ERP `cont*` 表是否并存。
- [ ] 整理 API 权限矩阵：模块、接口、权限码、数据范围。

### ERP 接入待办

- [x] 列出第一批同步表：`manaframe`, `supplierbase`, `contmain`, `contmanaframe`, `contbd`, `salegoodslist`, `salehead`, `salegoods`, `salepay`。
- [ ] 为每张 ERP 表补充主键、增量字段、更新时间字段、删除标识。
- [ ] 确认 Oracle 11g 是否开启归档日志、补充日志，是否允许 CDC。
- [ ] 定义同步延迟 SLA：合同状态已按 1 小时同步确认，供应商、销售流水、缴费状态仍待补充。
- [ ] 设计同步任务监控表：任务名、开始时间、结束时间、同步条数、失败原因。

### 业务待办

- [ ] 装修项目与 ERP 合同状态联动规则。
- [ ] 柜位拆分/合并后合同与销售归属规则。
- [ ] 收益地图从旧柜位迁移到铺位级 `business_units/geo_elements` 的方案。
- [ ] 供应商、商户、品牌三者的业务口径确认。
- [ ] 其他收益登记、财务确认和凭证草稿生成规则。

### 近期执行待办

| 优先级 | 任务 | 说明 |
| --- | --- | --- |
| P0 | [ ] 登录日志查询 | 今天新增，基于 `login_logs` 做列表、筛选和详情，入口建议放系统配置/安全审计 |
| P0 | [ ] 结算单继续完善 | ERP 结算金额直接取数，不在柜位系统重复计算 |
| P0 | [ ] `salegoodslist` 口径验收 | 销售核心只认 `salegoodslist`，校验退货、冲销、跨月调整 |
| P1 | [ ] 铺位-柜组-合同绑定模型 | 支持普通铺位一对一和超市大铺位多柜组多供应商多合同 |
| P1 | [ ] 铺位收益分析 | 以铺位为最小单位汇总销售毛利、联营/租赁收费、其他收益 |
| P1 | [ ] 图纸收益展示 | 在铺位图上按销售额、毛利、租金/收费、净收益等指标染色 |
| P2 | [ ] 企业微信导购小票核对 | 导购填数、拍照上传，后台 OCR/人工复核并匹配差异 |

## 8. 业务部门经营闭环实施代办

当前主线从“柜组经营闭环”调整为“铺位最小经营单元”。系统核心定位：

```text
以铺位为最小经营单元，汇总销售、ERP 结算和财务其他收益，形成收益分析和图纸化经营看板。
```

建议主线：

```text
铺位/柜组/合同绑定 -> salegoodslist 销售 -> ERP 结算单取数 -> 铺位收益汇总 -> 图纸收益看板 -> 手机端查询与小票核对
```

### 8.1 P0 合同管理

目标：让业务部门先能围绕柜组/经营单元查看合同、商户、品牌、经营方式和合同状态。

| 任务 | 说明 | 相关表/数据 |
| --- | --- | --- |
| [x] 合同台账列表 | 合同号、供应商/商户、品牌、柜组、柜位/经营单元、经营方式、状态、起止日期 | `contmain`, `contmanaframe`, `supplierbase`, `manaframe`, `counter_groups`, `business_units` |
| [x] 合同详情页 | 合同基础信息、关联柜位/柜组、费用条款、扣率/租金/保底、补充收费 | `contmain`, `contbd`, `contcyclist`, `contsupcharge` |
| [x] 合同状态同步 | 未生效、已生效、停用、终止、过期等状态统一展示 | `contmain.cmstatus` |
| [x] 合同与空间关联 | 明确 `business_units.unit_code`、`contmanaframe.cmfmfid`、`contmain.cmchar9` 的主关联规则 | `business_units`, `contmanaframe`, `contmain` |
| [x] 合同搜索筛选 | 按门店、楼层、部门、柜组、品牌、供应商、状态、到期时间筛选 | 合同副本表 + 权限范围 |
| [ ] 合同到期提醒 | 近 30/60/90 天到期合同提醒 | `contmain.cmlapdate` 或实际到期字段 |

### 8.2 P0 每日实时销售与小票明细

目标：业务人员能查每天实时销售、查看小票明细、统计付款方式，并看到单笔/商品级毛利。销售汇总核心只认 `salegoodslist`，其他销售报表只作为对照和校验，不作为主事实来源。

| 任务 | 说明 | 相关表/数据 |
| --- | --- | --- |
| [x] 确认销售数据源 | 销售事实核心只认 `salegoodslist`；`salehead/salegoods/salepay` 用于小票与付款明细 | ERP/POS 表 |
| [ ] 销售流水同步 | 建立 `salegoodslist` 按日期/更新时间/流水号的增量同步 | `salegoodslist` |
| [x] 小票列表 | 日期、门店、柜组、品牌、小票号、流水号、销售金额、数量、收银台、营业员 | 小票主表/销售明细 |
| [x] 小票详情 | 商品、条码、数量、售价、折扣、实收、成本、毛利、毛利率 | 商品明细 + 成本字段 |
| [x] 付款方式统计 | 现金、银行卡、储值卡、券、第三方支付、其他支付等 | 付款明细或销售表支付金额字段 |
| [ ] 退货/冲销处理 | 明确当天退货、跨月退货、原单冲销如何影响销售和毛利 | 销售/退货标识 |
| [x] 今日销售看板 | 今日销售、昨日对比、月累计、柜组排行、异常小票 | 销售汇总表/实时查询 |

### 8.3 P1 月度结算单与收费情况

目标：ERP 已生成结算金额，柜位系统不重复计算结算结果，只负责取数、关联铺位/柜组/合同、展示明细和参与收益分析。

| 任务 | 说明 | 相关表/数据 |
| --- | --- | --- |
| [ ] ERP 结算单同步/查询 | 获取 ERP 已生成的结算单主表和明细，不在本系统重算结算金额 | ERP 结算单表 |
| [ ] 结算单与铺位关联 | 通过合同、柜组、供应商映射到 `business_unit_bindings`，最终落到铺位 | `contmain`, `contmanaframe`, `business_unit_bindings` |
| [ ] 结算单列表 | 月份、铺位、柜组、合同、供应商、应收/应付、已收、未收、状态 | ERP 结算单副本表 |
| [ ] 结算单详情 | ERP 结算项目、合同条款、销售汇总、费用明细、调整项、最终金额 | ERP 结算明细 |
| [ ] 收费状态 | 应收、已收、部分收、未收、逾期 | ERP 财务/收费数据 |
| [ ] 权限接入 | 结算单按 `business_scope.view` 控制门店、部门、柜组、供应商范围 | 权限表 |

### 8.4 P1 铺位收益与收益地图

目标：按月生成每个铺位收益，并在图纸上用颜色和明细呈现。铺位是收益分析最小单位，柜组、供应商、合同是可展开维度。

建议收益口径先按可落地版本定义：

```text
铺位月收益 = 销售毛利 + 联营/租赁收费 + 其他收益 - 可归属费用/扣减
```

| 任务 | 说明 | 相关表/数据 |
| --- | --- | --- |
| [ ] 收益汇总模型 | 门店、楼层、铺位、柜组、供应商、合同、月份、销售额、毛利、结算收费、其他收益、净收益 | 新增 `unit_monthly_revenue_summary` 类表 |
| [ ] 销售毛利归集 | `salegoodslist` 先按柜组/供应商/合同汇总，再通过绑定表落到铺位 | `salegoodslist`, `business_unit_bindings` |
| [ ] 联营/租赁收费归集 | ERP 结算单按合同/供应商/柜组关联铺位 | ERP 结算单副本表 |
| [ ] 其他收益归集 | 财务直接收款、罚款、赔偿等登记后直接选铺位或通过合同/供应商匹配铺位 | `other_revenue_entries` |
| [ ] 收益计算任务 | 每日/每月定时汇总，支持重算指定月份和指定铺位 | 销售、结算、其他收益 |
| [ ] 收益地图接入 | 图纸按净收益、毛利率、销售额、收费状态染色 | `geo_elements`, `business_units`, 收益汇总表 |
| [ ] 地图筛选 | 月份、门店、楼层、部门、铺位、柜组、品牌、供应商、经营方式 | 收益汇总 + 权限 |
| [ ] 地图弹窗详情 | 铺位、柜组、供应商、合同、销售、小票、结算单、其他收益、近 12 月趋势 | 多表聚合 |
| [ ] 异常标识 | 空置、无合同、有销售无合同、低毛利、费用逾期 | 规则引擎/查询 |

### 8.4.1 P1 其他收益与凭证草稿

目标：把当前不在业务系统中体现、但财务实际收到的钱纳入铺位收益，例如供应商直接打款、罚款、赔偿、临时收费，并后续生成凭证草稿。

| 任务 | 说明 | 相关表/数据 |
| --- | --- | --- |
| [ ] 其他收益登记 | 收益日期、类型、金额、付款方、商户/供应商、铺位、合同、附件、备注 | `other_revenue_entries` |
| [ ] 财务确认 | 待确认、财务已确认、已生成凭证、已作废 | `other_revenue_entries.status` |
| [ ] 多铺位分摊 | 支持固定金额、按面积、按销售额、手工分摊 | `other_revenue_allocations` |
| [ ] 凭证模板 | 按收益类型配置借方/贷方科目、辅助核算、摘要规则 | `voucher_templates` |
| [ ] 凭证草稿 | 财务确认后自动生成凭证草稿，后续推 ERP 或导出 | `voucher_drafts` |

### 8.5 P0 权限体系

目标：从第一期就按业务实际管辖范围控制数据，不等功能完成后再补。

| 任务 | 说明 | 相关表/数据 |
| --- | --- | --- |
| [ ] 用户来源 | 本地维护、OA 同步、企业微信同步三选一或混合 | `users`, `user_identities` |
| [ ] 组织岗位 | 门店、部门、岗位、用户归属 | `departments`, `posts`, `user_department_posts` |
| [ ] 业务管辖范围 | 业务员负责柜组/品牌/供应商/楼层/品类中的哪一种 | `data_policies`, `data_policy_items`, `counter_groups` |
| [ ] 功能权限 | 合同查看、销售查看、小票查看、毛利查看、结算查看、费用调整、收益地图查看 | `permissions`, `roles`, `role_permissions` |
| [ ] 敏感字段权限 | 成本、毛利、净收益、付款明细是否分角色可见 | 后端字段级控制 |
| [ ] 权限矩阵文档 | 每个角色可看哪些模块、哪些数据、哪些字段、哪些操作 | 新增文档或系统配置页 |
| [ ] 登录日志查询 | 按用户、账号、IP、时间、成功/失败查询登录记录 | `login_logs` |

统一数据范围口径：

```text
功能权限：contract.view / sales.view / settlement.view / revenue.view
数据范围：business_scope.view
```

ERP 同步来的用户数据范围、系统手工维护的临时范围，都统一写入 `business_scope.view`。合同、销售、结算单、收益地图先检查各自功能权限，再加载统一业务范围过滤门店、部门、柜组、供应商、品牌、品类。

### 8.5.1 统一业务数据范围待办

| 优先级 | 任务 | 说明 |
| --- | --- | --- |
| P0 | [x] 数据策略来源字段 | `data_policies` 增加 `source_type/source_system/external_scope_id/external_scope_name/synced_at` |
| P0 | [x] 统一资源编码 | 新增权限资源约定 `business_scope.view`，作为合同、销售、结算、收益共用数据范围 |
| P0 | [x] 手工与 ERP 来源隔离 | 手工保存只覆盖 `MANUAL/shopview` 来源；ERP 同步只覆盖 `ERP/erp` 来源 |
| P0 | [x] 权限服务 | 新增 `load_business_scope()` 和通用 `scope_allows_business()` |
| P0 | [x] 合同模块切换 | 合同功能权限仍用 `contract.view`，数据过滤改用 `business_scope.view` |
| P0 | [x] 系统配置页改名 | “合同权限”调整为“业务数据范围”，并展示来源 |
| P0 | [x] ERP 权限同步预留 | 后续按 ERP 用户、范围 ID、范围柜组明细重建 `ERP/erp/business_scope.view` |
| P1 | [x] 销售模块接入 | 销售列表、小票详情、销售看板全部复用 `business_scope.view` |
| P1 | 结算模块接入 | 结算单列表和详情按统一范围过滤，供应商维度支持 `supplier` |
| P1 | 权限排查 | 增加“为什么能看该柜组”的排查视图或接口 |

建议初始角色：

| 角色 | 范围 |
| --- | --- |
| 业务员 | 查看自己负责柜组/供应商/品牌 |
| 业务主管 | 查看本部门 |
| 门店管理 | 查看本门店 |
| 财务 | 查看合同、结算、收费，可确认收费 |
| 管理员 | 全部数据和配置 |
| 只读查看 | 仅看授权范围内数据 |

### 8.6 P2 企业微信小程序/手机端

目标：手机端先解决高频查询和提醒，复杂图纸操作仍以 PC 为主。

| 任务 | 说明 |
| --- | --- |
| [ ] 企业微信登录 | 企业微信用户身份绑定系统用户 |
| [ ] 手机首页 | 今日销售、月累计、待确认结算、合同到期提醒 |
| [ ] 销售查询 | 按日期/柜组查销售和小票 |
| [ ] 合同查询 | 查看负责柜组合同状态和到期情况 |
| [ ] 结算查询 | 查看月结算单与收费状态 |
| [ ] 收益查看 | 第一版用列表/简化楼层图，后续再做完整 SVG 地图 |
| [ ] 每日小票核对 | 导购填写销售/支付数字，上传收银小票/POS 凭证，后台自动核对差异 |
| [ ] 移动端权限 | 与 PC 共用同一套角色和数据权限 |

### 8.7 建议实施顺序

1. 已完成：合同台账与合同详情，先把合同和柜组/经营单元关系打通。
2. 进行中：销售同步、小票列表、小票详情、付款方式统计，核心销售口径收敛到 `salegoodslist`，待真实同步和口径验收。
3. 已完成：权限矩阵与数据范围，先覆盖合同和销售。
4. 今天新增：登录日志查询。
5. 下一步：ERP 结算单取数、列表、详情和收费状态展示。
6. 下一步：铺位-柜组-合同绑定模型，支持普通商铺和超市场景。
7. 下一步：铺位月度收益汇总。
8. 下一步：收益地图接入铺位收益汇总。
9. 后续：企业微信小程序，先做查询、小票核对和提醒，再做审批/确认。

### 8.8 需要补充确认的问题

| 问题 | 影响 |
| --- | --- |
| [x] 合同主关联字段最终用 `contmanaframe.cmfmfid` 还是 `contmain.cmchar9`？ | 当前以 `contmanaframe.cmfmfid` 为主，兼容 `contmain.cmchar9` |
| [x] ERP 里是否已有小票主表、付款明细表？表名和主键是什么？ | 已按 `salehead/salegoods/salepay` 建模 |
| [x] 当前 `ods_salegoodslist` 是否能唯一还原一张小票？ | 当前优先使用 `salehead/salegoods/salepay`，`salegoodslist/ods_salegoodslist` 作为汇总和回退 |
| [x] 付款方式是多列金额，还是独立付款明细行？ | 已按 `salepay` 独立付款明细行处理 |
| [x] 商品成本/毛利字段在哪里？ERP 已算好还是柜位系统计算？ | 当前销售看板按销售明细毛利字段汇总展示 |
| [ ] 退货、冲销、跨月调整如何处理？ | 影响日销售和月结算准确性 |
| [x] ERP 是否已有月结算单？还是柜位系统自己生成？ | ERP 已直接生成结算金额，柜位系统只取数展示和参与收益分析 |
| [ ] ERP 结算单主表/明细表名、主键和状态字段是什么？ | 影响结算单查询接口和本地副本模型 |
| [ ] 收费状态来自 ERP 财务哪个字段或表？ | 影响实时性和权限 |
| [x] 业务员负责范围是柜组、供应商、品牌、楼层还是品类？ | 当前以 ERP 业务范围同步到 `business_scope.view`，支持门店/部门/柜组等维度 |
| [ ] 成本、毛利、净收益哪些角色可以看？ | 影响字段级权限 |
| [ ] 企业微信小程序第一版是只查询，还是需要确认/审批操作？ | 影响移动端范围 |
| [ ] 其他收益凭证是否推回 ERP，还是只生成导出文件？ | 影响凭证草稿接口和财务流程 |

### 8.9 已确认业务口径

| 事项 | 当前结论 |
| --- | --- |
| 合同主表 | `contmain` 是合同主表 |
| 合同所属柜组 | `contmanaframe` 是合同所属柜组表，可用于合同与柜组关联 |
| 保底信息 | `contbd` 是保底表 |
| 租赁周期费用 | `contcyclist` 是租赁周期性费用表 |
| 供应商合同费用 | `contsupcharge` 是供应商合同费用表 |
| 销售核心表 | 销售汇总和毛利核心只认 `salegoodslist` |
| 业务看销售口径 | 日常按柜组看销售，可通过绑定表汇总到铺位 |
| 结账口径 | ERP 已生成结算金额，柜位系统直接取结算结果 |
| 收益最小单位 | 铺位/`business_units` 是收益分析和图纸展示最小单位 |
| 超市场景 | 超市整体是一个铺位，内部可有多个柜组、多个供应商、多个合同，最终收益汇总回超市铺位 |
| 业务员负责范围 | ERP 权限表中已有业务员-柜组关系，后续同步到柜位系统维护对应表 |
| 合同同步频率 | 后台每 1 小时同步一次 |
| 后续合同创建 | 后续考虑在柜位系统创建合同，再推送到 OA 审批 |
| 成本/毛利与合同关系 | 成本和毛利不在合同表体现，应放在销售/收益模块 |
| 是否清算 | 从保底表 `contbd` 取，优先看 `cbisrunqs` |
| 结算位置 | `contmain.cmjsmkt` |
| 其他收益 | 供应商直接打款、罚款、赔偿等先通过其他收益登记纳入收益，后续生成凭证草稿 |

### 8.10 第一阶段建议开发范围

第一阶段不直接做完整销售和结算，先把合同与柜组权限基础打牢。

| 优先级 | 任务 | 目标 |
| --- | --- | --- |
| P0 | [x] ERP 合同数据字典落地 | 明确 `contmain`, `contmanaframe`, `contbd`, `contcyclist`, `contsupcharge` 字段含义和主键 |
| P0 | [x] 合同-柜组关联查询 | 以 `contmanaframe` 为主，把合同挂到柜组，再通过柜组挂到楼层/经营单元/地图 |
| P0 | [x] 合同台账第一版 | 支持按门店、楼层、柜组、供应商、合同状态、到期时间查询 |
| P0 | [x] 合同详情第一版 | 展示合同主信息、所属柜组、保底、周期费用、供应商合同费用 |
| P0 | [x] 业务员-柜组权限表设计 | 预留 ERP 权限表同步，先在柜位系统形成可查询的数据权限表 |
| P1 | 合同同步任务监控 | 记录 1 小时同步任务的开始/结束/条数/失败原因 |
| P1 | 合同创建预研 | 先设计柜位系统合同草稿表和 OA 推送状态，不急于上线 |
