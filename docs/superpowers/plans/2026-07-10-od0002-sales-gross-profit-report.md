# OD0002 门店销售毛利汇总表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 ShopView 中交付受现有销售数据范围保护的 OD0002 在线报表与六工作表 Excel 导出。

**Architecture:** 新建独立的 OD0002 报表服务，集中构造权限过滤后的销售基础数据集，再从同一数据集生成分店、部门、区域、品类、柜组、楼层六种聚合。现有 `sales` 路由只负责参数、鉴权和响应；Excel 服务消费相同的标准化报表结果，前端页面通过六标签页展示并调用服务端导出。

**Tech Stack:** FastAPI、SQLAlchemy、PostgreSQL、openpyxl、React、TypeScript、TanStack Query、Radix Tabs、Node test、pytest。

---

## 文件结构

- Create `python_app/services/od0002_report.py`：日期、指标、楼层字典、SQL 和报表结果组装。
- Create `python_app/services/od0002_excel.py`：将标准化报表结果渲染成模板风格 `.xlsx`。
- Modify `python_app/routers/sales.py`：新增查询与导出端点，复用 `sales.view` 和业务范围。
- Create `tests/test_od0002_report.py`：后端日期、指标、SQL 口径、权限参数与结果组装测试。
- Create `tests/test_od0002_excel.py`：工作表、表头、格式、说明和总计测试。
- Create `client/src/lib/od0002-report.ts`：前端类型、日期和下载参数工具。
- Create `client/src/lib/od0002-report.test.mjs`：前端纯函数测试。
- Create `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`：筛选器、六标签页、状态与导出。
- Modify `client/src/lib/navigation-items.ts`：新增导航入口。
- Modify `client/src/lib/module-permissions.ts`：绑定 `sales.view`。
- Modify `client/src/pages/main-dashboard.tsx`：模块标题、导入和页面路由。
- Modify `client/src/lib/role-permission-tree.ts`：在权限树的销售报表分组中显示新入口。
- Modify `client/src/components/navigation-sidebar.test.mjs`：验证导航入口。
- Create `client/src/lib/od0002-navigation.test.mjs`：验证权限和模块注册。

### Task 1: 报表领域函数与口径

**Files:**
- Create: `python_app/services/od0002_report.py`
- Test: `tests/test_od0002_report.py`

- [ ] **Step 1: 写日期与指标的失败测试**

```python
from datetime import date
from python_app.services.od0002_report import compare_period, metric_triplet


def test_compare_period_uses_same_dates_in_previous_year():
    assert compare_period(date(2026, 5, 29), date(2026, 6, 28)) == (
        date(2025, 5, 29),
        date(2025, 6, 28),
    )


def test_compare_period_clamps_leap_day():
    assert compare_period(date(2024, 2, 29), date(2024, 3, 1)) == (
        date(2023, 2, 28),
        date(2023, 3, 1),
    )


def test_metric_triplet_calculates_weighted_margin_and_yoy():
    result = metric_triplet(120, 24, 100, 15)
    assert result == {
        "sales_current": 120.0,
        "sales_prior": 100.0,
        "sales_yoy": 0.2,
        "profit_current": 24.0,
        "profit_prior": 15.0,
        "profit_yoy": 0.6,
        "margin_current": 0.2,
        "margin_prior": 0.15,
        "margin_change": 0.05,
    }


def test_metric_triplet_returns_none_when_denominator_is_zero():
    result = metric_triplet(0, 0, 0, 0)
    assert result["sales_yoy"] is None
    assert result["profit_yoy"] is None
    assert result["margin_current"] is None
    assert result["margin_prior"] is None
    assert result["margin_change"] is None
```

- [ ] **Step 2: 运行测试并确认按预期失败**

Run: `.venv/bin/pytest tests/test_od0002_report.py -q`

Expected: FAIL，原因是 `python_app.services.od0002_report` 尚不存在。

- [ ] **Step 3: 实现最小领域函数与常量**

