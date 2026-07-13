# HDYY01柜组经营分析表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增独立的“HDYY01柜组经营分析表”，提供与 OD0002 一致的查询条件和数据权限、在线柜组经营指标、数据质量提示以及 Excel 导出。

**Architecture:** 新报表使用独立的后端服务、接口、前端契约和页面；只复用 OD0002 已验证的组织选项、权限过滤和公共展示模式。事实指标从 `salegoodslist` 聚合，会员小票从 `salehead.hykh` 识别，正向消费次数单独按机构、柜组、日期、小票计算；分类等级由新的 `mana_brand_hierarchy` 编码维表提供，缺失时保留事实行并返回质量提示。

**Tech Stack:** FastAPI、SQLAlchemy text SQL、PostgreSQL、Alembic、pytest、openpyxl、React、TypeScript、TanStack Query、Node test runner、Vite。

---

## File map

- Create `python_app/alembic/versions/c7d8e9f0a1b2_create_mana_brand_hierarchy.py`: HDYY01 分类等级维表。
- Create `docs/sql/hdyy01_mana_brand_hierarchy_source.sql`: 供现有 ETL 使用的 `ODS_MANABRAND` 编码层级抽取语句。
- Create `tests/test_hdyy01_migration.py`: 迁移结构和源层级契约测试。
- Create `python_app/services/hdyy01_report.py`: 查询构造、行归一化、合计和质量指标。
- Create `tests/test_hdyy01_report.py`: SQL 粒度、退货、会员、权限参数及响应测试。
- Create `python_app/services/hdyy01_excel.py`: 明细及说明工作表。
- Create `tests/test_hdyy01_excel.py`: Excel 与导出接口测试。
- Modify `python_app/routers/authz.py`: 注册 `sales.hdyy01.view`。
- Modify `python_app/routers/sales.py`: 门店、部门、报表、导出四个接口。
- Create `client/src/lib/hdyy01-report.ts`: 类型、查询参数、格式和分页函数。
- Create `client/src/lib/hdyy01-report.test.mjs`: 前端契约和工具测试。
- Create `client/src/pages/sales-reports/hdyy01-group-operation-analysis.tsx`: 在线报表页面。
- Create `client/src/lib/hdyy01-navigation.test.mjs`: 导航、权限和页面接线测试。
- Modify `client/src/lib/navigation-items.ts`: 报表菜单项。
- Modify `client/src/lib/module-permissions.ts`: 独立权限映射。
- Modify `client/src/lib/role-permission-tree.ts`: 角色权限树节点。
- Modify `client/src/lib/role-permission-tree.test.mjs`: 权限树契约。
- Modify `client/src/pages/main-dashboard.tsx`: 页面导入、标题和渲染分支。

### Task 1: Add the coded hierarchy landing table

**Files:**
- Create: `python_app/alembic/versions/c7d8e9f0a1b2_create_mana_brand_hierarchy.py`
- Create: `docs/sql/hdyy01_mana_brand_hierarchy_source.sql`
- Create: `tests/test_hdyy01_migration.py`

- [ ] **Step 1: Write the failing migration contract test**

```python
from pathlib import Path


MIGRATION = Path("python_app/alembic/versions/c7d8e9f0a1b2_create_mana_brand_hierarchy.py")


def test_hdyy01_hierarchy_migration_contract():
    source = MIGRATION.read_text(encoding="utf-8")
    compact = " ".join(source.lower().split())
    assert 'revision: str = "c7d8e9f0a1b2"' in source
    assert 'down_revision' in source and '"b3c4d5e6f7a8"' in source
    assert "create table mana_brand_hierarchy" in compact
    for column in (
        "level1_code", "level1_name", "level2_code", "level2_name",
        "level3_code", "level3_name", "grade_code", "grade_label", "etl_loaded_at",
    ):
        assert column in compact
    assert "primary key (level3_code)" in compact
    assert "drop table if exists mana_brand_hierarchy" in compact


def test_hdyy01_hierarchy_documents_source_chain():
    source = Path("docs/sql/hdyy01_mana_brand_hierarchy_source.sql").read_text(encoding="utf-8")
    assert "BIBH.ODS_MANABRAND" in source
    assert "level3.MBPID = level2.MBID" in source
    assert "level2.MBPID = level1.MBID" in source
    assert "CASE level3.MBSTR1" in source
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_migration.py -q`

