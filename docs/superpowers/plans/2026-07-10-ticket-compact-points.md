# Ticket Compact Points Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the ticket-list product-count column from the page and Excel export, and include `香奈儿活动补发` in the existing consumption-points total.

**Architecture:** Keep the API response shape unchanged, including `quantity`, but expand the backend point-category predicate. Remove quantity only from the ticket-list presentation and its pure Excel table builder so other sales views and ticket details remain compatible.

**Tech Stack:** FastAPI, SQLAlchemy text SQL, React, TypeScript, SheetJS, Python `unittest`, Node test runner, Vite.

---

## File map and dirty-worktree constraint

- Modify `python_app/routers/sales.py`: extend the consumption point category predicate.
- Modify `tests/test_sales_ticket_filters.py`: assert the generated ticket SQL includes the Chanel reissue category.
- Modify `client/src/lib/export-sales-excel.ts`: remove quantity from the ticket export table only.
- Modify `client/src/lib/export-sales-excel.test.mjs`: verify ticket export headers, values, and totals after the column removal.
- Modify `client/src/pages/sales-dashboard.tsx`: remove product count from the ticket tab and its totals.
- Modify `client/src/lib/sales-dashboard-drilldown.test.mjs`: add a focused ticket-tab source contract.

These files already contain user-owned changes. Keep edits narrow and do not stage or commit the whole dirty files.

### Task 1: Include Chanel reissue points in consumption points

**Files:**
- Modify: `tests/test_sales_ticket_filters.py`
- Modify: `python_app/routers/sales.py`

- [ ] **Step 1: Add a failing SQL contract assertion**

In `test_group_tickets_sums_priced_sales_amount_by_billno`, append:

```python
self.assertIn("'香奈儿活动补发'", captured["sql"])
```

- [ ] **Step 2: Run the focused test and verify RED**

```bash
./.venv/bin/python -m unittest \
  tests.test_sales_ticket_filters.SalesTicketFilterTests.test_group_tickets_sums_priced_sales_amount_by_billno -v
```

Expected: FAIL because the generated SQL contains only `消费加积分` and `消费获得积分`.

- [ ] **Step 3: Extend the backend predicate**

Change `consumption_point_condition` to:

```python
consumption_point_condition = (
    f"{point_category_expr} IN ('消费加积分', '消费获得积分', '香奈儿活动补发')"
)
```

- [ ] **Step 4: Run the full backend file**

```bash
./.venv/bin/python -m unittest tests.test_sales_ticket_filters -v
```

Expected: all tests PASS.

### Task 2: Remove product count from ticket Excel

**Files:**
- Modify: `client/src/lib/export-sales-excel.test.mjs`
- Modify: `client/src/lib/export-sales-excel.ts`

- [ ] **Step 1: Change the export expectations first**

Update the ticket export test to assert the new column positions and absence of `商品数`:

```js
test("ticket export omits product count and inserts retail price before sales revenue", () => {
  const withRetail = buildTicketExportTable(ticketRows, true);
  assert.equal(withRetail[0].includes("商品数"), false);
  assert.equal(withRetail[0][5], "零售价");
  assert.equal(withRetail[0][6], "销售收入");
  assert.equal(withRetail[1][5], 1200);
  assert.equal(withRetail.at(-1)[5], 1200);

  const withoutRetail = buildTicketExportTable(ticketRows, false);
  assert.equal(withoutRetail[0].includes("商品数"), false);
  assert.equal(withoutRetail[0].includes("零售价"), false);
  assert.equal(withoutRetail[0][5], "销售收入");
});
```

- [ ] **Step 2: Run the export test and verify RED**

```bash
node --experimental-strip-types --test client/src/lib/export-sales-excel.test.mjs
```

Expected: FAIL because the current header still includes `商品数`.

- [ ] **Step 3: Remove quantity from the pure ticket export table**

In `buildTicketExportTable`:

- Delete `"商品数"` from `header`.
- Change the retail-price insertion index from `6` to `5`.
- Delete `sumQty` and `sumQty += n(row.quantity)`.
- Delete `n(row.quantity)` from each row.
- Remove the quantity position from `footer`, leaving five leading cells before sales revenue.
- Change the footer retail-price insertion index from `6` to `5`.