```python
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any

EXCLUDED_DEPARTMENT_CODES = frozenset({
    "6010115", "6010108", "6010109", "6010110", "6010202", "6010205",
    "6020105", "6020107", "6020109", "6020202", "6020205",
    "6030108", "6030109", "6030111", "6030202", "6030205",
})

FLOOR_NAMES = {
    "01": "BF", "02": "1F", "03": "2F", "04": "3F", "05": "4F",
    "06": "5F", "07": "6F", "08": "7F", "09": "8F", "10": "9F",
    "11": "10F", "12": "11F", "13": "12F", "14": "13F", "15": "14F",
    "16": "特卖", "17": "微商城", "18": "15F", "19": "16F",
}


def _previous_year(value: date) -> date:
    year = value.year - 1
    return date(year, value.month, min(value.day, monthrange(year, value.month)[1]))


def compare_period(start: date, end: date) -> tuple[date, date]:
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    return _previous_year(start), _previous_year(end)


def _number(value: Any) -> float:
    return float(value or Decimal("0"))


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def metric_triplet(sales_current: Any, profit_current: Any, sales_prior: Any, profit_prior: Any) -> dict[str, float | None]:
    sc, pc, sp, pp = map(_number, (sales_current, profit_current, sales_prior, profit_prior))
    mc, mp = _ratio(pc, sc), _ratio(pp, sp)
    return {
        "sales_current": sc, "sales_prior": sp, "sales_yoy": _ratio(sc - sp, sp),
        "profit_current": pc, "profit_prior": pp, "profit_yoy": _ratio(pc - pp, pp),
        "margin_current": mc, "margin_prior": mp,
        "margin_change": (mc - mp) if mc is not None and mp is not None else None,
    }
```

- [ ] **Step 4: 运行测试并确认通过**

Run: `.venv/bin/pytest tests/test_od0002_report.py -q`

Expected: 4 passed。

- [ ] **Step 5: 提交领域函数**

```bash
git add python_app/services/od0002_report.py tests/test_od0002_report.py
git commit -m "feat: add OD0002 report metrics"
```

### Task 2: 权限过滤基础查询与六维聚合

**Files:**
- Modify: `python_app/services/od0002_report.py`
- Modify: `tests/test_od0002_report.py`

- [ ] **Step 1: 写 SQL 口径与权限参数失败测试**

```python
from python_app.services.od0002_report import build_report_query


def test_report_query_uses_confirmed_fields_and_joins():
    sql, params = build_report_query(
        start_date=date(2026, 5, 29), end_date=date(2026, 6, 28),
        prior_start_date=date(2025, 5, 29), prior_end_date=date(2025, 6, 28),
        store_ids={"603"}, department_values={"6030101"}, group_values=set(),
    )
    normalized = " ".join(sql.lower().split())
    assert "sum(s.sglxssr)" in normalized
    assert "sum(s.sgln2)" in normalized
    assert "s.sglhsrq" in normalized
    assert "s.sglmfid" in normalized and "mf.mfcode" in normalized
    assert "mf.mfchr1" in normalized and "ac.category_code" in normalized
    assert "s.sglwmid <> '5'" in normalized
    assert "mf.mflc <> '00'" in normalized
    assert params["allowed_stores"] == ["603"]
    assert params["allowed_departments"] == ["6030101"]


def test_report_query_never_omits_empty_scope_filter():
    sql, _ = build_report_query(
        start_date=date(2026, 5, 29), end_date=date(2026, 6, 28),
        prior_start_date=date(2025, 5, 29), prior_end_date=date(2025, 6, 28),
        store_ids=set(), department_values=set(), group_values=set(),
    )
    assert "AND FALSE" in sql
```

- [ ] **Step 2: 运行目标测试并确认失败**

Run: `.venv/bin/pytest tests/test_od0002_report.py -q`

Expected: FAIL，`build_report_query` 尚不存在。

- [ ] **Step 3: 实现基础 CTE 和分组结果组装**

在 `od0002_report.py` 中实现：

