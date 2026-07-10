# Activity Analysis Store Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove activity search/schedule selection from the general activity-analysis page and make every page query aggregate by analysis scope, authorized store, and date.

**Architecture:** Keep the existing activity-analysis router and its `activity_id` compatibility path, but add permission-scoped store options plus reusable validation/filter helpers. The React page stops loading activities, selects an optional `store_code`, and sends that same value to every summary and drill-down request.

**Tech Stack:** FastAPI, SQLAlchemy text queries, Python `unittest`, React 18, TanStack Query, TypeScript, Node test runner, Vite.

---

### Task 1: Add permission-scoped store helpers and options endpoint

**Files:**
- Modify: `python_app/routers/activity_analysis.py:840-1017`
- Create: `test/test_activity_analysis_store_filter.py`

- [ ] **Step 1: Write failing helper tests**

Create `test/test_activity_analysis_store_filter.py` with fake DB rows and scope objects. Cover all-access active stores, restricted `store_id`/`store_code` matching, deny subtraction, case-insensitive code normalization, and a forbidden selected store:

```python
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from fastapi import HTTPException

from routers.activity_analysis import (
    _activity_store_options_for_scope,
    _require_selected_activity_store,
)


class ActivityAnalysisStoreFilterTest(unittest.TestCase):
    @patch("routers.activity_analysis._activity_store_scope_values")
    @patch("routers.activity_analysis._rows")
    def test_restricted_options_only_include_allowed_store(self, rows, scope_values):
        rows.return_value = [
            {"store_id": 1, "store_code": "601", "store_name": "常州购物中心"},
            {"store_id": 2, "store_code": "602", "store_name": "常州百货大楼"},
        ]
        scope_values.side_effect = [({"1"}, {"601"}), (set(), set())]
        scope = SimpleNamespace(all_access=False, allow={"store": {"1"}}, deny={})
        self.assertEqual(
            [row["store_code"] for row in _activity_store_options_for_scope(object(), scope)],
            ["601"],
        )

    @patch("routers.activity_analysis._activity_store_options_for_scope")
    def test_selected_store_outside_scope_is_forbidden(self, options):
        options.return_value = [
            {"store_id": 1, "store_code": "601", "store_name": "常州购物中心"},
        ]
        scope = SimpleNamespace(all_access=False, allow={"store": {"1"}}, deny={})
        with self.assertRaises(HTTPException) as raised:
            _require_selected_activity_store(object(), scope, "602")
        self.assertEqual(raised.exception.status_code, 403)
```

- [ ] **Step 2: Run tests and verify the helper imports fail**

Run: `python3 test/test_activity_analysis_store_filter.py`

Expected: FAIL because `_activity_store_options_for_scope` and `_require_selected_activity_store` do not exist.

- [ ] **Step 3: Implement store option and validation helpers**

Add focused helpers beside `_activity_store_scope_values`:

```python
def _activity_store_options_for_scope(db: Session, scope) -> list[dict[str, Any]]:
    rows = _rows(db, """
        SELECT store_id, store_code, store_name
        FROM stores
        WHERE COALESCE(is_active, TRUE) = TRUE
        ORDER BY store_id
    """, {})
    if getattr(scope, "all_access", False):
        return rows
    allowed_ids, allowed_codes = _activity_store_scope_values(db, scope)
    deny_scope = type("DenyScope", (), {
        "allow": {"store": scope.deny.get("store", set())},
        "all_access": False,
    })()
    denied_ids, denied_codes = _activity_store_scope_values(db, deny_scope)
    return [
        row for row in rows
        if (str(row["store_id"]) in allowed_ids or str(row["store_code"]).upper() in allowed_codes)
        and str(row["store_id"]) not in denied_ids
        and str(row["store_code"]).upper() not in denied_codes
    ]


def _require_selected_activity_store(db: Session, scope, store_code: str | None) -> str | None:
    normalized = str(store_code or "").strip().upper()
    if not normalized:
        return None
    allowed = {
        str(row["store_code"] or "").strip().upper()
        for row in _activity_store_options_for_scope(db, scope)
    }
    if normalized not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="门店不存在或无数据权限")
    return normalized
```

