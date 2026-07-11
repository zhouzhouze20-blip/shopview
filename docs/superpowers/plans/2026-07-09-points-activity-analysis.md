# Points Activity Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an activity-analysis page that audits member point grants for the black-diamond 3x, black-gold 2x, and birthday-month point activity, with department-scoped drilldown and explicit rule-match status.

**Architecture:** Add a focused backend point-rule service that computes ERP-style point basis from `sellpaygoods`, `paymode`, `tktqtype`, `tktqtypemkt`, `card_paymoderule`, and `rulejfrate`. Expose summary, department, member, and ticket drilldown endpoints under `/api/activity-analysis/points`. Add a React page under the existing `activity-analysis` group and keep all drilldowns constrained by the current user's business scope.

**Tech Stack:** FastAPI, SQLAlchemy text queries, PostgreSQL, React, TanStack Query, existing shadcn UI components, Python `unittest`, Node `.mjs` tests.

---

## File Structure

- Create `python_app/services/activity_analysis/point_rules.py`: SQL fragments and helpers for point-rule source status, ERP basis calculation, and row status labels.
- Modify `python_app/routers/activity_analysis.py`: add four read endpoints under `/points` and reuse `ACTIVITY_ANALYSIS_PERMISSION`, `_ensure_required_tables`, and business-scope helpers.
- Create `test/test_activity_points_rule_sql.py`: backend tests for SQL generation and status behavior.
- Create `client/src/pages/activity-analysis/points.tsx`: activity point audit UI with cards, rule status, department/member/ticket drilldown.
- Modify `client/src/pages/main-dashboard.tsx`: import and route the new page.
- Modify `client/src/lib/navigation-items.ts`: add `points-activity-analysis` under the existing activity-analysis group.
- Modify `client/src/lib/module-permissions.ts` only if the new module id is enforced by the current menu permission map.
- Create `client/src/lib/points-activity-analysis.test.mjs`: frontend pure formatting tests for statuses and metric labels.

## Task 1: Backend Point Rule SQL Helper

**Files:**
- Create: `python_app/services/activity_analysis/point_rules.py`
- Test: `test/test_activity_points_rule_sql.py`

- [ ] **Step 1: Write the failing test**

```python
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from services.activity_analysis.point_rules import (
    point_rule_source_tables,
    point_status_case_sql,
)


class ActivityPointsRuleSqlTest(unittest.TestCase):
    def test_source_tables_include_required_erp_dependencies(self):
        self.assertEqual(
            point_rule_source_tables(),
            (
                "order_point",
                "sellpaygoods",
                "paymode",
                "tktqtype",
                "tktqtypemkt",
                "card_paymoderule",
                "rulejfrate",
            ),
        )

    def test_status_case_exposes_degraded_calculation_states(self):
        sql = point_status_case_sql()

        self.assertIn("MISSING_RATE", sql)
        self.assertIn("ZERO_RATE", sql)
        self.assertIn("ALLOCATION_IMBALANCE", sql)
        self.assertIn("POINT_DIFF", sql)
        self.assertIn("OK", sql)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 test/test_activity_points_rule_sql.py
```

Expected: fail with `ModuleNotFoundError` for `services.activity_analysis.point_rules`.

- [ ] **Step 3: Create the helper**

```python
from __future__ import annotations


def point_rule_source_tables() -> tuple[str, ...]:
    return (
        "order_point",
        "sellpaygoods",
        "paymode",
        "tktqtype",
        "tktqtypemkt",
        "card_paymoderule",
        "rulejfrate",
    )


def point_status_case_sql(
    actual_expr: str = "actual_point",
    expected_expr: str = "expected_point",
    rate_expr: str = "jfrate",
    allocation_diff_expr: str = "allocation_diff_amount",
) -> str:
    return f"""
      CASE
        WHEN {rate_expr} IS NULL THEN 'MISSING_RATE'
        WHEN {rate_expr} = 0 THEN 'ZERO_RATE'
        WHEN ABS(COALESCE({allocation_diff_expr}, 0)) > 0.01 THEN 'ALLOCATION_IMBALANCE'
        WHEN ABS(COALESCE({actual_expr}, 0) - COALESCE({expected_expr}, 0)) > 0.01 THEN 'POINT_DIFF'
        ELSE 'OK'
      END
    """


def point_status_label(status: str | None) -> str:
    labels = {
        "OK": "正常",
        "POINT_DIFF": "积分差异",
        "MISSING_RATE": "缺积分倍率",
        "ZERO_RATE": "积分率为0",
        "ALLOCATION_IMBALANCE": "付款分摊不平",
    }
    return labels.get((status or "").strip().upper(), "待复核")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 test/test_activity_points_rule_sql.py
```