```python
DIMENSIONS = {
    "stores": ("store_code", "store_name"),
    "departments": ("department_code", "department_name"),
    "areas": ("area_code", "area_name"),
    "categories": ("category_code", "category_name"),
    "groups": ("group_code", "group_name"),
    "floors": ("floor_code", "floor_name"),
}


def build_report_query(*, start_date, end_date, prior_start_date, prior_end_date,
                       store_ids, department_values, group_values, selected_store=None):
    params = {
        "start_date": start_date, "end_date": end_date,
        "prior_start_date": prior_start_date, "prior_end_date": prior_end_date,
        "excluded_departments": sorted(EXCLUDED_DEPARTMENT_CODES),
    }
    scope_parts = []
    if not store_ids and not department_values and not group_values:
        scope_parts.append("FALSE")
    if store_ids:
        scope_parts.append("s.sglmarket::text = ANY(:allowed_stores)")
        params["allowed_stores"] = sorted(store_ids)
    if department_values:
        scope_parts.append("dept.mfcode = ANY(:allowed_departments)")
        params["allowed_departments"] = sorted(department_values)
    if group_values:
        scope_parts.append("mf.mfcode = ANY(:allowed_groups)")
        params["allowed_groups"] = sorted(group_values)
    if selected_store:
        scope_parts.append("s.sglmarket::text = :selected_store")
        params["selected_store"] = selected_store
    scope_sql = " AND (" + " OR ".join(scope_parts) + ")"
    dimensions = {
        "stores": ("store_code", "store_name"), "departments": ("department_code", "department_name"),
        "areas": ("area_code", "area_name"), "categories": ("category_code", "category_name"),
        "groups": ("group_code", "group_name"), "floors": ("floor_code", "floor_name"),
    }
    unions = []
    for dimension_type, (code, name) in dimensions.items():
        unions.append(
            f"SELECT '{dimension_type}' dimension_type, store_code, store_name, {code} dimension_code, "
            f"{name} dimension_name, "
            "SUM(sales_amount) FILTER (WHERE period='current') sales_current, "
            "SUM(profit_amount) FILTER (WHERE period='current') profit_current, "
            "SUM(sales_amount) FILTER (WHERE period='prior') sales_prior, "
            "SUM(profit_amount) FILTER (WHERE period='prior') profit_prior "
            f"FROM periodized GROUP BY store_code, store_name, {code}, {name}"
        )
    sql = BASE_CTE_SQL.format(scope_sql=scope_sql) + "\nUNION ALL\n".join(unions)
    return sql, params


def normalize_rows(rows):
    result = {name: [] for name in DIMENSIONS}
    quality = {"unmatched_area_category": 0, "unmatched_floor": 0}
    for raw in rows:
        item = {
            "store_code": raw["store_code"],
            "store_name": raw["store_name"],
            "dimension_code": raw["dimension_code"],
            "dimension_name": raw["dimension_name"] or "未匹配",
            **metric_triplet(raw["sales_current"], raw["profit_current"], raw["sales_prior"], raw["profit_prior"]),
        }
        result[raw["dimension_type"]].append(item)
    return result, quality
```

`BASE_CTE_SQL` 必须是完整的参数化 PostgreSQL CTE：连接 `stores`、柜组 `manaframe mf`、部门 `manaframe dept` 和 `area_category ac`，用 `CASE` 生成 current/prior，过滤租赁、楼层 `00`、排除部门和“其他类别区域”，并输出六组维度列。每个 `UNION ALL` 分支必须包含 `store_code`。权限条件从 `load_business_scope()` 的 allow/deny 集合转换成允许条件与拒绝条件；拒绝条件使用 `NOT (...)` 并优先于允许条件。

- [ ] **Step 4: 增加标准化结果和多门店隔离测试并运行**

```python
def test_normalize_rows_keeps_same_department_separate_by_store():
    rows = [
        {"dimension_type": "departments", "store_code": "601", "store_name": "中心", "dimension_code": "01", "dimension_name": "一部", "sales_current": 10, "profit_current": 1, "sales_prior": 8, "profit_prior": 1},
        {"dimension_type": "departments", "store_code": "603", "store_name": "新世纪", "dimension_code": "01", "dimension_name": "一部", "sales_current": 20, "profit_current": 2, "sales_prior": 18, "profit_prior": 2},
    ]
    result, _ = normalize_rows(rows)
    assert [(x["store_code"], x["sales_current"]) for x in result["departments"]] == [("601", 10.0), ("603", 20.0)]
```

Run: `.venv/bin/pytest tests/test_od0002_report.py -q`

Expected: all passed。

- [ ] **Step 5: 提交聚合服务**

```bash
git add python_app/services/od0002_report.py tests/test_od0002_report.py
git commit -m "feat: aggregate OD0002 report dimensions"
```

### Task 3: 查询 API 与部门权限集成

**Files:**
- Modify: `python_app/routers/sales.py`
- Modify: `tests/test_od0002_report.py`

- [ ] **Step 1: 写路由契约失败测试**

```python
from pathlib import Path


def test_sales_router_registers_od0002_query_and_export():
    source = Path("python_app/routers/sales.py").read_text()
    assert '@router.get("/reports/od0002")' in source
    assert '@router.get("/reports/od0002/export")' in source
    assert 'require_permission(db, current_user, "sales.view")' in source
    assert "load_business_scope" in source
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/pytest tests/test_od0002_report.py::test_sales_router_registers_od0002_query_and_export -q`

