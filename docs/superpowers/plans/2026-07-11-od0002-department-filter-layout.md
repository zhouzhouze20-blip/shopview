# OD0002 Department Filter and Query Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a permission-scoped single-department selector to OD0002, apply it consistently to online and Excel results, remove reset, and implement the approved grouped query layout.

**Architecture:** Add a dedicated department-option query that uses the same business-scope SQL as OD0002 and optionally limits by store. Pass an optional bound `department_id` through report and export loading into the base sales query. Extend frontend filter helpers for the all-department sentinel and store-change reset, then reorganize the existing controls into period and organization groups.

**Tech Stack:** FastAPI, SQLAlchemy text queries, PostgreSQL, React, TypeScript, TanStack Query, Tailwind CSS, pytest, Node test runner.

---

### Task 1: Add permission-scoped department options

**Files:**
- Modify: `python_app/services/od0002_report.py`
- Modify: `python_app/routers/sales.py`
- Test: `tests/test_od0002_report.py`

- [ ] **Step 1: Write failing service and endpoint tests**

Add tests proving the department query includes the trusted scope fragment, binds `selected_store` when supplied, excludes OD0002 excluded department codes, returns `department_code`, `department_name`, and `store_code`, and sorts each store with `department_display_sort_key`. Add an endpoint test that verifies `sales.od0002.view` and scope loading.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py -q`
Expected: FAIL because the department option builder, loader, and route do not exist.

- [ ] **Step 3: Implement the department option service and route**

Add `build_authorized_departments_query(...)`, `load_od0002_authorized_departments(...)`, and `GET /reports/od0002/departments?store_id=...`. Use bound parameters for store and excluded department codes; apply `_business_scope_filter_sql` with the same OD0002 dimension expressions; sort normalized rows by `(store_code, department_display_sort_key(...))`.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py -q`
Expected: all OD0002 report tests pass except the configured database integration skip.

### Task 2: Filter report and export by one department

**Files:**
- Modify: `python_app/services/od0002_report.py`
- Modify: `python_app/routers/sales.py`
- Test: `tests/test_od0002_report.py`
- Test: `tests/test_od0002_excel.py`

- [ ] **Step 1: Write failing query and endpoint tests**

Add tests proving `selected_department` creates a bound `department_id` predicate in `build_report_query`, report/export pass the same department value, and an empty value remains unfiltered.

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py tests/test_od0002_excel.py -q`
Expected: FAIL because report and export do not accept `department_id`.

- [ ] **Step 3: Implement bound department filtering**

Add `department_id: str | None` to OD0002 report/export routes and `_load_od0002_for_request`. Normalize whitespace and pass `selected_department` to `load_od0002_report` and `build_report_query`. Add this bound predicate after the department join in the OD0002 `base` CTE:

```sql
AND UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, ''))) = UPPER(:selected_department)
```

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py tests/test_od0002_excel.py -q`
Expected: all selected tests pass except the configured database integration skip.

### Task 3: Add frontend department filter state and request parameters

**Files:**
- Modify: `client/src/lib/od0002-report.ts`
- Modify: `client/src/lib/od0002-report.test.mjs`
- Modify: `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`

- [ ] **Step 1: Write failing helper tests**

Add tests for `OD0002_ALL_DEPARTMENTS`, `buildOd0002Params(..., departmentId)`, and a helper that changes store while resetting `departmentId` to the all-department sentinel.

- [ ] **Step 2: Verify RED**

Run: `node --test client/src/lib/od0002-report.test.mjs`
Expected: FAIL because department state helpers do not exist.

- [ ] **Step 3: Implement state and option loading**

Extend `Filters` with `departmentId`, default to `OD0002_ALL_DEPARTMENTS`, include a department query keyed by the draft store, render “全部部门” plus returned options, and reset department when store changes. Pass submitted department into query and export URL builders.

- [ ] **Step 4: Verify GREEN**

Run: `node --test client/src/lib/od0002-report.test.mjs`
Expected: all OD0002 frontend tests pass.

### Task 4: Implement approved B layout and remove reset

**Files:**
- Modify: `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`
- Test: `client/src/lib/od0002-report.test.mjs`

- [ ] **Step 1: Write failing source-contract test**

Assert the source contains “统计期间” and “组织范围”, uses a two-column responsive outer grid, places store and department in the organization group, and no longer imports or renders `RefreshCw`, `>重置<`, or the `reset` handler.

- [ ] **Step 2: Verify RED**

Run: `node --test client/src/lib/od0002-report.test.mjs`
Expected: FAIL because the old five-column layout and reset button remain.

- [ ] **Step 3: Implement the layout**

Use `grid gap-6 lg:grid-cols-2`; place four date fields in `sm:grid-cols-2`; place store and department in `sm:grid-cols-2`; keep query/export buttons aligned at the organization group bottom-right; preserve validation and export errors below the grouped grid.

- [ ] **Step 4: Verify GREEN**

Run: `node --test client/src/lib/od0002-report.test.mjs`
Expected: all OD0002 frontend tests pass.

### Task 5: Full verification

**Files:**
- Verify all files above.

- [ ] **Step 1: Run backend regressions**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py tests/test_od0002_excel.py -q`
Expected: all selected tests pass except the configured database integration skip.

- [ ] **Step 2: Run frontend tests, types, and build**

Run: `node --test client/src/lib/od0002-report.test.mjs client/src/lib/od0002-navigation.test.mjs client/src/lib/role-permission-tree.test.mjs && cd client && npx tsc --noEmit && npm run build`
Expected: tests, type checking, and production build succeed.

- [ ] **Step 3: Check patch hygiene**

Run: `git diff --check`
Expected: no whitespace errors.