Expected: `OK`.

## Task 2: Backend Points Endpoints

**Files:**
- Modify: `python_app/routers/activity_analysis.py`
- Test: `test/test_activity_points_rule_sql.py`

- [ ] **Step 1: Add failing tests for endpoint path constants**

Append to `test/test_activity_points_rule_sql.py`:

```python
class ActivityPointsRouterContractTest(unittest.TestCase):
    def test_activity_analysis_router_exposes_points_paths(self):
        router_file = Path(__file__).resolve().parents[1] / "python_app" / "routers" / "activity_analysis.py"
        text = router_file.read_text(encoding="utf-8")

        self.assertIn('@router.get("/points/overview")', text)
        self.assertIn('@router.get("/points/departments")', text)
        self.assertIn('@router.get("/points/members")', text)
        self.assertIn('@router.get("/points/tickets")', text)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 test/test_activity_points_rule_sql.py
```

Expected: fail because `/points/*` routes are not present.

- [ ] **Step 3: Add route imports and shared source-status helper**

In `python_app/routers/activity_analysis.py`, add:

```python
from services.activity_analysis.point_rules import point_rule_source_tables, point_status_case_sql
```

Add this helper near `_ensure_required_tables`:

```python
def _point_rule_source_status(db: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table_name in point_rule_source_tables():
        exists = _table_exists(db, table_name)
        row_count = 0
        if exists:
            row_count = int(_one(db, f"SELECT COUNT(*) AS row_count FROM {table_name}")["row_count"] or 0)
        rows.append({"table_name": table_name, "exists": exists, "row_count": row_count})
    return rows
```

- [ ] **Step 4: Add `/points/overview`**

Add an endpoint that:

```python
@router.get("/points/overview")
async def points_overview(
    start_date: str = Query(..., description="销售日期起 YYYY-MM-DD"),
    end_date: str = Query(..., description="销售日期止 YYYY-MM-DD"),
    department_code: str | None = Query(None, description="部门编码"),
    group_code: str | None = Query(None, description="柜组编码"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, ACTIVITY_ANALYSIS_PERMISSION)
    _ensure_required_tables(db)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    params: dict[str, Any] = {"start_date": start_date, "end_date": end_date}
    if department_code:
        params["department_code"] = department_code.strip()
    if group_code:
        params["group_code"] = group_code.strip()

    rows = _rows(db, POINTS_BASE_SQL + """
        SELECT
          COUNT(DISTINCT billno) AS ticket_count,
          COUNT(DISTINCT member_no) FILTER (WHERE member_no <> '') AS member_count,
          COALESCE(SUM(total_sales_amount), 0) AS total_sales_amount,
          COALESCE(SUM(point_basis_amount), 0) AS point_basis_amount,
          COALESCE(SUM(actual_point), 0) AS actual_point,
          COALESCE(SUM(expected_point), 0) AS expected_point,
          COALESCE(SUM(actual_point - expected_point), 0) AS point_diff,
          COUNT(*) FILTER (WHERE status <> 'OK') AS issue_count
        FROM point_rows
        WHERE sale_date BETWEEN :start_date AND :end_date
        """, params)
    summary = rows[0] if rows else {}
    return {"summary": summary, "source_status": _point_rule_source_status(db)}
```

Define `POINTS_BASE_SQL` in the same file as a CTE that joins `sellpaygoods`, `salehead`, `salegoods`, `paymode`, `tktqtype`, `tktqtypemkt`, `card_paymoderule`, latest `rulejfrate`, and `order_point`. It must select `status` using `point_status_case_sql()`.

- [ ] **Step 5: Add `/points/departments`, `/points/members`, and `/points/tickets`**

