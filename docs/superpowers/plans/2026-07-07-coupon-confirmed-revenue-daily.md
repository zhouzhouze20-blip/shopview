# Coupon Confirmed Revenue Daily Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only daily report showing how much coupon revenue finance confirmed each day and how much that represents after applying sales revenue rates.

**Architecture:** Add a focused query helper and FastAPI endpoint in `python_app/routers/activity_analysis.py` that reads `activity_coupon_revenue_movement` and joins back to `activity_coupon_voucher_match` for confirmation time. Add a React page under activity analysis, wire it into the existing dashboard switch, navigation tree, and module permission maps. Keep rebuild and monthly confirmation actions out of this page.

**Tech Stack:** FastAPI, SQLAlchemy text queries, React, TanStack Query, shadcn UI components, Node `assert` tests, Python `unittest`.

---

### Task 1: Backend Query Helper And Endpoint

**Files:**
- Modify: `python_app/routers/activity_analysis.py`
- Test: `tests/test_coupon_confirmed_revenue_daily.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_coupon_confirmed_revenue_daily.py`:

```python
import unittest

from routers.activity_analysis import (
    COUPON_CONFIRMED_REVENUE_VIEW_PERMISSION,
    coupon_confirmed_revenue_daily_sql,
    summarize_confirmed_revenue_rows,
)


class CouponConfirmedRevenueDailyTest(unittest.TestCase):
    def test_query_filters_by_finance_confirmed_at(self):
        sql = coupon_confirmed_revenue_daily_sql(include_coupon_type=False)

        self.assertIn("JOIN activity_coupon_voucher_match m", sql)
        self.assertIn("m.confirmed_at >= CAST(:start_date AS DATE)", sql)
        self.assertIn("m.confirmed_at < CAST(:end_date AS DATE) + INTERVAL '1 day'", sql)
        self.assertIn("rm.business_date", sql)

    def test_query_can_filter_coupon_type_without_recomputing_amount(self):
        sql = coupon_confirmed_revenue_daily_sql(include_coupon_type=True)

        self.assertIn("UPPER(TRIM(rm.coupon_type)) = UPPER(TRIM(:coupon_type))", sql)
        self.assertIn("COALESCE(rm.actual_revenue_amount, 0) AS actual_revenue_amount", sql)
        self.assertNotIn("rm.business_amount * rm.revenue_rate", sql)

    def test_summary_counts_missing_rate_as_zero_revenue(self):
        result = summarize_confirmed_revenue_rows(
            [
                {"market_code": "603", "business_amount": 1000, "actual_revenue_amount": 250, "rate_status": "OK"},
                {"market_code": "603", "business_amount": 500, "actual_revenue_amount": 0, "rate_status": "MISSING_RATE"},
                {"market_code": "601", "business_amount": 200, "actual_revenue_amount": 60, "rate_status": "OK"},
            ]
        )

        self.assertEqual(result["summary"]["movement_count"], 3)
        self.assertEqual(result["summary"]["missing_rate_count"], 1)
        self.assertEqual(result["summary"]["business_amount"], 1700)
        self.assertEqual(result["summary"]["confirmed_revenue_amount"], 310)
        self.assertEqual([row["market_code"] for row in result["store_summary"]], ["603", "601"])

    def test_permission_constant_is_read_only(self):
        self.assertEqual(COUPON_CONFIRMED_REVENUE_VIEW_PERMISSION, "activity_settlement.confirmed_revenue.view")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_coupon_confirmed_revenue_daily.py -q
```

Expected: import failure for the new helper names.

- [ ] **Step 3: Add minimal backend implementation**

In `python_app/routers/activity_analysis.py`, add:

```python
COUPON_CONFIRMED_REVENUE_VIEW_PERMISSION = "activity_settlement.confirmed_revenue.view"
```

Add helper functions near the existing coupon monthly helpers:

```python
def coupon_confirmed_revenue_daily_sql(include_coupon_type: bool = False) -> str:
    coupon_filter = "AND UPPER(TRIM(rm.coupon_type)) = UPPER(TRIM(:coupon_type))" if include_coupon_type else ""
    return f"""
        SELECT
          rm.id,
          rm.business_date,
          rm.period_month,
          rm.market_code,
          rm.business_store_code,
          rm.coupon_type,
          rm.coupon_name,
          rm.match_type,
          rm.movement_direction,
          rm.voucher_match_id,
          rm.voucher_detail_id,
          COALESCE(rm.business_amount, 0) AS business_amount,
          rm.revenue_rate,
          COALESCE(rm.actual_revenue_amount, 0) AS actual_revenue_amount,
          rm.rate_status,
          m.confirmed_at,
          COALESCE(NULLIF(u.real_name, ''), u.username) AS confirmed_by_name
        FROM activity_coupon_revenue_movement rm
        JOIN activity_coupon_voucher_match m ON m.id = rm.voucher_match_id
        LEFT JOIN users u ON u.user_id = m.confirmed_by
        WHERE m.confirmed_at >= CAST(:start_date AS DATE)
          AND m.confirmed_at < CAST(:end_date AS DATE) + INTERVAL '1 day'
          AND (:market_code = '' OR rm.market_code = :market_code)
          {coupon_filter}
        ORDER BY m.confirmed_at DESC, rm.market_code, rm.coupon_type, rm.id
    """


def _store_name_from_code(code: object) -> str:
    value = str(code or "")
    return {"601": "购物中心", "602": "百货大楼", "603": "新世纪", "604": "半山"}.get(value, value or "—")


def summarize_confirmed_revenue_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "movement_count": len(rows),
        "missing_rate_count": sum(1 for row in rows if row.get("rate_status") == "MISSING_RATE"),
        "business_amount": sum(float(row.get("business_amount") or 0) for row in rows),
        "confirmed_revenue_amount": sum(float(row.get("actual_revenue_amount") or 0) for row in rows),
        "sales_revenue_amount": None,
        "confirmed_revenue_ratio": None,
    }
    store_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("market_code") or "")
        item = store_map.setdefault(
            code,
            {
                "market_code": code,
                "store_name": _store_name_from_code(code),
                "movement_count": 0,
                "missing_rate_count": 0,
                "business_amount": 0.0,
                "confirmed_revenue_amount": 0.0,
                "sales_revenue_amount": None,
                "confirmed_revenue_ratio": None,
            },
        )
        item["movement_count"] += 1
        if row.get("rate_status") == "MISSING_RATE":
            item["missing_rate_count"] += 1
        item["business_amount"] += float(row.get("business_amount") or 0)
        item["confirmed_revenue_amount"] += float(row.get("actual_revenue_amount") or 0)
    normalized_rows = [{**row, "store_name": _store_name_from_code(row.get("market_code"))} for row in rows]
    return {"summary": summary, "store_summary": list(store_map.values()), "rows": normalized_rows}
```

Add endpoint:

```python
@router.get("/coupon-confirmed-revenue-daily")
async def coupon_confirmed_revenue_daily(
    start_date: str = Query(...),
    end_date: str | None = Query(None),
    market_code: str | None = Query(None),
    coupon_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, COUPON_CONFIRMED_REVENUE_VIEW_PERMISSION)
    _ensure_coupon_monthly_tables(db)
    if not _table_exists(db, "activity_coupon_voucher_match") or not _table_exists(db, "activity_coupon_revenue_movement"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="卡券凭证匹配表或每日收入变动表尚未创建")
    params = {
        "start_date": start_date,
        "end_date": end_date or start_date,
        "market_code": (market_code or "").strip(),
    }
    include_coupon_type = bool((coupon_type or "").strip())
    if include_coupon_type:
        params["coupon_type"] = coupon_type.strip()
    rows = _rows(db, coupon_confirmed_revenue_daily_sql(include_coupon_type), params)
    return summarize_confirmed_revenue_rows(rows)
```

- [ ] **Step 4: Run test to verify backend passes**

Run:

```bash
python -m pytest tests/test_coupon_confirmed_revenue_daily.py -q
```

Expected: 4 passed.

### Task 2: Permissions And Navigation

**Files:**
- Modify: `python_app/routers/authz.py`
- Modify: `client/src/lib/module-permissions.ts`
- Modify: `client/src/lib/navigation-items.ts`
- Modify: `client/src/lib/role-permission-tree.ts`
- Test: `client/src/lib/role-permission-tree.test.mjs`

- [ ] **Step 1: Write failing frontend permission tests**

Extend `client/src/lib/role-permission-tree.test.mjs` fixture with:

```js
{ id: 12, permission_code: "activity_settlement.confirmed_revenue.view", permission_name: "查看确认收入占比", module_code: "activity_settlement", action_code: "confirmed_revenue_view" },
```

Assert the activity settlement children are:

```js
assert.deepEqual((activitySettlement.children ?? []).map((node) => node.id), [
  "voucher-match",
  "confirmed-revenue-daily",
  "coupon-monthly-balance",
]);
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node client/src/lib/role-permission-tree.test.mjs
```

Expected: failure because `confirmed-revenue-daily` is missing.

- [ ] **Step 3: Add permission and nav entries**

Add backend permission to `CORE_PERMISSION_DEFINITIONS`:

```python
("activity_settlement.confirmed_revenue.view", "查看确认收入占比", "activity_settlement", "confirmed_revenue_view"),
```

Add module permission:

```ts
"confirmed-revenue-daily": ["activity_settlement.confirmed_revenue.view"],
```

Add navigation item between voucher match and monthly balance:

```ts
{ id: "confirmed-revenue-daily", name: "确认收入占比", icon: CircleDollarSign },
```

Add role tree node between voucher match and monthly balance:

```ts
{
  id: "confirmed-revenue-daily",
  name: "确认收入占比",
  permissionCodes: ["activity_settlement.confirmed_revenue.view"],
},
```

- [ ] **Step 4: Run test to verify navigation permissions pass**

Run:

```bash
node client/src/lib/role-permission-tree.test.mjs
```

Expected: test passes.

### Task 3: Frontend Page And Dashboard Routing

**Files:**
- Create: `client/src/pages/activity-analysis/confirmed-revenue-daily.tsx`
- Modify: `client/src/pages/main-dashboard.tsx`
- Test: `client/src/lib/confirmed-revenue-daily-page.test.mjs`

- [ ] **Step 1: Write failing static page test**

Create `client/src/lib/confirmed-revenue-daily-page.test.mjs`:

```js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const page = readFileSync(resolve("client/src/pages/activity-analysis/confirmed-revenue-daily.tsx"), "utf8");
const dashboard = readFileSync(resolve("client/src/pages/main-dashboard.tsx"), "utf8");

assert.match(page, /确认收入占比/);
assert.match(page, /coupon-confirmed-revenue-daily/);
assert.match(page, /confirmed_revenue_amount/);
assert.match(page, /missing_rate_count/);
assert.doesNotMatch(page, /刷新每日变动/);
assert.doesNotMatch(page, /确认月结/);
assert.match(dashboard, /ConfirmedRevenueDailyPage/);
assert.match(dashboard, /case "confirmed-revenue-daily"/);

console.log("confirmed revenue daily page checks passed");
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
node client/src/lib/confirmed-revenue-daily-page.test.mjs
```

Expected: file read failure because the page does not exist.

- [ ] **Step 3: Add page component and route**

Implement `ConfirmedRevenueDailyPage` with TanStack Query, filters, summary cards, store summary table, and detail table. Use the existing style from `voucher-match.tsx` and `coupon-monthly-balance.tsx`, but only include read-only refresh.

Wire `client/src/pages/main-dashboard.tsx`:

```ts
import ConfirmedRevenueDailyPage from "./activity-analysis/confirmed-revenue-daily";
```

Add label:

```ts
"confirmed-revenue-daily": "确认收入占比",
```

Add switch case:

```tsx
case "confirmed-revenue-daily":
  return <ConfirmedRevenueDailyPage />;
```

- [ ] **Step 4: Run test to verify page static checks pass**

Run:

```bash
node client/src/lib/confirmed-revenue-daily-page.test.mjs
```

Expected: test passes.

### Task 4: Verification

**Files:**
- Verify only; no new file expected.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
python -m pytest tests/test_coupon_confirmed_revenue_daily.py tests/test_coupon_monthly_balance.py tests/test_activity_voucher_matching.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run focused frontend tests**

Run:

```bash
node client/src/lib/confirmed-revenue-daily-page.test.mjs
node client/src/lib/role-permission-tree.test.mjs
```

Expected: both commands pass.

- [ ] **Step 3: Review diff scope**

Run:

```bash
git diff -- python_app/routers/activity_analysis.py python_app/routers/authz.py client/src/lib/module-permissions.ts client/src/lib/navigation-items.ts client/src/lib/role-permission-tree.ts client/src/pages/main-dashboard.tsx client/src/pages/activity-analysis/confirmed-revenue-daily.tsx tests/test_coupon_confirmed_revenue_daily.py client/src/lib/confirmed-revenue-daily-page.test.mjs
```

Expected: diff only contains the confirmed revenue daily page feature and no unrelated rewrites.