Expected: FAIL because the migration file does not exist.

- [ ] **Step 3: Create the migration**

```python
"""create HDYY01 mana brand hierarchy

Revision ID: c7d8e9f0a1b2
Revises: b3c4d5e6f7a8
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None

DDL = r"""
CREATE TABLE mana_brand_hierarchy (
    level1_code VARCHAR(100) NOT NULL,
    level1_name VARCHAR(100) NOT NULL,
    level2_code VARCHAR(100) NOT NULL,
    level2_name VARCHAR(100) NOT NULL,
    level3_code VARCHAR(100) NOT NULL,
    level3_name VARCHAR(100) NOT NULL,
    grade_code VARCHAR(10),
    grade_label VARCHAR(1),
    etl_loaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_mana_brand_hierarchy PRIMARY KEY (level3_code),
    CONSTRAINT ck_mana_brand_hierarchy_grade CHECK (grade_label IS NULL OR grade_label IN ('A','B','C','D'))
);
CREATE INDEX idx_mana_brand_hierarchy_level2 ON mana_brand_hierarchy(level2_code);
CREATE INDEX idx_mana_brand_hierarchy_level1 ON mana_brand_hierarchy(level1_code);
COMMENT ON TABLE mana_brand_hierarchy IS
'HDYY01分类等级维表；源链：BIBH.ODS_MANABRAND level3.MBPID = level2.MBID，level2.MBPID = level1.MBID';
"""

# Source extraction contract:
# FROM BIBH.ODS_MANABRAND level3
# JOIN BIBH.ODS_MANABRAND level2 ON level3.MBPID = level2.MBID AND level2.MBCLASS = 2
# JOIN BIBH.ODS_MANABRAND level1 ON level2.MBPID = level1.MBID AND level1.MBCLASS = 1
# WHERE level3.MBCLASS = 3

def upgrade() -> None:
    op.execute(DDL)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mana_brand_hierarchy")
```

Create `docs/sql/hdyy01_mana_brand_hierarchy_source.sql` as the exact extraction contract handed to the existing ETL process:

```sql
SELECT
    level1.MBID AS level1_code,
    level1.MBCNAME AS level1_name,
    level2.MBID AS level2_code,
    level2.MBCNAME AS level2_name,
    level3.MBID AS level3_code,
    level3.MBCNAME AS level3_name,
    level3.MBSTR1 AS grade_code,
    CASE level3.MBSTR1
      WHEN '1' THEN 'A' WHEN '2' THEN 'B'
      WHEN '3' THEN 'C' WHEN '4' THEN 'D'
    END AS grade_label,
    CURRENT_TIMESTAMP AS etl_loaded_at
FROM BIBH.ODS_MANABRAND level3
JOIN BIBH.ODS_MANABRAND level2
  ON level3.MBPID = level2.MBID AND level2.MBCLASS = 2
JOIN BIBH.ODS_MANABRAND level1
  ON level2.MBPID = level1.MBID AND level1.MBCLASS = 1
WHERE level3.MBCLASS = 3;
```

The ETL job must stage this result, reject duplicate `level3_code` rows with conflicting parent or grade values, and replace `mana_brand_hierarchy` only after the staged result passes that check.

- [ ] **Step 4: Run migration tests and Alembic head check**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_migration.py -q && python_app/.venv/bin/alembic -c python_app/alembic.ini heads`

Expected: tests PASS and `c7d8e9f0a1b2 (head)`.

- [ ] **Step 5: Commit**

```bash
git add python_app/alembic/versions/c7d8e9f0a1b2_create_mana_brand_hierarchy.py docs/sql/hdyy01_mana_brand_hierarchy_source.sql tests/test_hdyy01_migration.py
git commit -m "feat: add HDYY01 hierarchy dimension"
```

### Task 2: Build the HDYY01 report query and payload

**Files:**
- Create: `python_app/services/hdyy01_report.py`
- Create: `tests/test_hdyy01_report.py`

- [ ] **Step 1: Write failing tests for the report contract**

```python
from datetime import date

from python_app.services.hdyy01_report import (
    TrustedScopeSql,
    build_report_query,
    build_report_payload,
)