Each endpoint must use the same `POINTS_BASE_SQL` and return:

```python
{"items": rows, "source_status": _point_rule_source_status(db)}
```

The departments endpoint groups by department and group; the members endpoint filters by department/group and groups by member; the tickets endpoint filters by member or status and returns bill-level rows.

- [ ] **Step 6: Run backend tests**

Run:

```bash
python3 test/test_activity_points_rule_sql.py
```

Expected: `OK`.

## Task 3: Frontend Formatting Helpers

**Files:**
- Create: `client/src/lib/points-activity-analysis.ts`
- Test: `client/src/lib/points-activity-analysis.test.mjs`

- [ ] **Step 1: Write failing frontend helper test**

```javascript
import assert from "node:assert/strict";
import test from "node:test";
import { pointStatusLabel, pointStatusTone } from "./points-activity-analysis.ts";

test("maps backend point statuses to user-facing labels", () => {
  assert.equal(pointStatusLabel("OK"), "正常");
  assert.equal(pointStatusLabel("POINT_DIFF"), "积分差异");
  assert.equal(pointStatusLabel("MISSING_RATE"), "缺积分倍率");
  assert.equal(pointStatusLabel("ZERO_RATE"), "积分率为0");
  assert.equal(pointStatusLabel("ALLOCATION_IMBALANCE"), "付款分摊不平");
  assert.equal(pointStatusLabel("unknown"), "待复核");
});

test("marks degraded statuses as warning or danger", () => {
  assert.equal(pointStatusTone("OK"), "success");
  assert.equal(pointStatusTone("POINT_DIFF"), "danger");
  assert.equal(pointStatusTone("MISSING_RATE"), "warning");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node --import tsx client/src/lib/points-activity-analysis.test.mjs
```

Expected: fail because helper file does not exist.

- [ ] **Step 3: Create helper**

```typescript
export type PointStatus = "OK" | "POINT_DIFF" | "MISSING_RATE" | "ZERO_RATE" | "ALLOCATION_IMBALANCE";

export function pointStatusLabel(status?: string | null) {
  switch ((status || "").toUpperCase()) {
    case "OK":
      return "正常";
    case "POINT_DIFF":
      return "积分差异";
    case "MISSING_RATE":
      return "缺积分倍率";
    case "ZERO_RATE":
      return "积分率为0";
    case "ALLOCATION_IMBALANCE":
      return "付款分摊不平";
    default:
      return "待复核";
  }
}

export function pointStatusTone(status?: string | null) {
  switch ((status || "").toUpperCase()) {
    case "OK":
      return "success";
    case "POINT_DIFF":
    case "ZERO_RATE":
      return "danger";
    case "MISSING_RATE":
    case "ALLOCATION_IMBALANCE":
      return "warning";
    default:
      return "muted";
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
node --import tsx client/src/lib/points-activity-analysis.test.mjs
```

Expected: pass.

## Task 4: Frontend Page and Navigation

**Files:**
- Create: `client/src/pages/activity-analysis/points.tsx`
- Modify: `client/src/pages/main-dashboard.tsx`
- Modify: `client/src/lib/navigation-items.ts`

- [ ] **Step 1: Add route and navigation tests**

Add a small assertion to `client/src/components/navigation-sidebar.test.mjs`:

```javascript
assert.ok(
  (activityAnalysisGroup.subItems ?? []).some((item) => item.id === "points-activity-analysis"),
);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node --import tsx client/src/components/navigation-sidebar.test.mjs
```

Expected: fail because the navigation item is missing.

- [ ] **Step 3: Create page**

Create `client/src/pages/activity-analysis/points.tsx` with:

```tsx
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BadgeCheck, Calculator, ChevronRight, RefreshCw, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import { pointStatusLabel, pointStatusTone } from "@/lib/points-activity-analysis";

type Row = Record<string, string | number | null>;

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value || 0));
const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") qs.set(key, String(value));
  });
  const text = qs.toString();
  return text ? `?${text}` : "";
}

function localDate() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function PointsActivityAnalysisPage() {
  const [startDate, setStartDate] = useState(localDate);
  const [endDate, setEndDate] = useState(localDate);
  const [departmentCode, setDepartmentCode] = useState("");
  const [memberNo, setMemberNo] = useState("");
  const common = useMemo(() => ({ start_date: startDate, end_date: endDate, department_code: departmentCode }), [startDate, endDate, departmentCode]);
  const overview = useQuery<{ summary: Row; source_status: Row[] }>({
    queryKey: ["/api/activity-analysis/points/overview", common],
    queryFn: () => apiGet(`/api/activity-analysis/points/overview${buildQuery(common)}`),
  });
  const departments = useQuery<{ items: Row[] }>({
    queryKey: ["/api/activity-analysis/points/departments", common],
    queryFn: () => apiGet(`/api/activity-analysis/points/departments${buildQuery(common)}`),
  });
  const members = useQuery<{ items: Row[] }>({
    queryKey: ["/api/activity-analysis/points/members", common],
    queryFn: () => apiGet(`/api/activity-analysis/points/members${buildQuery(common)}`),
  });
  const tickets = useQuery<{ items: Row[] }>({
    queryKey: ["/api/activity-analysis/points/tickets", common, memberNo],
    queryFn: () => apiGet(`/api/activity-analysis/points/tickets${buildQuery({ ...common, member_no: memberNo, limit: 100 })}`),
  });

  const summary = overview.data?.summary || {};
  const refresh = () => {
    overview.refetch();
    departments.refetch();
    members.refetch();
    tickets.refetch();
  };

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">积分活动核对</h1>
          <p className="mt-1 text-sm text-muted-foreground">按部门权限核对黑钻 3 倍、黑金 2 倍和生日月多倍积分，缺规则时标记待复核。</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-4">
          <div><Label>开始日期</Label><Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div>
          <div><Label>结束日期</Label><Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div>
          <div><Label>部门编码</Label><Input value={departmentCode} onChange={(e) => setDepartmentCode(e.target.value)} placeholder="可选" /></div>
          <Button className="self-end" variant="outline" onClick={refresh}><RefreshCw className="mr-2 h-4 w-4" />刷新</Button>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card><CardContent className="p-4"><p className="text-sm text-muted-foreground">总销售额</p><p className="mt-2 text-2xl font-semibold">{money(summary.total_sales_amount)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-sm text-muted-foreground">积分基数</p><p className="mt-2 text-2xl font-semibold">{money(summary.point_basis_amount)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-sm text-muted-foreground">实际积分</p><p className="mt-2 text-2xl font-semibold">{number(summary.actual_point)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-sm text-muted-foreground">应送积分</p><p className="mt-2 text-2xl font-semibold">{number(summary.expected_point)}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-sm text-muted-foreground">异常行</p><p className="mt-2 text-2xl font-semibold text-amber-700">{number(summary.issue_count)}</p></CardContent></Card>
      </div>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Calculator className="h-5 w-5" />部门钻取</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <Table><TableHeader><TableRow><TableHead>部门</TableHead><TableHead>柜组</TableHead><TableHead className="text-right">销售额</TableHead><TableHead className="text-right">积分基数</TableHead><TableHead className="text-right">差异</TableHead></TableRow></TableHeader>
            <TableBody>{(departments.data?.items || []).map((row, index) => (
              <TableRow key={index} className="cursor-pointer" onClick={() => setDepartmentCode(String(row.department_code || ""))}>
                <TableCell>{row.department_name || row.department_code || "未归属"}</TableCell><TableCell>{row.group_name || row.group_code || "全部"}</TableCell><TableCell className="text-right">{money(row.total_sales_amount)}</TableCell><TableCell className="text-right">{money(row.point_basis_amount)}</TableCell><TableCell className="text-right">{number(row.point_diff)}</TableCell>
              </TableRow>
            ))}</TableBody>
          </Table>
        </CardContent>
      </Card>
      <div className="grid gap-4 xl:grid-cols-2">
        <Card><CardHeader><CardTitle>部门销售会员</CardTitle></CardHeader><CardContent className="overflow-x-auto">
          <Table><TableHeader><TableRow><TableHead>会员</TableHead><TableHead>等级</TableHead><TableHead className="text-right">销售额</TableHead><TableHead className="text-right">实际积分</TableHead><TableHead className="text-right">差异</TableHead></TableRow></TableHeader>
            <TableBody>{(members.data?.items || []).map((row, index) => (
              <TableRow key={index} className="cursor-pointer" onClick={() => setMemberNo(String(row.member_no || ""))}>
                <TableCell>{row.member_no || "未刷卡"}</TableCell><TableCell>{row.customer_level || "—"}</TableCell><TableCell className="text-right">{money(row.total_sales_amount)}</TableCell><TableCell className="text-right">{number(row.actual_point)}</TableCell><TableCell className="text-right">{number(row.point_diff)}</TableCell>
              </TableRow>
            ))}</TableBody>
          </Table>
        </CardContent></Card>
        <Card><CardHeader><CardTitle>小票明细</CardTitle></CardHeader><CardContent className="overflow-x-auto">
          <div className="mb-3 flex gap-2"><Input value={memberNo} onChange={(e) => setMemberNo(e.target.value)} placeholder="会员号筛选" /><Button variant="outline"><Search className="h-4 w-4" /></Button></div>
          <Table><TableHeader><TableRow><TableHead>小票号</TableHead><TableHead className="text-right">销售额</TableHead><TableHead className="text-right">积分基数</TableHead><TableHead className="text-right">实际/应送</TableHead><TableHead>状态</TableHead></TableRow></TableHeader>
            <TableBody>{(tickets.data?.items || []).map((row, index) => (
              <TableRow key={index}>
                <TableCell>{row.billno}</TableCell><TableCell className="text-right">{money(row.total_sales_amount)}</TableCell><TableCell className="text-right">{money(row.point_basis_amount)}</TableCell><TableCell className="text-right">{number(row.actual_point)} / {number(row.expected_point)}</TableCell><TableCell><Badge variant={pointStatusTone(String(row.status)) === "danger" ? "destructive" : "secondary"}>{pointStatusLabel(String(row.status))}</Badge></TableCell>
              </TableRow>
            ))}</TableBody>
          </Table>
        </CardContent></Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Wire page into dashboard and navigation**

Import `PointsActivityAnalysisPage` in `client/src/pages/main-dashboard.tsx`, add label `"points-activity-analysis": "积分活动核对"`, and add switch case:

```tsx
case "points-activity-analysis":
  return <PointsActivityAnalysisPage />;