Add `GET /api/activity-analysis/store-options`, require `ACTIVITY_ANALYSIS_PERMISSION`, load the `sales` business scope, and return `_activity_store_options_for_scope(db, business_scope)`.

- [ ] **Step 4: Run helper tests**

Run: `python3 test/test_activity_analysis_store_filter.py`

Expected: PASS for option filtering, deny filtering, normalization, and forbidden selection.

- [ ] **Step 5: Commit the helper slice**

```bash
git add python_app/routers/activity_analysis.py test/test_activity_analysis_store_filter.py
git commit -m "feat: add scoped activity store options"
```

### Task 2: Apply selected store to every general-analysis query

**Files:**
- Modify: `python_app/routers/activity_analysis.py:2332-4860`
- Modify: `test/test_activity_analysis_store_filter.py`

- [ ] **Step 1: Write failing endpoint contract tests**

Use `inspect.signature` and `inspect.getsource` to assert that `overview`, `coupon_summary`, `coupon_flows`, `quality_issues`, `coupon_type_departments`, and `department_tickets` accept `store_code`, validate it, and add it to log filtering. Assert that `overview` and `quality_issues` also apply the selected store to `salehead h` period-only queries. Assert that the `unassigned_activity` quality branch keeps its existing issue definition while adding business-scope and selected-store clauses.

```python
for endpoint in endpoints:
    self.assertIn("store_code", inspect.signature(endpoint).parameters)
    source = inspect.getsource(endpoint)
    self.assertIn("_require_selected_activity_store", source)
    self.assertIn("selected_store_code", source)
```

- [ ] **Step 2: Run endpoint tests and verify failure**

Run: `python3 test/test_activity_analysis_store_filter.py`

Expected: FAIL because the six endpoints do not accept or apply `store_code`.

- [ ] **Step 3: Add reusable SQL fragments**

Add helpers that bind a validated store code without interpolating user input:

```python
def _selected_store_clause(
    selected_store_code: str | None,
    params: dict[str, Any],
    *,
    expression: str,
    prefix: str,
) -> str:
    if not selected_store_code:
        return ""
    key = f"{prefix}_selected_store_code"
    params[key] = selected_store_code
    return f" AND {expression}::varchar = :{key}"
```

For each endpoint, normalize/authorize once:

```python
selected_store_code = _require_selected_activity_store(db, business_scope, store_code)
selected_log_store_sql = _selected_store_clause(
    selected_store_code,
    params,
    expression="l.tcflmkt",
    prefix="overview_logs",
)
log_filter = f"({log_filter}){selected_log_store_sql}"
```

Use an `h.mkt` clause for `period_pay_summary` and `payments_without_logs`. In `quality_issues/unassigned_activity`, preserve the unassigned-activity predicate, then append the existing `log_scope_sql` and the selected `l.tcflmkt` clause so that the branch cannot escape business scope.

- [ ] **Step 4: Run backend tests**

Run: `python3 test/test_activity_analysis_store_filter.py`

Expected: PASS.

Run: `python3 test/test_activity_points_rule_sql.py`

Expected: existing activity/points SQL contract tests PASS.

Run: `python3 -m py_compile python_app/routers/activity_analysis.py`

Expected: exit code 0.

- [ ] **Step 5: Commit endpoint filtering**

```bash
git add python_app/routers/activity_analysis.py test/test_activity_analysis_store_filter.py
git commit -m "feat: filter activity analysis by store"
```

### Task 3: Replace activity controls with the store selector

**Files:**
- Modify: `client/src/pages/activity-analysis/index.tsx:1-560`
- Create: `client/src/pages/activity-analysis/index.test.mjs`