def test_query_keeps_returns_but_counts_only_positive_net_tickets():
    sql, params = build_report_query(
        date(2026, 7, 1), date(2026, 7, 10),
        TrustedScopeSql(" AND 1=1"), {}, "603", "6030117",
    )
    compact = " ".join(sql.lower().split())
    assert "sum(coalesce(s.sglxssr, 0)) as ticket_sales" in compact
    assert "count(*) filter (where ticket_sales > 0)" in compact
    assert "sum(coalesce(s.sglxssr, 0)) as sales_amount" in compact
    assert "sglxssr > 0" not in compact.split("base_sales as", 1)[1].split("ticket_sales as", 1)[0]
    assert params["selected_store"] == "603"
    assert params["selected_department"] == "6030117"


def test_query_joins_member_tickets_by_bill_and_market():
    sql, _ = build_report_query(
        date(2026, 7, 1), date(2026, 7, 10), TrustedScopeSql(""), {}
    )
    compact = " ".join(sql.lower().split())
    assert "from salehead h" in compact
    assert "nullif(trim(both from coalesce(h.hykh, '')), '') is not null" in compact
    assert "h.billno = s.sglbillno" in compact
    assert "trim(both from h.mkt) = s.sglmarket::text" in compact


def test_payload_calculates_total_and_null_average_ticket():
    payload = build_report_payload([
        {"store_code": "603", "store_name": "新世纪", "department_code": "60301",
         "department_name": "女装", "group_code": "6030101", "group_name": "A柜组",
         "area": 10, "floor_code": "02", "level1_code": "10", "level1_name": "服装",
         "level2_code": "1001", "level2_name": "女装", "grade_label": "A",
         "quantity": -1, "sales_amount": -100, "tax_cost": -60, "profit": -40,
         "ticket_count": 0, "member_sales": -100, "stored_card_sales": -50}
    ], start_date=date(2026, 7, 1), end_date=date(2026, 7, 10))
    assert payload["rows"][0]["average_ticket"] is None
    assert payload["total"]["sales_amount"] == -100.0
    assert payload["total"]["ticket_count"] == 0
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_report.py -q`

Expected: FAIL because `services.hdyy01_report` does not exist.

- [ ] **Step 3: Implement the service constants, trusted scope wrapper and SQL**

Implement `hdyy01_report.py` with `EXCLUDED_DEPARTMENT_CODES` imported from `services.od0002_report`, a local `TrustedScopeSql` alias imported from the same module, and one bound SQL query using these CTEs:

```sql
WITH base_sales AS MATERIALIZED (
  SELECT s.*, st.store_name,
         TRIM(BOTH FROM s.sglmfid) AS group_code,
         COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), '未匹配') AS group_name,
         TRIM(BOTH FROM dept.mfcode) AS department_code,
         COALESCE(NULLIF(TRIM(BOTH FROM dept.mfcname), ''), '未匹配') AS department_name,
         mf.mfyymj AS area, TRIM(BOTH FROM mf.mflc) AS floor_code,
         h.level1_code, h.level1_name, h.level2_code, h.level2_name, h.grade_label
  FROM salegoodslist s
  LEFT JOIN manaframe mf ON UPPER(TRIM(s.sglmfid)) = UPPER(TRIM(mf.mfcode))
  LEFT JOIN manaframe dept ON UPPER(TRIM(mf.mfpcode)) = UPPER(TRIM(dept.mfcode))
  LEFT JOIN stores st ON TRIM(st.store_code) = s.sglmarket::text
  LEFT JOIN mana_brand_hierarchy h ON UPPER(TRIM(mf.mfchr2)) = UPPER(TRIM(h.level3_code))
  WHERE s.sglhsrq BETWEEN :start_date AND :end_date
    AND (s.sglwmid IS NULL OR s.sglwmid <> '5')
    AND TRIM(BOTH FROM COALESCE(dept.mfcode, '')) <> ALL(:excluded_department_codes)
),
ticket_sales AS (
  SELECT sglmarket::text AS store_code, group_code, sglhsrq, sglbillno,
         SUM(COALESCE(sglxssr, 0)) AS ticket_sales
  FROM base_sales GROUP BY 1,2,3,4
),
ticket_counts AS (
  SELECT store_code, group_code, COUNT(*) FILTER (WHERE ticket_sales > 0) AS ticket_count
  FROM ticket_sales GROUP BY 1,2
),
member_tickets AS (
  SELECT DISTINCT h.billno, TRIM(BOTH FROM h.mkt) AS store_code
  FROM salehead h
  WHERE h.rqsj::date BETWEEN :start_date AND :end_date
    AND NULLIF(TRIM(BOTH FROM COALESCE(h.hykh, '')), '') IS NOT NULL
),
unmatched_member_tickets AS (
  SELECT COUNT(*) AS unmatched_member_ticket_count
  FROM member_tickets mt
  WHERE NOT EXISTS (
    SELECT 1 FROM base_sales s
    WHERE s.sglbillno = mt.billno
      AND s.sglmarket::text = mt.store_code
  )
),
group_metrics AS (
  SELECT s.sglmarket::text AS store_code, MAX(s.store_name) AS store_name,
         s.department_code, MAX(s.department_name) AS department_name,
         s.group_code, MAX(s.group_name) AS group_name,
         MAX(s.area) AS area, MAX(s.floor_code) AS floor_code,
         MAX(s.level1_code) AS level1_code, MAX(s.level1_name) AS level1_name,
         MAX(s.level2_code) AS level2_code, MAX(s.level2_name) AS level2_name,
         MAX(s.grade_label) AS grade_label,
         SUM(COALESCE(s.sglsl, 0)) AS quantity,
         SUM(COALESCE(s.sglxssr, 0)) AS sales_amount,
         SUM(COALESCE(s.sgln13, 0)+COALESCE(s.sgln14, 0)-COALESCE(s.sglsupzk, 0)) AS tax_cost,
         SUM(COALESCE(s.sgln2, 0)) AS profit,
         SUM(CASE WHEN mt.billno IS NOT NULL THEN COALESCE(s.sglxssr, 0) ELSE 0 END) AS member_sales,
         SUM(COALESCE(s.sglfcard, 0)) AS stored_card_sales
  FROM base_sales s
  LEFT JOIN member_tickets mt ON mt.billno = s.sglbillno
    AND mt.store_code = s.sglmarket::text
  GROUP BY 1,3,5
)
SELECT gm.*, COALESCE(tc.ticket_count, 0) AS ticket_count,
       (SELECT unmatched_member_ticket_count FROM unmatched_member_tickets) AS unmatched_member_ticket_count