Expected: FAIL，OD0002 路由尚未注册。

- [ ] **Step 3: 实现查询端点**

在 `sales.py` 中增加：

```python
@router.get("/reports/od0002")
async def od0002_report(
    start_date: date = Query(), end_date: date = Query(),
    store_id: str | None = Query(None), db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    prior_start, prior_end = compare_period(start_date, end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    return load_od0002_report(
        db, scope=scope, start_date=start_date, end_date=end_date,
        prior_start_date=prior_start, prior_end_date=prior_end,
        selected_store=store_id,
    )
```

`load_od0002_report` 必须调用现有业务范围 SQL 生成逻辑；如果选中门店不在权限范围内，返回 403；结束日期早于开始日期返回 422。

- [ ] **Step 4: 运行后端测试**

Run: `.venv/bin/pytest tests/test_od0002_report.py -q`

Expected: all passed。

- [ ] **Step 5: 提交 API**

```bash
git add python_app/routers/sales.py python_app/services/od0002_report.py tests/test_od0002_report.py
git commit -m "feat: expose OD0002 report API"
```

### Task 4: 服务端 Excel 导出

**Files:**
- Create: `python_app/services/od0002_excel.py`
- Modify: `python_app/routers/sales.py`
- Test: `tests/test_od0002_excel.py`

- [ ] **Step 1: 写工作簿失败测试**

```python
from io import BytesIO
from openpyxl import load_workbook
from python_app.services.od0002_excel import build_od0002_workbook


def test_workbook_contains_six_sheets_and_notes(sample_report):
    payload = build_od0002_workbook(sample_report)
    wb = load_workbook(BytesIO(payload))
    assert wb.sheetnames == ["分店", "部门", "区域", "品类", "柜组", "楼层", "报表说明"]
    assert wb["分店"]["A2"].value.startswith("本期日期范围：")
    assert wb["分店"]["B6"].number_format == "0.00"
    assert wb["分店"]["D6"].number_format == "0.00%"
    assert "sglxssr" in wb["报表说明"]["B2"].value
    assert "当前用户权限范围" in wb["报表说明"]["B2"].value
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/pytest tests/test_od0002_excel.py -q`

Expected: FAIL，Excel 服务尚不存在。

- [ ] **Step 3: 实现模板风格工作簿**

```python
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

SHEET_NAMES = ["分店", "部门", "区域", "品类", "柜组", "楼层"]
HEADER_FILL = PatternFill("solid", fgColor="0874B5")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def build_od0002_workbook(report: dict) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for key, title in zip(("stores", "departments", "areas", "categories", "groups", "floors"), SHEET_NAMES):
        ws = wb.create_sheet(title)
        write_report_sheet(ws, title, report, report["dimensions"][key])
    notes = wb.create_sheet("报表说明")
    notes["B2"] = build_notes(report)
    notes["B2"].alignment = Alignment(wrap_text=True, vertical="top")
    notes.column_dimensions["B"].width = 110
    notes.row_dimensions[2].height = 180
    output = BytesIO()
    wb.save(output)
    return output.getvalue()
```

`write_report_sheet` 写入日期行、三层表头、万元金额、百分比、合计行、冻结窗格和蓝色标题样式。金额单元格写入 `元 / 10000`；同比和毛利率保持小数数值并使用百分比格式。

- [ ] **Step 4: 实现导出端点并运行测试**

```python
@router.get("/reports/od0002/export")
async def export_od0002_report(
    start_date: date = Query(), end_date: date = Query(),
    store_id: str | None = Query(None), db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "sales.view")
    prior_start, prior_end = compare_period(start_date, end_date)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    report = load_od0002_report(
        db, scope=scope, start_date=start_date, end_date=end_date,
        prior_start_date=prior_start, prior_end_date=prior_end,
        selected_store=store_id,
    )
    content = build_od0002_workbook(report)
    filename = f"OD0002_门店销售毛利汇总表_{start_date}_{end_date}.xlsx"
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
```

Run: `.venv/bin/pytest tests/test_od0002_excel.py tests/test_od0002_report.py -q`

Expected: all passed。

- [ ] **Step 5: 提交导出服务**

```bash
git add python_app/services/od0002_excel.py python_app/routers/sales.py tests/test_od0002_excel.py
git commit -m "feat: export OD0002 workbook"
```

### Task 5: 前端日期、类型和下载工具

