# 商品周转财务月报

## 已落地的数据与调度

- 表：`public.inventory_turnover_monthly`。
- 每行：财务年月 × 门店 × 柜组 × 供应商 × 经营方式（经销、成本代销）。
- 财务年月示例：2026-08 = 2026-07-29～2026-08-28。沿用系统特殊月份规则：1月1～28日、12月11月29日～12月31日，平年3月从3月1日开始。
- 保存每个财务月的最新结果，不为每次运行追加重复月报。本月统计至北京时间前一天；历史月份统计至月末。
- PAPI 数据库任务 **66**：销售数据库 sales_db（源4）到 sales_db（目标4），每日北京时间 **06:30**，更新本财务月和上财务月。
- 首载：2026-08、2026-09，四门店共595行；2026-09统计截止2026-09-15。
- 使用唯一键更新，可重复执行。以前存在而源数据删除的组合也会重新输出零金额，避免留存旧金额。
- 不修改原始销售/库存表、不修改其他同步任务。相关任务配置与首载证据保存在 `reports/inventory-turnover-20260916/`。

## 公式

| 字段 | 口径 |
|---|---|
| 销售数量、收入 | `salegoodslist` 按 `sglhsrq` 汇总，保留退货负数 |
| 不含税销售成本 | 逐行 `sgln13 / (1 + sgljjtax)` 再汇总，不统一假定13% |
| 期末数量、成本 | `goodsstock_bak` 统计截止日快照，按柜组、供应商、经营方式汇总 |
| 不含税平均库存 | 期间库存 `gstkcbhsjjje` 合计 / 已统计自然日数 |
| 周转率 | 不含税销售成本 / 不含税平均库存 |
| 周转天数 | 不含税平均库存 / 不含税销售成本 × 已统计天数 |
| 期末存销比 | 期末不含税库存成本 / 不含税销售成本 |
| 期末库存覆盖天数 | 期末存销比 × 已统计天数（按期间历史速度估算，不是需求预测） |

零数量、零收入且成本为空的记录按零业务额处理。有业务金额但缺失成本、非零成本缺失或异常进项税率，成本及相关比率留空并标记异常。
门店期间库存快照缺日时平均库存及周转率留空；缺期末快照时期末金额及存销比留空。销售日期覆盖不全时相关比率留空，需区分未同步与停业。覆盖天数仅检查门店日期是否存在，不证明源系统每条明细都已完整同步。
平均库存非正、销售成本非正时周转指标留空；负期末成本不计算期末存销比。
未提供可售/残损/临期及在途标识，因此“覆盖天数”是账面库存估算，不能直接当作采购订单数量。

## 按门店、部门、财务年月查询

```sql
SELECT financial_month, store_code, store_name,
       department_code, department_name, group_code, group_name,
       supplier_code, supplier_name, operation_method,
       period_start, period_end, as_of_date,
       sales_quantity, sales_revenue, sales_cost_ex_tax,
       ending_quantity, ending_cost_ex_tax, average_cost_ex_tax,
       turnover_days, turnover_rate, stock_sales_ratio, stock_cover_days,
       data_status, updated_at
FROM public.inventory_turnover_monthly
WHERE store_code = '603'
  AND department_code = '6030101'
  AND financial_month = '2026-08'
ORDER BY group_code, supplier_code, operation_method;
```

部门编码示例 `6030101` 为新世纪一部（化妆）。去掉部门条件可以查询该门店所有部门。
用 `SELECT DISTINCT store_code, department_code, department_name FROM inventory_turnover_monthly` 查询已保存的部门。

## 应用入口与权限

代码入口：库存管理 → 商品周转财务月报，门店、部门、财务年月联动，支持分页和完整结果 Excel 导出。
API：`GET /api/inventory-turnover/options`、`GET /api/inventory-turnover`、`GET /api/inventory-turnover/export`。
查询和导出使用同一权限 `sales.inventory_turnover.view` 及原有门店、部门、柜组、供应商、类别、楼层数据范围。品牌级授权不适用于柜组汇总，遇到此类范围会拒绝查询而不是放宽权限。
权限只注册，不自动给普通角色授权。

数据库DDL与定时任务已在当前配置的sales_db/PAPI生效；网页/API代码尚需随应用版本部署，不能把本地构建成功视为服务器菜单已上线。
迁移 `s8b9c0d1e2f3` 可重复执行同一DDL。当前只应用本次DDL，未执行工作区其他待迁移版本、未改写Alembic版本记录。