FROM group_metrics gm
LEFT JOIN ticket_counts tc USING (store_code, group_code)
ORDER BY gm.store_code, gm.department_code, gm.group_code
```

Insert the trusted scope fragment and optional selected store/department clauses inside `base_sales`. Keep every user value in `params`.

- [ ] **Step 4: Implement payload normalization and quality metrics**

```python
def _number(value):
    return float(value or 0)

def normalize_row(row):
    item = dict(row)
    count = int(item.get("ticket_count") or 0)
    sales = _number(item.get("sales_amount"))
    for key in ("area", "quantity", "sales_amount", "tax_cost", "profit", "member_sales", "stored_card_sales"):
        item[key] = _number(item.get(key))
    item["ticket_count"] = count
    item["average_ticket"] = sales / count if count else None
    return item

def build_report_payload(rows, *, start_date, end_date, selected_store=None, selected_department=None):
    normalized = [normalize_row(row) for row in rows]
    total = {key: sum(row[key] for row in normalized) for key in
             ("quantity", "sales_amount", "tax_cost", "profit", "ticket_count", "member_sales", "stored_card_sales")}
    total["average_ticket"] = total["sales_amount"] / total["ticket_count"] if total["ticket_count"] else None
    quality = {
        "unmatched_organization_group_count": sum(not row.get("department_code") for row in normalized),
        "unmatched_organization_sales_amount": sum(row["sales_amount"] for row in normalized if not row.get("department_code")),
        "unmatched_hierarchy_group_count": sum(not row.get("level2_code") for row in normalized),
        "unmatched_hierarchy_sales_amount": sum(row["sales_amount"] for row in normalized if not row.get("level2_code")),
        "missing_grade_group_count": sum(not row.get("grade_label") for row in normalized),
        "missing_grade_sales_amount": sum(row["sales_amount"] for row in normalized if not row.get("grade_label")),
        "unmatched_member_ticket_count": max(
            (int(row.get("unmatched_member_ticket_count") or 0) for row in normalized),
            default=0,
        ),
    }
    return {"dates": {"start_date": start_date, "end_date": end_date},
            "selected_store": selected_store, "selected_department": selected_department,
            "rows": normalized, "total": total, "quality": quality,
            "generated_at": datetime.now(timezone.utc).isoformat()}
