# OD0002 Table Display and Department Order Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make OD0002 use red for rising同比, green for falling同比, compact data rows, and the sales-dashboard department order.

**Architecture:** Reuse `department_display_sort_key` in the OD0002 backend result normalizer so both JSON and Excel share the same department order. Add a small frontend helper that maps raw同比 values to color classes and render metric cells from raw metric metadata rather than formatted string signs. Apply `py-2` only to body and footer cells.

**Tech Stack:** Python, FastAPI service helpers, React, TypeScript, Node test runner, pytest, Tailwind CSS.

---

### Task 1: Align OD0002 department ordering

**Files:**
- Modify: `python_app/services/od0002_report.py`
- Test: `tests/test_od0002_report.py`

- [ ] **Step 1: Write the failing test**

Add a test that feeds department rows in reverse business order and asserts the normalized `departments` list equals the order returned by `department_display_sort_key`, while another dimension remains unchanged.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py -q`
Expected: FAIL because OD0002 currently preserves SQL code order.

- [ ] **Step 3: Write minimal implementation**

Import `department_display_sort_key` and sort only `dimensions["departments"]` after rows are normalized:

```python
dimensions["departments"].sort(
    key=lambda row: department_display_sort_key({
        "department_code": row.get("dimension_code"),
        "department_name": row.get("dimension_name"),
    })
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py tests/test_od0002_excel.py -q`
Expected: all selected tests pass, with the configured integration test allowed to skip.

### Task 2: Apply同比 colors and compact rows

**Files:**
- Modify: `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`
- Test: `client/src/lib/od0002-report.test.mjs`

- [ ] **Step 1: Write the failing test**

Add source contract assertions proving the page maps positive同比 to `text-red-600`, negative同比 to `text-green-600`, leaves zero uncolored, uses raw metric positions `2`, `5`, and `8`, and applies `py-2` to body/footer cells.

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test client/src/lib/od0002-report.test.mjs`
Expected: FAIL because negative formatted strings currently use red and cells have no compact padding class.

- [ ] **Step 3: Write minimal implementation**

Add `yoyColorClass(value)` and render the nine metric cells with their raw values. Only indexes `2`, `5`, and `8` receive同比 colors. Add `py-2` to store, dimension, metric, and footer cells.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test client/src/lib/od0002-report.test.mjs`
Expected: all tests pass.

### Task 3: Verify the combined change

**Files:**
- Verify: `python_app/services/od0002_report.py`
- Verify: `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`

- [ ] **Step 1: Run backend regression tests**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py tests/test_od0002_excel.py -q`
Expected: all selected tests pass, with only the configured integration skip.

- [ ] **Step 2: Run frontend tests and type checks**

Run: `node --test client/src/lib/od0002-report.test.mjs client/src/lib/od0002-navigation.test.mjs && cd client && npx tsc --noEmit`
Expected: tests and TypeScript checks exit successfully.

- [ ] **Step 3: Check patch hygiene**

Run: `git diff --check`
Expected: no whitespace errors.