- [ ] **Step 1: Write failing page contract tests**

Read `index.tsx` as source and assert the requested UI/query contract:

```javascript
test("general activity analysis uses store and date filters without activity selection", () => {
  assert.equal(source.includes("活动搜索"), false);
  assert.equal(source.includes("活动档期</Label>"), false);
  assert.equal(source.includes("/api/activity-analysis/activities"), false);
  assert.equal(source.includes("activity_id:"), false);
  assert.match(source, /<Label>门店<\/Label>/);
  assert.match(source, /\/api\/activity-analysis\/store-options/);
  assert.match(source, /store_code: selectedStoreParam/);
});
```

Also assert that all six query blocks include `selectedStoreCode` in their query key and `store_code` in their query string, and that the range-description card shows the current store label.

- [ ] **Step 2: Run frontend test and verify failure**

Run: `node --test client/src/pages/activity-analysis/index.test.mjs`

Expected: FAIL because the old activity controls and activity list request still exist.

- [ ] **Step 3: Implement the page state and queries**

In `index.tsx`:

- Remove `Search` import, `ActivityOption`, `keyword`, `activityId`, `activitiesQuery`, activity auto-selection effect, and `selectedActivity`.
- Add `StoreOption` and `selectedStoreCode` state.
- Load `/api/activity-analysis/store-options`.
- Render “门店” with an `all` sentinel and permission-scoped options.
- Define `selectedStoreParam = selectedStoreCode === "all" ? "" : selectedStoreCode`, so `buildQuery` omits the sentinel and otherwise passes the concrete code.
- Remove every `activity_id` argument and activity-dependent `enabled` condition.
- Add `selectedStoreCode` to all relevant query keys and pass `store_code` to overview, coupon summary, coupon flows, quality issues, coupon departments/groups, and department tickets.
- Reset drill-down state on `[analysisScope, selectedStoreCode, startDate, endDate]`.
- Replace the single-activity card with a range card showing analysis-scope label, selected store name, and selected dates.
- Refresh the store options query together with the visible data queries.

- [ ] **Step 4: Run frontend tests and type/build checks**

Run: `node --test client/src/pages/activity-analysis/index.test.mjs`

Expected: PASS.

Run: `npm --prefix client run build`

Expected: TypeScript and Vite build complete successfully.

- [ ] **Step 5: Commit the page slice**

```bash
git add client/src/pages/activity-analysis/index.tsx client/src/pages/activity-analysis/index.test.mjs
git commit -m "feat: add activity analysis store filter"
```

### Task 4: Verify the finished flow

**Files:**
- Modify only if verification exposes a defect in the files above.

- [ ] **Step 1: Run focused verification**

```bash
python3 test/test_activity_analysis_store_filter.py
python3 test/test_activity_points_rule_sql.py
python3 -m py_compile python_app/routers/activity_analysis.py
node --test client/src/pages/activity-analysis/index.test.mjs
npm --prefix client run build
```

Expected: all commands exit 0.

- [ ] **Step 2: Start or reuse the local services and inspect `5174`**

Open “销售管理 → 活动分析 → 通用活动分析” and confirm the filter row contains only analysis scope, start date, end date, store, and refresh. Confirm “活动档期券” loads without a selected activity and changing store updates cards, tables, quality data, and drill-down requests.

- [ ] **Step 3: Verify request and permission boundaries**

In the browser network log, confirm a concrete store sends `store_code=601` (or the selected code), while “全部有权限门店” omits `store_code`. Confirm an unavailable store code returns `403` and does not fall back to all stores.

- [ ] **Step 4: Review the final diff**

Run: `git diff HEAD~3 -- python_app/routers/activity_analysis.py test/test_activity_analysis_store_filter.py client/src/pages/activity-analysis/index.tsx client/src/pages/activity-analysis/index.test.mjs`

Expected: only the approved store-filter feature and its tests are present; unrelated dirty-worktree files are untouched.