The resulting leading row structure must be:

```ts
const values: (string | number)[] = [
  row.billno,
  String(row.sale_datetime || row.sale_date || "").trim() || "—",
  String(row.transaction_type || "").trim() || "—",
  row.invoice_no != null && `${row.invoice_no}` !== "" ? row.invoice_no : "—",
  row.cashier || "—",
  n(row.effective_sales),
  n(row.net_profit),
];
```

The existing remaining discount, payment, and point values stay after these entries.

- [ ] **Step 4: Run the export test and verify GREEN**

Run the Step 2 command.

Expected: both export tests PASS.

### Task 3: Remove product count from the ticket page

**Files:**
- Modify: `client/src/lib/sales-dashboard-drilldown.test.mjs`
- Modify: `client/src/pages/sales-dashboard.tsx`

- [ ] **Step 1: Add a focused failing page-source test**

Inside the existing sales-dashboard source test, derive the ticket tab and assert:

```js
const ticketTabStart = pageSource.indexOf('<TabsContent value="tickets">');
const ticketTabEnd = pageSource.indexOf("</TabsContent>", ticketTabStart);
const ticketTabSource = pageSource.slice(ticketTabStart, ticketTabEnd);
assert.ok(ticketTabStart >= 0 && ticketTabEnd > ticketTabStart);
assert.doesNotMatch(ticketTabSource, />商品数</);
assert.doesNotMatch(ticketTabSource, /ticketsTableTotals\.quantity/);
assert.match(ticketTabSource, /showPricedSalesAmount \? 14 : 13/);
```

- [ ] **Step 2: Run the page test and verify RED**

```bash
node --experimental-strip-types --test client/src/lib/sales-dashboard-drilldown.test.mjs
```

Expected: FAIL because the ticket tab still renders `商品数` and uses spans 15/14.

- [ ] **Step 3: Remove the ticket-page quantity presentation**

In `ticketsTableTotals`, delete:

```ts
quantity: acc.quantity + Number(row.quantity || 0),
```

and its initializer:

```ts
quantity: 0,
```

In the ticket tab, delete the “商品数” header, `number(row.quantity)` data cell, and `ticketsTableTotals.quantity` footer cell. Change the empty-state span to:

```tsx
colSpan={showPricedSalesAmount ? 14 : 13}
```

- [ ] **Step 4: Run frontend tests and build**

```bash
node --experimental-strip-types --test \
  client/src/lib/sales-dashboard-drilldown.test.mjs \
  client/src/lib/export-sales-excel.test.mjs
npm --prefix client run build
```

Expected: all Node tests PASS and the production build exits `0`.

### Task 4: Final verification

**Files:**
- Verify only.

- [ ] **Step 1: Run all focused automated checks**

```bash
./.venv/bin/python -m unittest tests.test_sales_ticket_filters -v
node --experimental-strip-types --test \
  client/src/lib/sales-dashboard-drilldown.test.mjs \
  client/src/lib/export-sales-excel.test.mjs
npm --prefix client run build
git diff --check -- \
  python_app/routers/sales.py \
  tests/test_sales_ticket_filters.py \
  client/src/lib/export-sales-excel.ts \
  client/src/lib/export-sales-excel.test.mjs \
  client/src/pages/sales-dashboard.tsx \
  client/src/lib/sales-dashboard-drilldown.test.mjs
```

Expected: Python tests, Node tests, build, and diff check all exit `0`.

- [ ] **Step 2: Verify the live local page**

On `http://127.0.0.1:5174/`, verify the Chanel ticket table has no “商品数”, all remaining columns fit the current desktop viewport, and the consumption-point values for `13075059`, `13074987`, `13074902`, and `13074868` are `50,850`, `20,650`, `6,570`, and `9,330`.

- [ ] **Step 3: Verify the ticket Excel export**

Export the Chanel ticket rows and confirm there is no “商品数” header, “零售价” remains before “销售收入”, and consumption points match the page.
