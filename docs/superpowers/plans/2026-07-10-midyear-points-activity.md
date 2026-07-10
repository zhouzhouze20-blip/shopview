# Midyear Points Activity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the points audit page to `中心年中庆活动`, enforce the `2026-07-09` activity boundary, remove the duplicate frontend query, and make the permission-scoped dashboard complete well inside its 60-second safety timeout.

**Architecture:** Preserve the existing module ID, permission code, and API paths. The frontend consumes the dashboard response as the single source for filters and results; the backend normalizes dates before touching business tables, materializes one permission-scoped payment/goods set, limits all large-table work to relevant bills, and reads source-table status from PostgreSQL metadata instead of `COUNT(*)` scans.

**Tech Stack:** React 18, TypeScript, TanStack Query, Node test runner, FastAPI, SQLAlchemy, PostgreSQL, Python unittest, Nginx.

---

## Dirty-worktree safety

The implementation targets already contain user-owned uncommitted work:

- `M client/src/pages/main-dashboard.tsx`
- `M python_app/routers/activity_analysis.py`
- `?? client/src/lib/navigation-items.ts`
- `?? client/src/lib/points-activity-analysis.ts`
- `?? client/src/lib/points-activity-analysis.test.mjs`
- `?? client/src/pages/activity-analysis/points.tsx`
- `?? client/src/components/navigation-sidebar.test.mjs`
- `?? test/test_activity_points_rule_sql.py`

Do not use `git add -A`, do not reset files, and do not commit implementation files during this run. Each task ends with a focused diff checkpoint instead of a commit so unrelated work is preserved. The design and plan documents may be committed separately because they do not overlap existing work.

## File map

- `client/src/lib/navigation-items.ts`: left-navigation label.
- `client/src/pages/main-dashboard.tsx`: workspace-tab label in `MODULE_LABELS`.
- `client/src/lib/points-activity-analysis.ts`: activity start constant, default-date helper, and query-state messages.
- `client/src/pages/activity-analysis/points.tsx`: title, date inputs, one dashboard query, department options, refresh, and error-content gating.
- `client/src/components/navigation-sidebar.test.mjs`: navigation and tab-label contract tests.
- `client/src/lib/points-activity-analysis.test.mjs`: date, message, empty-state, and page-source contract tests.
- `python_app/routers/activity_analysis.py`: date normalization, empty responses, local timeout, metadata-only source status, optimized CTEs, and all `/points/*` endpoints.
- `test/test_activity_points_rule_sql.py`: backend date, timeout, SQL-shape, source-status, and Nginx contract tests.
- `config/nginx.conf`: route-specific points API read timeout.

### Task 1: Rename and simplify the frontend page

**Files:**
- Modify: `client/src/components/navigation-sidebar.test.mjs`
- Modify: `client/src/lib/points-activity-analysis.test.mjs`
- Modify: `client/src/lib/navigation-items.ts`
- Modify: `client/src/pages/main-dashboard.tsx`
- Modify: `client/src/lib/points-activity-analysis.ts`
- Modify: `client/src/pages/activity-analysis/points.tsx`

- [ ] **Step 1: Add failing navigation, tab, date, query, and message tests**

Add `readFileSync` to `client/src/components/navigation-sidebar.test.mjs` and append:

```js
test("names the points module as the midyear activity without changing its id", () => {
  const pointsActivity = findItem(navigationItems, "points-activity-analysis");
  assert.ok(pointsActivity);
  assert.equal(pointsActivity.id, "points-activity-analysis");
  assert.equal(pointsActivity.name, "中心年中庆活动");

  const dashboardSource = readFileSync(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8");
  assert.match(dashboardSource, /"points-activity-analysis":\s*"中心年中庆活动"/);
});
```

Extend the points helper test import with `POINTS_ACTIVITY_START_DATE` and `pointsActivityDefaultEndDate`. Replace the current generic loading/error test and append:

```js
test("reports distinct midyear activity query states", () => {
  const emptyDashboard = { departments: [], groups: [], members: [], tickets: [] };

  assert.equal(pointAnalysisQueryMessage({ isLoading: true }), "正在加载中心年中庆活动数据...");
  assert.equal(
    pointAnalysisQueryMessage({ isError: true, error: new Error("API请求失败: 403 - 无功能权限") }),
    "无中心年中庆活动查看权限",
  );
  assert.equal(
    pointAnalysisQueryMessage({ isError: true, error: new Error("API请求失败: 504 - query timeout") }),
    "中心年中庆活动数据查询超时，请缩短日期范围后重试",
  );
  assert.equal(
    pointAnalysisQueryMessage({ isError: true, error: new Error("API请求失败: 500 - database error") }),
    "中心年中庆活动数据加载失败，请稍后重试或检查后端服务",
  );
  assert.equal(
    pointAnalysisQueryMessage({ isLoading: false, isError: false, data: emptyDashboard }),
    "当前日期和权限范围内暂无数据",
  );
  assert.equal(
    pointAnalysisQueryMessage({
      isLoading: false,
      isError: false,
      data: { ...emptyDashboard, departments: [{ department_name: "中心一部" }] },
    }),
    null,
  );
});

test("uses the July 9 activity boundary", () => {
  assert.equal(POINTS_ACTIVITY_START_DATE, "2026-07-09");
  assert.equal(pointsActivityDefaultEndDate("2026-07-10"), "2026-07-10");
  assert.equal(pointsActivityDefaultEndDate("2026-07-08"), "2026-07-09");
});

test("points page uses one dashboard query for filters and results", () => {
  const page = readFileSync(new URL("../pages/activity-analysis/points.tsx", import.meta.url), "utf8");

  assert.match(page, />中心年中庆活动<\/h1>/);
  assert.match(page, /department_options:\s*Row\[\]/);
  assert.match(page, /dashboard\.data\?\.department_options/);
  assert.match(page, /useState\(POINTS_ACTIVITY_START_DATE\)/);
  assert.equal(page.match(/min=\{POINTS_ACTIVITY_START_DATE\}/g)?.length, 2);
  assert.match(page, /\/api\/activity-analysis\/points\/dashboard/);
  assert.doesNotMatch(page, /\/api\/activity-analysis\/points\/department-options/);
  assert.doesNotMatch(page, /departmentOptions\.refetch/);
  assert.equal(page.match(/useQuery</g)?.length, 1);
});
```

- [ ] **Step 2: Run the frontend tests and verify RED**

Run:

```bash
node --experimental-strip-types --test client/src/lib/points-activity-analysis.test.mjs client/src/components/navigation-sidebar.test.mjs
```

Expected: FAIL because the visible label is still `积分活动核对`, the start/date helpers do not exist, error states are generic, and the page still requests department-options.

- [ ] **Step 3: Implement the shared frontend date and message contract**

In `client/src/lib/points-activity-analysis.ts`, add:

```ts
export const POINTS_ACTIVITY_START_DATE = "2026-07-09";

export function pointsActivityDefaultEndDate(today: string) {
  return today < POINTS_ACTIVITY_START_DATE ? POINTS_ACTIVITY_START_DATE : today;
}

export type PointDashboardStateData = {
  departments?: unknown[];
  groups?: unknown[];
  members?: unknown[];
  tickets?: unknown[];
};

export type PointAnalysisQueryState = {
  isLoading?: boolean;
  isFetching?: boolean;
  isError?: boolean;
  error?: unknown;
  data?: PointDashboardStateData | null;
};

function pointQueryErrorText(error: unknown) {
  return error instanceof Error ? error.message : String(error || "");
}

export function pointAnalysisQueryMessage(state: PointAnalysisQueryState) {
  if (state.isLoading || state.isFetching) return "正在加载中心年中庆活动数据...";
  if (state.isError) {
    const errorText = pointQueryErrorText(state.error);
    if (/API请求失败:\s*403\b/.test(errorText)) return "无中心年中庆活动查看权限";
    if (/API请求失败:\s*504\b/.test(errorText) || /查询超时|statement timeout/i.test(errorText)) {
      return "中心年中庆活动数据查询超时，请缩短日期范围后重试";
    }
    return "中心年中庆活动数据加载失败，请稍后重试或检查后端服务";
  }
  if (state.data) {
    const collections = [state.data.departments, state.data.groups, state.data.members, state.data.tickets];
    if (collections.every((items) => !items?.length)) return "当前日期和权限范围内暂无数据";
  }
  return null;
}
```

- [ ] **Step 4: Rename all three visible surfaces without changing internal identifiers**

```ts
// client/src/lib/navigation-items.ts
{ id: "points-activity-analysis", name: "中心年中庆活动", icon: Calculator },

// client/src/pages/main-dashboard.tsx, MODULE_LABELS
"points-activity-analysis": "中心年中庆活动",

// client/src/pages/activity-analysis/points.tsx
<h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">中心年中庆活动</h1>
```

Do not change `points-activity-analysis`, `activity_analysis.points.view`, or `/api/activity-analysis/points/dashboard`.