**Files:**
- Create: `client/src/lib/od0002-report.ts`
- Create: `client/src/lib/od0002-report.test.mjs`

- [ ] **Step 1: 写前端失败测试**

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { buildOd0002Params, previousYearDate } from "./od0002-report.ts";

test("previousYearDate clamps leap day", () => {
  assert.equal(previousYearDate("2024-02-29"), "2023-02-28");
});

test("buildOd0002Params omits all-store sentinel", () => {
  assert.equal(buildOd0002Params("2026-05-29", "2026-06-28", "all"), "start_date=2026-05-29&end_date=2026-06-28");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs`

Expected: FAIL，模块尚不存在。

- [ ] **Step 3: 实现前端工具和接口类型**

```typescript
export const OD0002_ALL_STORES = "all";
export type Od0002DimensionKey = "stores" | "departments" | "areas" | "categories" | "groups" | "floors";

export function previousYearDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  const candidate = new Date(Date.UTC(year - 1, month - 1, day));
  if (candidate.getUTCMonth() !== month - 1) return `${year - 1}-${String(month).padStart(2, "0")}-28`;
  return candidate.toISOString().slice(0, 10);
}

export function buildOd0002Params(start: string, end: string, storeId: string): string {
  const params = new URLSearchParams({ start_date: start, end_date: end });
  if (storeId && storeId !== OD0002_ALL_STORES) params.set("store_id", storeId);
  return params.toString();
}
```

同时声明 `Od0002Row`、`Od0002Quality` 和 `Od0002Response`，字段名与后端响应完全一致。

- [ ] **Step 4: 运行测试和类型检查**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs && npx tsc --noEmit`

Expected: tests passed，TypeScript 无错误。

- [ ] **Step 5: 提交前端工具**

```bash
git add client/src/lib/od0002-report.ts client/src/lib/od0002-report.test.mjs
git commit -m "feat: add OD0002 frontend model"
```

### Task 6: 在线六标签页页面

**Files:**
- Create: `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`
- Modify: `client/src/lib/od0002-report.test.mjs`

- [ ] **Step 1: 写页面配置失败测试**

```javascript
import { OD0002_TABS } from "./od0002-report.ts";

test("OD0002 exposes the six approved tabs", () => {
  assert.deepEqual(OD0002_TABS.map((x) => x.label), ["分店", "部门", "区域", "品类", "柜组", "楼层"]);
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs`

Expected: FAIL，`OD0002_TABS` 尚不存在。

- [ ] **Step 3: 添加标签配置并实现页面**

```typescript
export const OD0002_TABS = [
  { key: "stores", label: "分店" },
  { key: "departments", label: "部门" },
  { key: "areas", label: "区域" },
  { key: "categories", label: "品类" },
  { key: "groups", label: "柜组" },
  { key: "floors", label: "楼层" },
] as const;
```

页面使用 `Card`、`Input`、`Select`、`Tabs`、`Table` 和现有 `GlobalStoreSelector`/门店查询模式。查询键必须包含开始、结束和门店；点击查询才提交编辑中的筛选值。导出通过认证请求取得 blob，再用临时对象 URL 下载，文件名读取 `Content-Disposition`。

表格固定显示：维度名称、销售收入本期/同期/同比、毛利额本期/同期/同比、毛利率本期/同期/同比。空值显示 `—`，金额除以 10000 保留两位，百分比保留两位。接口错误、无数据、质量提示分别显示独立状态。

- [ ] **Step 4: 运行前端测试和构建**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs && npm run build`

Expected: tests passed，Vite build successful。

- [ ] **Step 5: 提交页面**

```bash
git add client/src/lib/od0002-report.ts client/src/lib/od0002-report.test.mjs client/src/pages/sales-reports/od0002-sales-gross-profit.tsx
git commit -m "feat: add OD0002 report page"
```

### Task 7: 导航、权限树与模块路由

**Files:**
- Modify: `client/src/lib/navigation-items.ts`
- Modify: `client/src/lib/module-permissions.ts`
- Modify: `client/src/lib/role-permission-tree.ts`
- Modify: `client/src/pages/main-dashboard.tsx`
- Modify: `client/src/components/navigation-sidebar.test.mjs`
- Create: `client/src/lib/od0002-navigation.test.mjs`

- [ ] **Step 1: 写导航失败测试**

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("OD0002 is registered under sales reports and requires sales.view", () => {
  const navigation = fs.readFileSync("src/lib/navigation-items.ts", "utf8");
  const permissions = fs.readFileSync("src/lib/module-permissions.ts", "utf8");
  const dashboard = fs.readFileSync("src/pages/main-dashboard.tsx", "utf8");
  assert.match(navigation, /id: "od0002-sales-gross-profit"/);
  assert.match(navigation, /OD0002 门店销售毛利汇总表/);
  assert.match(permissions, /"od0002-sales-gross-profit": \["sales\.view"\]/);
  assert.match(dashboard, /case "od0002-sales-gross-profit"/);
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-navigation.test.mjs`

Expected: FAIL，导航尚未注册。

- [ ] **Step 3: 注册模块**

在 `sales-reports` 的 `subItems` 中追加：

```typescript
{ id: "od0002-sales-gross-profit", name: "OD0002 门店销售毛利汇总表", icon: FileSpreadsheet }
```

在 `MODULE_PERMISSION_REQUIREMENTS` 中追加：

```typescript
"od0002-sales-gross-profit": ["sales.view"],
```

在 `MODULE_LABELS` 与 `renderModuleContent` 中注册相同模块 ID，并在 `role-permission-tree.ts` 的销售报表节点追加该模块。导入 `Od0002SalesGrossProfitReportPage` 后返回 `<Od0002SalesGrossProfitReportPage />`。

- [ ] **Step 4: 运行导航测试与前端构建**

Run: `cd client && node --test --experimental-strip-types src/components/navigation-sidebar.test.mjs src/lib/od0002-navigation.test.mjs && npm run build`

Expected: tests passed，build successful。

- [ ] **Step 5: 提交导航集成**

```bash
git add client/src/lib/navigation-items.ts client/src/lib/module-permissions.ts client/src/lib/role-permission-tree.ts client/src/pages/main-dashboard.tsx client/src/components/navigation-sidebar.test.mjs client/src/lib/od0002-navigation.test.mjs
git commit -m "feat: register OD0002 sales report"
```

### Task 8: 数据对账、完整验证与文档收尾

**Files:**
- Modify: `tests/test_od0002_report.py`
- Modify: `tests/test_od0002_excel.py`
- Modify: `docs/superpowers/specs/2026-07-10-od0002-sales-gross-profit-report-design.md` only when a confirmed implementation constraint changes the approved design

- [ ] **Step 1: 写参考期间对账测试**

增加一个只在配置测试数据库时运行的集成测试，使用市场 `603`、同期 `2025-05-29` 至 `2025-06-28`，断言过滤后销售收入为 `16837093.9096`。没有测试数据库时用 `pytest.skip`，单元测试仍必须运行。

```python
def test_od0002_reference_period_reconciles(db_session):
    report = load_od0002_report(
        db_session,
        scope=full_store_scope("603"),
        start_date=date(2025, 5, 29), end_date=date(2025, 6, 28),
        prior_start_date=date(2024, 5, 29), prior_end_date=date(2024, 6, 28),
        selected_store="603",
    )
    total = report["totals"]["stores"]
    assert total["sales_current"] == pytest.approx(16837093.9096, abs=0.01)
```

- [ ] **Step 2: 运行完整后端测试**

Run: `.venv/bin/pytest tests/test_od0002_report.py tests/test_od0002_excel.py -q`

Expected: all passed；集成环境缺失时只允许 reference-period 测试显示 skipped。

- [ ] **Step 3: 运行完整前端测试与构建**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs src/lib/od0002-navigation.test.mjs src/components/navigation-sidebar.test.mjs && npm run build`

Expected: all tests passed，build successful，零 TypeScript 错误。

- [ ] **Step 4: 执行真实只读接口抽查**

使用一个拥有市场 `603` 全店权限的测试账号查询同期参考范围；确认分店、部门、区域、品类、柜组和楼层各自合计一致，导出的六个工作表与页面总计一致。再使用一个仅有单部门权限的测试账号，确认六页及 Excel 都不出现未授权部门数据。

- [ ] **Step 5: 查看页面和 Excel 视觉结果**

启动本地应用，逐个查看六个标签页在常用窗口宽度下是否有截断或错位；下载 Excel 并检查所有工作表的标题、表头、列宽、冻结行、金额和百分比格式。发现问题时先写一个能捕获错误的测试，再修复。

- [ ] **Step 6: 提交验证收尾**

```bash
git add tests/test_od0002_report.py tests/test_od0002_excel.py docs/superpowers/specs/2026-07-10-od0002-sales-gross-profit-report-design.md
git commit -m "test: verify OD0002 report end to end"
```