```

Add the navigation item under the activity-analysis group:

```ts
{ id: "points-activity-analysis", name: "积分活动核对", icon: Calculator }
```

- [ ] **Step 5: Run frontend tests**

Run:

```bash
node --import tsx client/src/components/navigation-sidebar.test.mjs
node --import tsx client/src/lib/points-activity-analysis.test.mjs
```

Expected: both pass.

## Task 5: End-to-End Verification

**Files:**
- No new files.

- [ ] **Step 1: Run backend focused tests**

```bash
python3 test/test_activity_points_rule_sql.py
python3 test/test_point_rule_tables_migration.py
```

Expected: both pass.

- [ ] **Step 2: Run frontend focused tests**

```bash
node --import tsx client/src/components/navigation-sidebar.test.mjs
node --import tsx client/src/lib/points-activity-analysis.test.mjs
```

Expected: both pass.

- [ ] **Step 3: Run type/build check**

Use the repo's existing build command from `package.json`. If the script is `check`, run:

```bash
npm run check
```

Expected: exit code 0.

- [ ] **Step 4: Manual database sanity query**

Run:

```bash
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("python_app").resolve()))
from sqlalchemy import create_engine, text
from models.database import DATABASE_URL
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    for table in ("card_paymoderule", "rulejfrate", "sellpaygoods"):
        row = conn.execute(text(f"SELECT COUNT(*) AS c FROM {table}")).mappings().one()
        print(table, row["c"])
PY
```

Expected: non-zero counts for all three tables.

## Self-Review

- Spec coverage: plan covers ERP rule dependencies, department-scoped visibility, member and ticket drilldown, rule-match statuses, and degraded calculation states.
- Placeholder scan: no placeholder tasks remain; all tests and commands have concrete paths.
- Type consistency: backend status values match frontend helper status values.