- [ ] **Step 5: Collapse `points.tsx` to one dashboard query**

Update the response type and initial dates:

```ts
type DashboardResponse = {
  summary: Row;
  department_options: Row[];
  departments: Row[];
  groups: Row[];
  members: Row[];
  tickets: Row[];
};

const [startDate, setStartDate] = useState(POINTS_ACTIVITY_START_DATE);
const [endDate, setEndDate] = useState(() => pointsActivityDefaultEndDate(localDate()));
```

Delete `DepartmentOptionsResponse` and its `useQuery`. Define the dashboard query before the option-validation effect, then use:

```ts
useEffect(() => {
  const options = dashboard.data?.department_options || [];
  if (!options.length) {
    if (departmentName !== DEPARTMENT_SCOPE_ALL_VALUE) setDepartmentName(DEPARTMENT_SCOPE_ALL_VALUE);
    return;
  }
  const optionNames = new Set(options.map((option) => String(option.department_name || "")));
  if (departmentName !== DEPARTMENT_SCOPE_ALL_VALUE && !optionNames.has(departmentName)) {
    setDepartmentName(DEPARTMENT_SCOPE_ALL_VALUE);
  }
}, [departmentName, dashboard.data?.department_options]);

const queryMessage = pointAnalysisQueryMessage(dashboard);
const isPageLoading = dashboard.isLoading;
const showDashboardContent = !dashboard.isError;
const refresh = () => dashboard.refetch();
```

Render dropdown options from `(dashboard.data?.department_options || [])`. Add `min={POINTS_ACTIVITY_START_DATE}` to both date inputs. Move the query-message card before the summary strip and wrap the summary plus detail cards in `showDashboardContent ? <>...</> : null` so an HTTP error cannot appear as a successful all-zero dashboard.

- [ ] **Step 6: Run frontend tests and type checking; verify GREEN**

```bash
node --experimental-strip-types --test client/src/lib/points-activity-analysis.test.mjs client/src/components/navigation-sidebar.test.mjs
npm run check
```

Expected: all focused tests PASS and TypeScript exits 0.

- [ ] **Step 7: Review the focused frontend diff**

```bash
git diff --check -- client/src/lib/navigation-items.ts client/src/pages/main-dashboard.tsx client/src/lib/points-activity-analysis.ts client/src/pages/activity-analysis/points.tsx client/src/components/navigation-sidebar.test.mjs client/src/lib/points-activity-analysis.test.mjs
```

Expected: no whitespace errors; only the approved page contract is changed on top of the pre-existing work.

### Task 2: Enforce the backend activity boundary and local timeout

**Files:**
- Modify: `test/test_activity_points_rule_sql.py`
- Modify: `python_app/routers/activity_analysis.py`

- [ ] **Step 1: Add failing tests for date normalization, early empty results, and timeout mapping**

Add to `ActivityPointsRouterContractTest`:

```python
def test_points_date_range_clamps_to_activity_start(self):
    from routers.activity_analysis import _points_effective_date_range

    self.assertEqual(
        _points_effective_date_range("2026-07-01", "2026-07-10"),
        ("2026-07-09", "2026-07-11"),
    )
    self.assertIsNone(_points_effective_date_range("2026-07-01", "2026-07-08"))

def test_points_date_range_rejects_reversed_or_invalid_dates(self):
    from fastapi import HTTPException
    from routers.activity_analysis import _points_effective_date_range

    with self.assertRaises(HTTPException) as reversed_error:
        _points_effective_date_range("2026-07-10", "2026-07-09")
    self.assertEqual(reversed_error.exception.status_code, 400)

    with self.assertRaises(HTTPException) as invalid_error:
        _points_effective_date_range("2026/07/09", "2026-07-10")
    self.assertEqual(invalid_error.exception.status_code, 400)

def test_empty_points_dashboard_keeps_the_response_contract(self):
    from routers.activity_analysis import _empty_points_dashboard_response

    response = _empty_points_dashboard_response()
    self.assertEqual(response["summary"], {})
    for key in ("department_options", "departments", "groups", "members", "tickets", "source_status"):
        self.assertEqual(response[key], [])

def test_pre_activity_dashboard_returns_before_business_table_checks(self):
    import asyncio
    from unittest.mock import patch
    from routers import activity_analysis as router

    with (
        patch.object(router, "require_permission"),
        patch.object(router, "_ensure_required_tables", side_effect=AssertionError("business tables inspected")),
        patch.object(router, "_ensure_point_rule_tables", side_effect=AssertionError("point tables inspected")),
    ):
        response = asyncio.run(
            router.points_dashboard(
                start_date="2026-07-01",
                end_date="2026-07-08",
                department_name=None,
                group_code=None,
                member_no=None,
                keyword=None,
                limit=200,
                db=object(),
                current_user=object(),
            )
        )

    self.assertEqual(response, router._empty_points_dashboard_response())

def test_points_query_timeout_is_local_and_maps_to_504(self):
    from fastapi import HTTPException
    from sqlalchemy.exc import OperationalError
    from routers.activity_analysis import _execute_points_query

    class FakeDb:
        def __init__(self):
            self.statements = []
            self.rolled_back = False

        def execute(self, statement, params=None):
            self.statements.append(str(statement))

        def rollback(self):
            self.rolled_back = True

    db = FakeDb()
    timeout = OperationalError("SELECT", {}, RuntimeError("canceling statement due to statement timeout"))

    with self.assertRaises(HTTPException) as raised:
        _execute_points_query(db, lambda: (_ for _ in ()).throw(timeout))

    self.assertEqual(raised.exception.status_code, 504)
    self.assertTrue(db.rolled_back)
    self.assertTrue(any("statement_timeout = '60s'" in statement for statement in db.statements))
```