```

Implement `load_hdyy01_report()` to execute the SQL once and pass the mappings to `build_report_payload()`.

- [ ] **Step 5: Run report tests and the OD0002 regression tests**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_report.py tests/test_od0002_report.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add python_app/services/hdyy01_report.py tests/test_hdyy01_report.py
git commit -m "feat: add HDYY01 report service"
```

### Task 3: Add permission-scoped APIs

**Files:**
- Modify: `python_app/routers/authz.py`
- Modify: `python_app/routers/sales.py`
- Modify: `tests/test_hdyy01_report.py`

- [ ] **Step 1: Add failing route tests**

Add tests asserting that all four endpoints require `sales.hdyy01.view`, call `load_business_scope(..., fallback_resource_code="sales")`, pass OD0002-equivalent aliases to `_business_scope_filter_sql`, reject an unauthorized selected store, bind the selected department, and load the report exactly once.

```python
def test_hdyy01_route_uses_independent_permission(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope
    calls = {}
    monkeypatch.setattr(sales, "require_permission", lambda db, user, code: calls.setdefault("permission", code))
    monkeypatch.setattr(sales, "load_business_scope", lambda *a, **k: DataScope(all_access=True))
    monkeypatch.setattr(sales, "_business_scope_filter_sql", lambda scope, params, **kwargs: calls.setdefault("aliases", kwargs) or "")
    monkeypatch.setattr(sales, "load_hdyy01_report", lambda *a, **k: {"rows": []})
    result = asyncio.run(sales.hdyy01_report(date(2026, 7, 1), date(2026, 7, 10), None, object(), object()))
    assert result == {"rows": []}
    assert calls["permission"] == "sales.hdyy01.view"
    assert calls["aliases"]["group_expr"] == "mf.mfcode"
```

- [ ] **Step 2: Run the route test and verify RED**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_report.py -q`

Expected: FAIL because HDYY01 routes and permission are missing.

- [ ] **Step 3: Register the permission and route imports**

Add to `CORE_PERMISSION_DEFINITIONS`:

```python
("sales.hdyy01.view", "查看HDYY01柜组经营分析表", "sales", "hdyy01_view"),
```

Import in `routers/sales.py`:

```python
from services.hdyy01_report import load_hdyy01_report
from services.hdyy01_excel import build_hdyy01_workbook_file
```

- [ ] **Step 4: Add the four endpoints**

Use the OD0002 route pattern with `/reports/hdyy01/stores`, `/reports/hdyy01/departments`, `/reports/hdyy01`, `/reports/hdyy01/export`. Reuse `load_od0002_authorized_stores()` and `load_od0002_authorized_departments()` for options, but require `sales.hdyy01.view` and use parameter prefixes `hdyy01_stores`, `hdyy01_departments`, and `hdyy01`. For the main query, bind category scope aliases to `h.level2_code` and `h.level2_name`; keep `mf.mfcode`, `dept.mfcode`, `dept.mfcname`, `mf.mflc`, and `st.store_id::text` for group, department, floor and store aliases. Extract `_load_hdyy01_for_request()` so query and export share validation, selected-store authorization, scope SQL and one report load.

- [ ] **Step 5: Run route and authorization tests**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_report.py tests/test_od0002_report.py tests/test_authz.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add python_app/routers/authz.py python_app/routers/sales.py tests/test_hdyy01_report.py
git commit -m "feat: expose HDYY01 report APIs"
```

### Task 4: Add the Excel workbook

**Files:**
- Create: `python_app/services/hdyy01_excel.py`
- Create: `tests/test_hdyy01_excel.py`

- [ ] **Step 1: Write failing workbook and export tests**

Create a sample payload with one positive row and one return row. Assert sheet names `明细` and `报表说明`, all 19 headers in the approved order, frozen pane `A3`, auto-filter over the detail range, two-decimal money formats, integer ticket count, total row, formula-injection escaping, report notes, streamed filename, and temporary-file closure.