## 验证与已知限制

- 首载源595行、目标595行、唯一业务键595个。
- 新世纪8月化妆部门16行平均库存与原Excel一致；00062销售和期末数量为0，20530销售88515元、期末413件。
- 隔离临时表集成测试覆盖供应商分离、退货、多税率、缺库存日期、缺税率、年初年末与闰年、月中天数、源记录删除。
- 当前其他门店8月存在缺日，系统明确标记，不把缺失日期当0生成正常周转率。
- 调度已启用，需后续由PAPI运行日志确认每天实际运行成功；首次手动运行成功不代表未来调度永不失败。

手动重算旧月份可将 `inventory_turnover_rows(年份,月份,截止日期)` 作为PAPI源，沿用任务66字段映射与唯一键更新；生产查询不要自行把缺失指标替换成0。

## 按品牌汇总与前台 Sheet

- 财务月报默认展示“按品牌周转率汇总”，另有“供应商明细”页签。点击品牌名称打开右侧 Sheet，查看该柜组各供应商、经营方式明细。
- 品牌沿用原Excel的品牌柜组口径，以门店、部门、财务年月、柜组编码分组；同柜组多个供应商合并，同名不同柜组不自动合并。不是商品档案品牌编码的跨柜组汇总。
- API同一响应中的 `brands` 为汇总，`rows` 为明细。汇总基于已通过权限过滤的明细，不会因聚合扩大供应商或门店权限。
- 前台按权限筛选明细后汇总，后台另提供实体汇总表 `public.inventory_turnover_brand_monthly`。复用每日06:30任务；明细写入后通过数据库触发器在同一事务刷新相关财务月的实体汇总。数量、金额求和后重算比率，不平均明细比率。
- 任一明细金额为空则对应汇总金额为空；期间不一致时不计算相关比率。零销售供应商及负库存尾差仍计入金额，保留“明细异常”状态及异常明细数，可从Sheet定位。
- Excel导出包含“按品牌周转率汇总”和“供应商明细”两张工作表，沿用同一查询权限。
- 本次实际数据核验：新世纪2026-08化妆部门16条供应商明细，合并为15个品牌柜组；玉兰油两家供应商合并销售收入88,515元、期末413件，周转率约0.611967、周转天数50.66、期末存销比2.026884。
- 本次页面、API和导出变更仍为本地代码，须随应用部署后才能在服务器入口使用。


## 后台直接取数：品牌汇总实体表

已创建 `sales_db.public.inventory_turnover_brand_monthly`，不是视图。唯一键为财务年月、门店编码、部门编码、品牌柜组编码。首载208行，覆盖四门店的2026-08、2026-09，合计对应595条供应商明细。

```sql
SELECT financial_month, store_code, store_name,
       department_code, department_name, group_code, group_name,
       supplier_count, detail_count,
       sales_quantity, sales_revenue, sales_cost_ex_tax,
       ending_quantity, ending_cost_ex_tax, average_cost_ex_tax,
       turnover_rate, turnover_days, stock_sales_ratio, stock_cover_days,
       as_of_date, exception_count, data_status, updated_at, refreshed_at
FROM public.inventory_turnover_brand_monthly
WHERE store_code = '603'
  AND department_code = '6030101'
  AND financial_month = '2026-08'
ORDER BY group_code;
```

- `group_code/group_name`：品牌柜组编码/名称，沿用原Excel口径。
- `supplier_count`：去重供应商数；`detail_count`：供应商×经营方式明细行数。
- `exception_count/data_status`：异常明细行数及原因；明细异常不一定意味着合并后的金额非正。
- `updated_at`：所含明细最早更新时间；`refreshed_at`：本汇总行刷新时间。
- 触发器覆盖明细INSERT、UPDATE、DELETE，按发生变化的财务月重算；删除最后一条明细时对应汇总行也会移除。刷新失败会回滚该次明细写入，不提交半套结果。
- 原PAPI任务66仍为每日北京时间06:30，不增加第二个独立调度。补算旧财务月明细时也会同步刷新对应汇总。
- 后台表包含全量柜组数据，直接SQL读取按数据库账号权限控制；不自动套用应用角色的供应商范围。前台继续先过滤授权明细再汇总，避免受限账号读到柜组其他供应商金额。
- DDL：`python_app/sql/inventory_turnover_brand.sql`；迁移：`t9c0d1e2f3a4`。当前已直接应用此DDL，未执行其他待发布迁移、未改写Alembic版本记录。