- [ ] **Step 2: Run backend tests and verify RED**

```bash
PYTHONPATH=python_app .venv/bin/python test/test_activity_points_rule_sql.py -v
```

Expected: FAIL because `_points_effective_date_range`, `_empty_points_dashboard_response`, and `_execute_points_query` do not exist.

- [ ] **Step 3: Implement the date, empty-response, and timeout helpers**

Add imports and helpers near the points constants in `python_app/routers/activity_analysis.py`:

```python
from datetime import date, timedelta
from typing import Any, Callable, Iterable

from sqlalchemy.exc import OperationalError

POINTS_ACTIVITY_START_DATE = date(2026, 7, 9)
POINTS_QUERY_TIMEOUT_SECONDS = 60


def _points_effective_date_range(start_date: str, end_date: str) -> tuple[str, str] | None:
    try:
        requested_start = date.fromisoformat(start_date)
        requested_end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="日期必须为 YYYY-MM-DD") from exc
    if requested_start > requested_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始日期不能晚于结束日期")
    if requested_end < POINTS_ACTIVITY_START_DATE:
        return None
    effective_start = max(requested_start, POINTS_ACTIVITY_START_DATE)
    return effective_start.isoformat(), (requested_end + timedelta(days=1)).isoformat()


def _empty_points_dashboard_response() -> dict[str, Any]:
    return {
        "summary": {},
        "department_options": [],
        "departments": [],
        "groups": [],
        "members": [],
        "tickets": [],
        "source_status": [],
    }


def _is_points_statement_timeout(exc: OperationalError) -> bool:
    return "statement timeout" in str(exc).lower() or "querycanceled" in str(exc).lower()


def _execute_points_query(db: Session, loader: Callable[[], Any]) -> Any:
    db.execute(text(f"SET LOCAL statement_timeout = '{POINTS_QUERY_TIMEOUT_SECONDS}s'"))
    try:
        return loader()
    except OperationalError as exc:
        if not _is_points_statement_timeout(exc):
            raise
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="中心年中庆活动数据查询超时",
        ) from exc
```

- [ ] **Step 4: Apply the date boundary to every `/points/*` endpoint**

Immediately after `require_permission` in `points_department_options`, `points_dashboard`, `points_overview`, `points_departments`, `points_members`, and `points_tickets`, call `_points_effective_date_range(start_date, end_date)`. If it returns `None`, return the endpoint-specific response below. Otherwise unpack it:

```python
effective_range = _points_effective_date_range(start_date, end_date)
effective_start_date, effective_end_exclusive = effective_range
```

Use these exact early responses:

```python
# department-options
{"items": []}

# dashboard
_empty_points_dashboard_response()

# overview
{"summary": {}, "source_status": []}

# departments, members, tickets
{"items": [], "source_status": []}
```

Perform this check before `_ensure_required_tables` and `_ensure_point_rule_tables`, so a wholly pre-activity interval does not inspect business source tables. For non-empty ranges, use:

```python
params = {
    "start_date": effective_start_date,
    "end_exclusive": effective_end_exclusive,
    # keep each endpoint's existing limit/filter params
}
```

Run each `_one` or `_rows` points query through `_execute_points_query(db, lambda: ...)`. Do not wrap `require_permission`; a real 403 must remain a 403.