- [ ] **Step 2: Run and verify RED**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_excel.py -q`

Expected: FAIL because the workbook module does not exist.

- [ ] **Step 3: Implement the workbook**

Use these fixed columns:

```python
COLUMNS = (
    ("机构", "store_name"), ("部门", "department_name"),
    ("柜组编码", "group_code"), ("柜组名称", "group_name"),
    ("面积", "area"), ("楼层", "floor_code"),
    ("一级编码", "level1_code"), ("一级名称", "level1_name"),
    ("二级编码", "level2_code"), ("二级名称", "level2_name"),
    ("等级", "grade_label"), ("数量", "quantity"),
    ("销售收入", "sales_amount"), ("含税成本", "tax_cost"),
    ("毛利", "profit"), ("消费次数", "ticket_count"),
    ("客单价", "average_ticket"), ("会员销售", "member_sales"),
    ("储值卡销售", "stored_card_sales"),
)
```

Build a `SpooledTemporaryFile`, save and seek to zero. The notes must name `sglhsrq`, `sglxssr`, `sgln13+sgln14-sglsupzk`, `sgln2`, `sglfcard`, `salehead.hykh`, positive-ticket counting, return inclusion, `sglwmid=5`, excluded department codes, and current permission scope.

- [ ] **Step 4: Run Excel tests**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_excel.py tests/test_od0002_excel.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python_app/services/hdyy01_excel.py tests/test_hdyy01_excel.py python_app/routers/sales.py
git commit -m "feat: export HDYY01 workbook"
```

### Task 5: Add the frontend contract and utilities

**Files:**
- Create: `client/src/lib/hdyy01-report.ts`
- Create: `client/src/lib/hdyy01-report.test.mjs`

- [ ] **Step 1: Write failing utility tests**

Test `buildHdyy01Params`, store-change department reset, currency/quantity/count formatting, null average ticket, query-state messages, 50-row pagination, option normalization and content-disposition filename parsing.

- [ ] **Step 2: Run and verify RED**

Run: `cd client && node --experimental-strip-types --test src/lib/hdyy01-report.test.mjs`

Expected: FAIL because `hdyy01-report.ts` does not exist.

- [ ] **Step 3: Implement types and pure helpers**

```typescript
export const HDYY01_ALL_STORES = "all";
export const HDYY01_ALL_DEPARTMENTS = "all";

export interface Hdyy01Row {
  store_code: string | null; store_name: string | null;
  department_code: string | null; department_name: string | null;
  group_code: string; group_name: string; area: number; floor_code: string | null;
  level1_code: string | null; level1_name: string | null;
  level2_code: string | null; level2_name: string | null; grade_label: string | null;
  quantity: number; sales_amount: number; tax_cost: number; profit: number;
  ticket_count: number; average_ticket: number | null;
  member_sales: number; stored_card_sales: number;
}

export function buildHdyy01Params(start: string, end: string, storeId: string, departmentId: string) {
  const params = new URLSearchParams({ start_date: start, end_date: end });
  if (storeId.trim() && storeId !== HDYY01_ALL_STORES) params.set("store_id", storeId.trim());
  if (departmentId.trim() && departmentId !== HDYY01_ALL_DEPARTMENTS) params.set("department_id", departmentId.trim());
  return params;
}

export const formatMoney = (value: number | null | undefined) =>
  value == null ? "—" : value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
```

Reuse the proven filename and object-URL revocation behavior by moving no OD0002 code; copy the small pure functions into the HDYY01 module to keep report contracts independent.

- [ ] **Step 4: Run utility tests**

Run: `cd client && node --experimental-strip-types --test src/lib/hdyy01-report.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add client/src/lib/hdyy01-report.ts client/src/lib/hdyy01-report.test.mjs
git commit -m "feat: add HDYY01 frontend contract"
```

### Task 6: Build the online report page

**Files:**
- Create: `client/src/pages/sales-reports/hdyy01-group-operation-analysis.tsx`
- Modify: `client/src/lib/hdyy01-report.test.mjs`

- [ ] **Step 1: Add a failing page-source contract test**

Assert the page contains the approved title, four endpoints, start/end/store/department controls, all 19 column labels, total row, 50-row pagination, quality labels, authenticated export, empty/error/permission states, and no “同期” or “同比” text.

- [ ] **Step 2: Run and verify RED**

Run: `cd client && node --experimental-strip-types --test src/lib/hdyy01-report.test.mjs`

Expected: FAIL because the page is missing.

- [ ] **Step 3: Implement the page**

Follow the OD0002 query-state pattern, but keep only start date, end date, store and department. Use `/api/sales/reports/hdyy01/stores`, `/departments`, the main endpoint and `/export`; set `enabled` only after the user clicks 查询. Render the approved 19 columns inside `max-h-[65vh] overflow-auto`, use sticky headers, paginate at 50 rows, and show `quality` in a separate card.

