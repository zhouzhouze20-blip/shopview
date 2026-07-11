# Supermarket Sales Drilldown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route supermarket and fresh-food departments through department, group, group goods, product tickets, and receipt detail without changing the normal department path.

**Architecture:** Keep route decisions in a small frontend helper and let the existing sales dashboard page hold the selected group/product state. Extend the existing group tickets API with optional goods, barcode, and supplier filters so the ticket page can be reused.

**Tech Stack:** React, TanStack Query, TypeScript, Node `node:test`, FastAPI, SQLAlchemy.

---

### Task 1: Frontend Drilldown State

**Files:**
- Create: `client/src/lib/sales-dashboard-drilldown.ts`
- Create: `client/src/lib/sales-dashboard-drilldown.test.mjs`
- Modify: `client/src/pages/sales-dashboard.tsx`

- [ ] Write a failing Node test that imports the new helper and asserts:
  - supermarket/fresh departments route to `groups`
  - normal departments route to `groups`
  - supermarket group clicks route to `department-products`
  - normal group clicks route to `tickets`
  - selected product values become ticket query params
- [ ] Run `node client/src/lib/sales-dashboard-drilldown.test.mjs` and confirm the missing module failure.
- [ ] Implement the helper and wire `sales-dashboard.tsx` to track `selectedDepartmentProduct`.
- [ ] Make group goods rows clickable; for supermarket/fresh groups, clicking a group opens the goods table filtered by `group_code`.
- [ ] Update breadcrumbs and back buttons so product-ticket context returns to the group goods page.
- [ ] Re-run the Node helper test.

### Task 2: Backend Ticket Filters

**Files:**
- Modify: `python_app/routers/sales.py`
- Create: `tests/test_sales_ticket_filters.py`

- [ ] Write a failing Python unit test for SQL filter construction that expects `goods_code`, `barcode`, and `supplier_code` predicates.
- [ ] Add a small SQL filter helper for optional ticket product filters.
- [ ] Use that helper in `/api/sales/groups/{group_code}/tickets`.
- [ ] Re-run the Python test.

### Task 3: Verification

**Files:**
- Existing build/test files only.

- [ ] Run `node client/src/lib/sales-dashboard-drilldown.test.mjs`.
- [ ] Run `python -m pytest tests/test_sales_ticket_filters.py -q`.
- [ ] Run `npm --prefix client run build`.
- [ ] Inspect `git diff -- client/src/pages/sales-dashboard.tsx client/src/lib/sales-dashboard-drilldown.ts python_app/routers/sales.py`.