- [ ] **Step 5: Run backend tests and verify GREEN**

```bash
PYTHONPATH=python_app .venv/bin/python test/test_activity_points_rule_sql.py -v
```

Expected: all date and timeout tests PASS.

- [ ] **Step 6: Review the focused backend helper diff**

```bash
git diff --check -- python_app/routers/activity_analysis.py test/test_activity_points_rule_sql.py
```

Expected: helper changes preserve permission ordering and do not touch roles or policies.

### Task 3: Rewrite the dashboard SQL around relevant bills

**Files:**
- Modify: `test/test_activity_points_rule_sql.py`
- Modify: `python_app/routers/activity_analysis.py`

- [ ] **Step 1: Replace old SQL-shape expectations with failing optimization tests**

Delete `test_points_base_sql_allows_early_salehead_filter`, because the optimized base SQL owns the date predicate instead of accepting arbitrary injected date SQL. Replace the old `point_bill_groups`/raw `salegoodslist` assertions in `test_points_sales_amount_uses_salegoodslist_revenue_not_payment_allocation`, `test_points_dashboard_filters_by_department_name`, and `test_points_dashboard_level_sales_source_groups_by_group_code` with the optimized CTE assertions below; keep their existing revenue-source and member-count business assertions.

```python
def test_points_base_sql_filters_early_and_limits_large_tables_to_relevant_bills(self):
    from routers.activity_analysis import _points_base_sql

    sql = _points_base_sql("AND scope_marker = 1")
    self.assertIn("scoped_payment_goods AS MATERIALIZED", sql)
    self.assertIn("h.rqsj >= CAST(:start_date AS date)", sql)
    self.assertIn("h.rqsj < CAST(:end_exclusive AS date)", sql)
    self.assertNotIn("h.rqsj::date BETWEEN", sql)
    self.assertIn("AND scope_marker = 1", sql)
    self.assertIn("scoped_bill_groups AS MATERIALIZED", sql)
    self.assertIn("accounting_sales_by_group AS MATERIALIZED", sql)
    self.assertIn("JOIN point_bills pb", sql)
    self.assertIn("ON op.order_id = pb.billno::text", sql)
    self.assertEqual(sql.count("JOIN salegoodslist s"), 1)
    self.assertIn("FROM scoped_payment_goods psg", sql)

def test_point_source_status_uses_catalog_estimates_not_full_counts(self):
    import inspect
    from routers.activity_analysis import _point_rule_source_status

    source = inspect.getsource(_point_rule_source_status)
    self.assertIn("reltuples", source)
    self.assertNotIn("COUNT(*)", source)

def test_points_dashboard_reuses_scoped_rows_for_level_sales(self):
    router_file = Path(__file__).resolve().parents[1] / "python_app" / "routers" / "activity_analysis.py"
    source = router_file.read_text(encoding="utf-8")
    match = re.search(r"level_sales_source AS MATERIALIZED \((.*?)level_sales_rows AS MATERIALIZED", source, re.S)

    self.assertIsNotNone(match)
    level_sql = match.group(1)
    self.assertIn("FROM scoped_payment_goods", level_sql)
    self.assertNotIn("JOIN salehead", level_sql)
    self.assertNotIn("JOIN salegoodslist", level_sql)
```

- [ ] **Step 2: Run backend tests and verify RED**

```bash
PYTHONPATH=python_app .venv/bin/python test/test_activity_points_rule_sql.py -v
```

Expected: FAIL because the old SQL aggregates all `order_point`, performs repeated base joins, uses casted date predicates, and executes exact source-table counts.

- [ ] **Step 3: Replace the expensive top-level CTE flow**

Keep the existing `manaframe_groups`, `latest_rate`, point formulas, and final response queries. Replace the bill/payment/sales CTEs inside `_points_base_sql` with:

```sql
scoped_payment_goods AS MATERIALIZED (
  SELECT
    h.billno,
    h.rqsj::date AS sale_date,
    h.rqsj AS sale_time,
    h.mkt::varchar AS market_code,
    COALESCE(NULLIF(TRIM(BOTH FROM h.hykh), ''), '') AS member_no,
    TRIM(BOTH FROM COALESCE(h.custtype, '')) AS customer_level,
    g.rowno AS goods_rowno,
    g.code AS goods_code,
    COALESCE(NULLIF(g.name, ''), g.code) AS goods_name,
    TRIM(BOTH FROM COALESCE(g.gz, '')) AS group_code,
    cg.group_name,
    cg.department_code,
    cg.department_name,
    COALESCE(cg.store_id, h.mkt::varchar) AS store_id,
    spg.spgrowno,
    spg.spgpmcode,
    spg.spgpayerid,
    COALESCE(spg.spgmoney, 0) AS payment_amount,
    COALESCE(spg.spggdmoney, 0) AS payment_alloc_amount
  FROM salehead h
  JOIN sellpaygoods spg ON spg.spgbillno = h.billno
  JOIN salegoods g
    ON g.billno = spg.spgbillno
   AND g.rowno::numeric = spg.spggdrow
  LEFT JOIN manaframe_groups cg
    ON UPPER(TRIM(COALESCE(cg.group_code, ''))) = UPPER(TRIM(COALESCE(g.gz, '')))
  WHERE COALESCE(h.djlb, '') NOT IN ('V', 'W', 'Y', 'Z')
    AND h.mkt::text = '601'
    AND h.rqsj >= CAST(:start_date AS date)
    AND h.rqsj < CAST(:end_exclusive AS date)
    {_sales_department_exclusion_sql("cg")}
    {scope_filter_sql}
),
scoped_bill_groups AS MATERIALIZED (
  SELECT DISTINCT billno, market_code, sale_date, group_code
  FROM scoped_payment_goods
),
accounting_sales_by_group AS MATERIALIZED (
  SELECT
    s.sglbillno AS billno,
    s.sglmarket::varchar AS market_code,
    s.sglhsrq::date AS sale_date,
    TRIM(BOTH FROM COALESCE(s.sglmfid, '')) AS group_code,
    SUM(COALESCE(s.sglxssr, 0)) AS sales_amount
  FROM salegoodslist s
  JOIN scoped_bill_groups sbg
    ON sbg.billno = s.sglbillno
   AND sbg.market_code = s.sglmarket::varchar
   AND sbg.sale_date = s.sglhsrq::date
   AND UPPER(TRIM(COALESCE(sbg.group_code, ''))) = UPPER(TRIM(COALESCE(s.sglmfid, '')))
  GROUP BY 1, 2, 3, 4
),
point_bills AS MATERIALIZED (
  SELECT DISTINCT billno
  FROM scoped_payment_goods
  WHERE customer_level IN ('03', '04')
),
point_by_bill AS (
  SELECT
    op.order_id AS billno,
    SUM(COALESCE(op.point, 0)) AS actual_point,
    SUM(CASE WHEN COALESCE(op.point_type, '') IN ('消费加积分', '消费获得积分') THEN COALESCE(op.point, 0) ELSE 0 END) AS consumption_point,
    SUM(CASE WHEN COALESCE(op.point_type, '') LIKE '生日月%' THEN COALESCE(op.point, 0) ELSE 0 END) AS birthday_month_point
  FROM order_point op
  JOIN point_bills pb ON op.order_id = pb.billno::text
  GROUP BY op.order_id
),
pay_line_balance AS (
  SELECT
    billno AS spgbillno,
    spgrowno,
    spgpmcode,
    MAX(payment_amount) AS payment_amount,
    SUM(payment_alloc_amount) AS allocated_amount,
    SUM(payment_alloc_amount) - MAX(payment_amount) AS allocation_diff_amount
  FROM scoped_payment_goods
  WHERE customer_level IN ('03', '04')
  GROUP BY billno, spgrowno, spgpmcode
)
```

Build `spg_rows` directly from the scoped materialization; do not rejoin `salehead`, `sellpaygoods`, `salegoods`, or `manaframe`:

```sql
spg_rows AS (
  SELECT
    psg.billno,
    psg.sale_date,
    psg.sale_time,
    psg.market_code,
    psg.member_no,
    psg.customer_level,
    psg.goods_rowno,
    psg.goods_code,
    psg.goods_name,
    psg.group_code,
    psg.group_name,
    psg.department_code,
    psg.department_name,
    psg.store_id,
    psg.spgrowno,
    psg.spgpmcode,
    psg.spgpayerid,
    COALESCE(sgl.sales_amount, 0) AS accounting_sales_amount,
    psg.payment_alloc_amount,
    COALESCE(plb.allocation_diff_amount, 0) AS allocation_diff_amount,
    lr.jfrate,
    CASE
      WHEN cpr.fkcode IS NOT NULL THEN 0
      WHEN psg.spgpmcode IN ('0500', '0514', '0580') THEN COALESCE(
        NULLIF(TRIM(BOTH FROM tm.tqmisjf), '')::numeric * COALESCE(tm.tqmevrate, 1),
        NULLIF(TRIM(BOTH FROM tq.tqisjf), '')::numeric * COALESCE(tq.tqrevrate, 1),
        0
      )
      WHEN psg.spgpmcode = '0400' THEN 0.5
      ELSE COALESCE(pm.pmrevrate, 1)
    END AS point_basis_rate
  FROM scoped_payment_goods psg
  LEFT JOIN accounting_sales_by_group sgl
    ON sgl.billno = psg.billno
   AND sgl.market_code = psg.market_code
   AND sgl.sale_date = psg.sale_date
   AND UPPER(TRIM(COALESCE(sgl.group_code, ''))) = UPPER(TRIM(COALESCE(psg.group_code, '')))
  LEFT JOIN paymode pm
    ON UPPER(TRIM(COALESCE(pm.pmcode, ''))) = UPPER(TRIM(COALESCE(psg.spgpmcode, '')))
  LEFT JOIN card_paymoderule cpr
    ON UPPER(TRIM(COALESCE(cpr.fkcode, ''))) = UPPER(TRIM(COALESCE(psg.spgpmcode, '')))
  LEFT JOIN tktqtypemkt tm
    ON tm.tqmmkt::text = psg.market_code
   AND UPPER(TRIM(COALESCE(tm.tqmcode, ''))) = UPPER(TRIM(COALESCE(SUBSTRING(psg.spgpayerid FROM 1 FOR 1), '')))
  LEFT JOIN tktqtype tq
    ON UPPER(TRIM(COALESCE(tq.tqcode, ''))) = UPPER(TRIM(COALESCE(SUBSTRING(psg.spgpayerid FROM 1 FOR 1), '')))
  LEFT JOIN latest_rate lr
    ON UPPER(TRIM(COALESCE(lr.jfmfid, ''))) = UPPER(TRIM(COALESCE(psg.group_code, '')))
  LEFT JOIN pay_line_balance plb
    ON plb.spgbillno = psg.billno
   AND plb.spgrowno = psg.spgrowno
   AND plb.spgpmcode = psg.spgpmcode
  WHERE psg.customer_level IN ('03', '04')
)
```

- [ ] **Step 4: Reuse scoped rows for the sales-level summary**

Remove `level_extra_filters`. Build:

```sql
level_sales_source AS MATERIALIZED (
  SELECT customer_level, billno, market_code, sale_date, group_code, member_no
  FROM scoped_payment_goods
  WHERE 1=1
    {" ".join(extra_filters)}
  GROUP BY 1, 2, 3, 4, 5, 6
),
level_sales_rows AS MATERIALIZED (
  SELECT
    src.customer_level,
    COALESCE(SUM(s.sales_amount), 0) AS total_sales_amount,
    CASE
      WHEN src.customer_level IN ('01', '02', '03', '04') THEN COUNT(DISTINCT NULLIF(src.member_no, ''))
      ELSE COUNT(DISTINCT src.billno)
    END AS person_count
  FROM level_sales_source src
  JOIN accounting_sales_by_group s
    ON s.billno = src.billno
   AND s.market_code = src.market_code
   AND s.sale_date = src.sale_date
   AND UPPER(TRIM(COALESCE(s.group_code, ''))) = UPPER(TRIM(COALESCE(src.group_code, '')))
  GROUP BY src.customer_level
)
```

Remove redundant outer `sale_date BETWEEN` filters because `_points_base_sql` now applies the effective range before large-table joins.

- [ ] **Step 5: Replace source-table `COUNT(*)` with catalog estimates**

```python
def _point_rule_source_status(db: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table_name in (*point_rule_source_tables(), "salehead", "salegoods", "manaframe"):
        qualified_name = f"public.{table_name}"
        row = db.execute(
            text(
                """
                SELECT
                  to_regclass(:qualified_name) IS NOT NULL AS exists,
                  COALESCE(c.reltuples, 0)::bigint AS estimated_row_count
                FROM (SELECT 1) anchor
                LEFT JOIN pg_class c ON c.oid = to_regclass(:qualified_name)
                """
            ),
            {"qualified_name": qualified_name},
        ).mappings().first()
        rows.append(
            {
                "table_name": table_name,
                "exists": bool(row and row.get("exists")),
                "row_count": int(row.get("estimated_row_count") or 0) if row else 0,
            }
        )
    return rows
```

Keep the response key `row_count` for compatibility; it becomes a diagnostic estimate.

- [ ] **Step 6: Run backend tests and verify GREEN**

```bash
PYTHONPATH=python_app .venv/bin/python test/test_activity_points_rule_sql.py -v
python3 -m py_compile python_app/routers/activity_analysis.py
```