- [ ] **Step 4: Run page tests and TypeScript**

Run: `cd client && node --experimental-strip-types --test src/lib/hdyy01-report.test.mjs && npx tsc --noEmit`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add client/src/pages/sales-reports/hdyy01-group-operation-analysis.tsx client/src/lib/hdyy01-report.test.mjs
git commit -m "feat: add HDYY01 report page"
```

### Task 7: Wire navigation and independent permissions

**Files:**
- Create: `client/src/lib/hdyy01-navigation.test.mjs`
- Modify: `client/src/lib/navigation-items.ts`
- Modify: `client/src/lib/module-permissions.ts`
- Modify: `client/src/lib/role-permission-tree.ts`
- Modify: `client/src/lib/role-permission-tree.test.mjs`
- Modify: `client/src/pages/main-dashboard.tsx`

- [ ] **Step 1: Write failing navigation tests**

Assert `hdyy01-group-operation-analysis` appears after OD0002 under `sales-reports`, maps only to `sales.hdyy01.view`, appears as a dedicated role-permission node, and imports/renders `Hdyy01GroupOperationAnalysisPage` in the main dashboard.

- [ ] **Step 2: Run and verify RED**

Run: `cd client && node --experimental-strip-types --test src/lib/hdyy01-navigation.test.mjs src/lib/role-permission-tree.test.mjs`

Expected: FAIL because navigation wiring is missing.

- [ ] **Step 3: Add navigation, permission-tree and dashboard wiring**

Use the exact module id `hdyy01-group-operation-analysis`, label `HDYY01柜组经营分析表`, icon `FileSpreadsheet`, and permission `sales.hdyy01.view`. Add the page import and switch branch without changing OD0002.

- [ ] **Step 4: Run navigation tests and production build**

Run: `cd client && node --experimental-strip-types --test src/lib/hdyy01-navigation.test.mjs src/lib/role-permission-tree.test.mjs && npm run build`

Expected: PASS and Vite production build completes.

- [ ] **Step 5: Commit**

```bash
git add client/src/lib/hdyy01-navigation.test.mjs client/src/lib/navigation-items.ts client/src/lib/module-permissions.ts client/src/lib/role-permission-tree.ts client/src/lib/role-permission-tree.test.mjs client/src/pages/main-dashboard.tsx
git commit -m "feat: expose HDYY01 report navigation"
```

### Task 8: Full regression, database integration and handoff

**Files:**
- Modify only if failures reveal an HDYY01 defect in files already listed above.

- [ ] **Step 1: Run backend focused and regression tests**

Run: `python_app/.venv/bin/pytest tests/test_hdyy01_migration.py tests/test_hdyy01_report.py tests/test_hdyy01_excel.py tests/test_od0002_report.py tests/test_od0002_excel.py -q`

Expected: PASS.

- [ ] **Step 2: Run all frontend report tests and type checks**

Run: `cd client && node --experimental-strip-types --test src/lib/hdyy01-report.test.mjs src/lib/hdyy01-navigation.test.mjs src/lib/od0002-report.test.mjs src/lib/od0002-navigation.test.mjs src/lib/role-permission-tree.test.mjs && npx tsc --noEmit && npm run build`

Expected: PASS.

- [ ] **Step 3: Verify migration graph and whitespace**

Run: `python_app/.venv/bin/alembic -c python_app/alembic.ini heads && git diff --check`

Expected: a single `c7d8e9f0a1b2 (head)` and no whitespace errors.

- [ ] **Step 4: Run optional PostgreSQL integration validation**

When a disposable PostgreSQL URL is available, migrate it to head, insert fixtures containing one positive member sale, one non-member sale, one negative member return, two stores with the same group code, and a hierarchy row; then run `tests/test_hdyy01_report.py` against it. Confirm the negative return remains in amounts but not ticket count, and two stores remain separate.

- [ ] **Step 5: Record live acceptance boundary**

Document that code/tests prove query shape and local PostgreSQL behavior, while production acceptance still requires a live ERP comparison for one store/date range and a populated `mana_brand_hierarchy`. Do not claim ERP parity from automated tests alone.

- [ ] **Step 6: Final commit if verification fixes were needed**

```bash
git add python_app client tests
git commit -m "fix: complete HDYY01 verification"
```