Expected: all tests PASS and the router compiles.

- [ ] **Step 7: Review the focused SQL diff**

```bash
git diff --check -- python_app/routers/activity_analysis.py test/test_activity_points_rule_sql.py
```

Expected: existing point formulas and response fields remain while duplicate large-table scans are removed.

### Task 4: Add a route-specific Nginx safety timeout

**Files:**
- Modify: `test/test_activity_points_rule_sql.py`
- Modify: `config/nginx.conf`

- [ ] **Step 1: Add a failing Nginx scoping test**

```python
def test_points_nginx_timeout_is_60_seconds_without_changing_general_api_timeout(self):
    config = (Path(__file__).resolve().parents[1] / "config" / "nginx.conf").read_text(encoding="utf-8")
    points_location = re.search(r"location \^~ /api/activity-analysis/points/ \{(.*?)\n\s*\}", config, re.S)
    general_location = re.search(r"location /api/ \{(.*?)\n\s*\}", config, re.S)

    self.assertIsNotNone(points_location)
    self.assertIn("proxy_read_timeout 60s;", points_location.group(1))
    self.assertIsNotNone(general_location)
    self.assertIn("proxy_read_timeout 30s;", general_location.group(1))
```

- [ ] **Step 2: Run the backend test and verify RED**

```bash
PYTHONPATH=python_app .venv/bin/python test/test_activity_points_rule_sql.py -v
```

Expected: FAIL because no points-specific Nginx location exists.

- [ ] **Step 3: Add the points-specific location before `location /api/`**

```nginx
        location ^~ /api/activity-analysis/points/ {
            proxy_pass http://shopview_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 60s;
        }
```

Keep the existing general `/api/` block at 30 seconds.

- [ ] **Step 4: Run the Nginx contract test and verify GREEN**

```bash
PYTHONPATH=python_app .venv/bin/python test/test_activity_points_rule_sql.py -v
```

Expected: all backend tests PASS.

- [ ] **Step 5: Review the focused operations diff**

```bash
git diff --check -- config/nginx.conf test/test_activity_points_rule_sql.py
```

Expected: only the points path receives a 60-second read timeout.

### Task 5: Verify behavior, build integrity, and live performance

**Files:**
- Verify only; no new files.

- [ ] **Step 1: Run all focused automated tests**

```bash
node --experimental-strip-types --test client/src/lib/points-activity-analysis.test.mjs client/src/components/navigation-sidebar.test.mjs
PYTHONPATH=python_app .venv/bin/python test/test_activity_points_rule_sql.py -v
```

Expected: all focused frontend and backend tests PASS.

- [ ] **Step 2: Run full static/build verification**

```bash
npm run check
npm run build
python3 -m py_compile python_app/routers/activity_analysis.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 3: Run the read-only live database benchmark for 王薇 and 白海燕**

```bash
.venv/bin/python -c "exec(\"\"\"import asyncio, sys, time\nsys.path.insert(0, 'python_app')\nfrom models.database import SessionLocal\nfrom models.models import User\nfrom routers.activity_analysis import points_dashboard\nfor name in ['王薇', '白海燕']:\n    db = SessionLocal()\n    user = db.query(User).filter(User.real_name == name).one()\n    started = time.perf_counter()\n    result = asyncio.run(points_dashboard(start_date='2026-07-09', end_date='2026-07-10', department_name=None, group_code=None, member_no=None, keyword=None, limit=200, db=db, current_user=user))\n    elapsed = time.perf_counter() - started\n    print(name, user.user_id, f'{elapsed:.3f}s', len(result.get('department_options', [])), len(result.get('departments', [])), len(result.get('tickets', [])))\n    assert elapsed < 10, f'{name} dashboard exceeded 10 seconds: {elapsed:.3f}s'\n    db.close()\n\"\"\")"
```

Expected: both `王薇 667` and `白海燕 606` complete in under 10 seconds without a 504 or statement timeout.

- [ ] **Step 4: Verify the pre-activity range returns before business SQL**

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, 'python_app'); from routers.activity_analysis import _points_effective_date_range; assert _points_effective_date_range('2026-07-01', '2026-07-08') is None; print('pre-activity range returns before business SQL')"
```

Expected: prints `pre-activity range returns before business SQL`.

- [ ] **Step 5: Inspect the final working-tree boundary**

```bash
git status --short
git diff --stat
git diff --check
```

Expected: no whitespace errors; pre-existing unrelated files remain untouched and no implementation files are staged.
