# Center Cosmetics Retail Price Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `sum(sglsjje)` as a conditional “零售价” column to the Changzhou Shopping Center cosmetics department group and ticket views, totals, and Excel exports.

**Architecture:** The sales API always returns a numeric `priced_sales_amount` for group and ticket rows. A single frontend scope helper identifies “常州购物中心 → 中心一部（化妆）”; the page and export functions use that boolean to conditionally insert the column while every other department keeps its existing shape.

**Tech Stack:** FastAPI, SQLAlchemy text SQL, React, TypeScript, TanStack Query, SheetJS (`xlsx`), Python `unittest`/pytest, Node test runner.

---

## File map and worktree constraint

- Modify `python_app/routers/sales.py`: select and return `priced_sales_amount` for group and ticket summaries.
- Modify `tests/test_sales_ticket_filters.py`: backend SQL contract tests for the new aggregation.
- Modify `client/src/lib/sales-dashboard-drilldown.ts`: pure scope predicate for the one allowed store/department pair.
- Modify `client/src/lib/sales-dashboard-drilldown.test.mjs`: scope predicate tests.
- Modify `client/src/lib/export-sales-excel.ts`: conditional group/ticket export table builders and export options.
- Create `client/src/lib/export-sales-excel.test.mjs`: tests for conditional headers, rows, and totals without writing files.
- Modify `client/src/pages/sales-dashboard.tsx`: types, totals, handlers, conditional cells, and dynamic empty-state spans.

The current worktree already has user-owned modifications in `python_app/routers/sales.py` and `client/src/pages/sales-dashboard.tsx`. Preserve those changes. During execution, inspect the diff before each edit, keep new hunks narrow, and do not stage or commit whole dirty files. Verification checkpoints replace per-task commits unless the new hunks can be staged independently without capturing user changes.

### Task 1: Add and test the center-cosmetics scope predicate

**Files:**
- Modify: `client/src/lib/sales-dashboard-drilldown.test.mjs`
- Modify: `client/src/lib/sales-dashboard-drilldown.ts`

- [ ] **Step 1: Write the failing scope tests**

Add `isCenterCosmeticsRetailPriceScope` to the test import and append:

```js
test("retail price scope matches only Changzhou Shopping Center cosmetics", () => {
  assert.equal(
    isCenterCosmeticsRetailPriceScope(
      { store_id: "1", store_name: "常州购物中心" },
      { department_code: "6010101", department_name: "中心一部(化妆)" },
    ),
    true,
  );
  assert.equal(
    isCenterCosmeticsRetailPriceScope(
      { store_id: 601, store_name: "常州购物中心" },
      { department_code: "", department_name: "中心一部（化妆）" },
    ),
    true,
  );
  assert.equal(
    isCenterCosmeticsRetailPriceScope(
      { store_id: "3", store_name: "常州新世纪" },
      { department_code: "6030101", department_name: "新世纪一部(化妆)" },
    ),
    false,
  );
  assert.equal(
    isCenterCosmeticsRetailPriceScope(
      { store_id: "1", store_name: "常州购物中心" },
      { department_code: "6010102", department_name: "中心四部(男装)" },
    ),
    false,
  );
});

test("retail price scope requires both store and department", () => {
  assert.equal(isCenterCosmeticsRetailPriceScope(null, { department_code: "6010101" }), false);
  assert.equal(isCenterCosmeticsRetailPriceScope({ store_id: "1" }, null), false);
});
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
node --experimental-strip-types --test client/src/lib/sales-dashboard-drilldown.test.mjs
```

Expected: FAIL because `isCenterCosmeticsRetailPriceScope` is not exported.

- [ ] **Step 3: Implement the minimal pure predicate**

Append to `client/src/lib/sales-dashboard-drilldown.ts`:

```ts
type StoreScope = { store_id?: string | number | null; store_name?: string | null } | null | undefined;
type DepartmentScope = {
  department_code?: string | number | null;
  department_name?: string | null;
} | null | undefined;

function normalizeScopeName(value: unknown): string {
  return String(value ?? "").trim().replaceAll("（", "(").replaceAll("）", ")");
}

export function isCenterCosmeticsRetailPriceScope(store: StoreScope, department: DepartmentScope): boolean {
  if (!store || !department) return false;
  const storeId = String(store.store_id ?? "").trim();
  const departmentCode = String(department.department_code ?? "").trim();
  const storeMatches = ["1", "601"].includes(storeId) || normalizeScopeName(store.store_name) === "常州购物中心";
  const departmentMatches =
    departmentCode === "6010101" || normalizeScopeName(department.department_name) === "中心一部(化妆)";
  return storeMatches && departmentMatches;
}
```

- [ ] **Step 4: Run the scope tests and verify they pass**

Run the Step 2 command.

Expected: all `sales-dashboard-drilldown` tests PASS.

### Task 2: Return retail-price totals from the backend

**Files:**
- Modify: `tests/test_sales_ticket_filters.py`
- Modify: `python_app/routers/sales.py`

- [ ] **Step 1: Write failing group and ticket SQL tests**

Import `_group_level_sales_rows` and `group_tickets`, then add tests that capture generated SQL:

```python
def test_group_summary_sums_priced_sales_amount(self):
    captured = {}

    def fake_fetch(_db, sql, params):
        captured["sql"] = " ".join(sql.lower().split())
        captured["params"] = params
        return []

    with (
        patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
        patch.object(sales_router, "_table_exists", lambda _db, table: table in {"manaframe", "stores"}),
        patch.object(sales_router, "_fetch_mappings", fake_fetch),
    ):
        _group_level_sales_rows(
            object(),
            start_date="2026-07-01",
            end_date="2026-07-10",
            store_id="1",
            department_code="6010101",
            group_code=None,
            keyword=None,
            limit=200,
        )

    self.assertIn("coalesce(sum(s.sglsjje), 0) as priced_sales_amount", captured["sql"])

def test_group_tickets_sums_priced_sales_amount_by_billno(self):
    captured = {}

    def fake_fetch(_db, sql, params):
        captured["sql"] = " ".join(sql.lower().split())
        return []

    with (
        patch.object(sales_router, "require_permission", lambda *_args, **_kwargs: None),
        patch.object(sales_router, "load_business_scope", lambda *_args, **_kwargs: None),
        patch.object(sales_router, "_salegoodslist_table", lambda _db: "salegoodslist"),
        patch.object(sales_router, "_table_exists", lambda _db, _table: False),
        patch.object(sales_router, "_fetch_mappings", fake_fetch),
    ):
        asyncio.run(group_tickets("6010101035", db=object(), current_user=object()))

    self.assertIn("s.sglsjje", captured["sql"])
    self.assertIn("coalesce(sum(sglsjje), 0) as priced_sales_amount", captured["sql"])
    self.assertIn("tr.priced_sales_amount", captured["sql"])
```

- [ ] **Step 2: Run the two tests and verify they fail**

Run:

```bash
./.venv/bin/python -m unittest \
  tests.test_sales_ticket_filters.SalesTicketFilterTests.test_group_summary_sums_priced_sales_amount \
  tests.test_sales_ticket_filters.SalesTicketFilterTests.test_group_tickets_sums_priced_sales_amount_by_billno -v
```

Expected: both FAIL because the SQL does not yet select `priced_sales_amount`.

- [ ] **Step 3: Add the group aggregation**

In `_group_level_sales_rows`, insert after `quantity`:

```sql
COALESCE(SUM(s.sglsjje), 0) AS priced_sales_amount,
```

In the prior-only fallback row created by `_merge_group_summaries_same_period`, add:

```python
"priced_sales_amount": 0.0,
```

- [ ] **Step 4: Add the ticket aggregation**

In the `base` CTE of `group_tickets`, add `s.sglsjje`. In `ticket_rows`, add:

```sql
COALESCE(SUM(sglsjje), 0) AS priced_sales_amount,
```

In the final select, place this before `tr.effective_sales`:

```sql
tr.priced_sales_amount,
```

Update the endpoint docstring to state `零售价=sum(sglsjje)`.

- [ ] **Step 5: Run the backend tests**

Run:

```bash
./.venv/bin/python -m unittest tests.test_sales_ticket_filters -v
```

Expected: all tests PASS.

### Task 3: Build and test conditional Excel tables

**Files:**
- Create: `client/src/lib/export-sales-excel.test.mjs`
- Modify: `client/src/lib/export-sales-excel.ts`

- [ ] **Step 1: Write failing tests for group and ticket export tables**

Create a Node test importing `buildGroupExportTable` and `buildTicketExportTable`. Define these fixtures before the tests:

```js
const groupRows = [{
  group_code: "6010101035",
  group_name: "测试柜组",
  department_name: "中心一部(化妆)",
  ticket_count: 1,
  quantity: 2,
  priced_sales_amount: 1200,
  effective_sales: 900,
  net_profit: 90,
  ticket_margin: 0.1,
  net_margin: 0.1,
  same_period_ticket_count: 1,
  same_period_effective_sales: 800,
  same_period_net_profit: 80,
  same_period_margin: 0.1,
}];

const ticketRows = [{
  billno: "13000001",
  sale_date: "2026-07-10",
  sale_datetime: "2026-07-10 10:00:00",
  invoice_no: "1001",
  cashier: "001",
  quantity: 2,
  priced_sales_amount: 1200,
  effective_sales: 900,
  net_profit: 90,
  ticket_margin: 0.1,
  authorized_discount: 10,
  mzk: 0,
  lq: 0,
  consumption_point: 9,
  birthday_month_member_point: 0,
  transaction_type: "销售",
}];
```

Then assert:

```js
test("group export inserts retail price only when requested", () => {
  const withRetail = buildGroupExportTable(groupRows, true);
  assert.equal(withRetail[0][2], "零售价");
  assert.equal(withRetail[1][2], 1200);
  assert.equal(withRetail.at(-1)[2], 1200);

  const withoutRetail = buildGroupExportTable(groupRows, false);
  assert.equal(withoutRetail[0].includes("零售价"), false);
  assert.equal(withoutRetail[0][2], "本期销售收入");
});

test("ticket export inserts retail price before sales revenue", () => {
  const withRetail = buildTicketExportTable(ticketRows, true);
  assert.equal(withRetail[0][6], "零售价");
  assert.equal(withRetail[0][7], "销售收入");
  assert.equal(withRetail[1][6], 1200);
  assert.equal(withRetail.at(-1)[6], 1200);

  const withoutRetail = buildTicketExportTable(ticketRows, false);
  assert.equal(withoutRetail[0].includes("零售价"), false);
  assert.equal(withoutRetail[0][6], "销售收入");
});
```

- [ ] **Step 2: Run the export test and verify it fails**

Run:

```bash
node --experimental-strip-types --test client/src/lib/export-sales-excel.test.mjs
```

Expected: FAIL because the two table builders are not exported.

- [ ] **Step 3: Add conditional group export construction**

Add `priced_sales_amount: number` to `GroupSummaryExport`. Extract the current header/body/footer construction into:

```ts
export function buildGroupExportTable(
  rows: GroupSummaryExport[],
  includePricedSalesAmount = false,
): (string | number)[][] {
  const header: (string | number)[] = [
    "柜组名称", "柜组编码", "本期销售收入", "同期销售收入", "销售收入同比",
    "毛利", "同期毛利", "本期毛利率(%)", "同期毛利率(%)", "同期小票数",
  ];
  if (includePricedSalesAmount) header.splice(2, 0, "零售价");

  let pricedTotal = 0;
  let effectiveTotal = 0;
  let sameEffectiveTotal = 0;
  let profitTotal = 0;
  let sameProfitTotal = 0;
  let sameTicketTotal = 0;
  const body = rows.map((row) => {
    pricedTotal += n(row.priced_sales_amount);
    effectiveTotal += n(row.effective_sales);
    sameEffectiveTotal += n(row.same_period_effective_sales);
    profitTotal += n(row.net_profit);
    sameProfitTotal += n(row.same_period_net_profit);
    sameTicketTotal += n(row.same_period_ticket_count);
    const values: (string | number)[] = [
      row.group_name || row.group_code,
      row.group_code,
      n(row.effective_sales),
      n(row.same_period_effective_sales),
      yoyDisplay(n(row.effective_sales), n(row.same_period_effective_sales)),
      n(row.net_profit),
      n(row.same_period_net_profit),
      marginPctDisplay(row.ticket_margin ?? row.net_margin),
      marginPctDisplay(row.same_period_margin),
      n(row.same_period_ticket_count),
    ];
    if (includePricedSalesAmount) values.splice(2, 0, n(row.priced_sales_amount));
    return values;
  });
  const footer: (string | number)[] = [
    "合计", "", effectiveTotal, sameEffectiveTotal,
    yoyDisplay(effectiveTotal, sameEffectiveTotal), profitTotal, sameProfitTotal,
    effectiveTotal > 0 ? Math.round((profitTotal / effectiveTotal) * 10000) / 100 : 0,
    sameEffectiveTotal > 0 ? Math.round((sameProfitTotal / sameEffectiveTotal) * 10000) / 100 : 0,
    sameTicketTotal,
  ];
  if (includePricedSalesAmount) footer.splice(2, 0, pricedTotal);
  return [header, ...body, footer];
}
```

Change the writer signature to:

```ts
export function exportGroupsToExcel(
  rows: GroupSummaryExport[],
  startDate: string,
  endDate: string,
  options: { includePricedSalesAmount?: boolean } = {},
): void
```

and pass `buildGroupExportTable(rows, Boolean(options.includePricedSalesAmount))` to `writeWorkbook`.

- [ ] **Step 4: Add conditional ticket export construction**

Add `priced_sales_amount: number` to `TicketSummaryExport`. Extract the current table construction into:

```ts
export function buildTicketExportTable(
  rows: TicketSummaryExport[],
  includePricedSalesAmount = false,
): (string | number)[][] {
  const header: (string | number)[] = [
    "单据号", "日期", "销售类型", "小票号", "收银员", "商品数", "销售收入",
    "毛利", "毛利率(%)", "授权折扣", "面值卡(MZK)", "礼券(LQ)",
    "消费加积分", "生日月会员加积分",
  ];
  if (includePricedSalesAmount) header.splice(6, 0, "零售价");

  const totals = {
    quantity: 0, priced: 0, sales: 0, profit: 0, authorized: 0,
    mzk: 0, lq: 0, consumption: 0, birthday: 0,
  };
  const body = rows.map((row) => {
    totals.quantity += n(row.quantity);
    totals.priced += n(row.priced_sales_amount);
    totals.sales += n(row.effective_sales);
    totals.profit += n(row.net_profit);
    totals.authorized += n(row.authorized_discount);
    totals.mzk += n(row.mzk);
    totals.lq += n(row.lq);
    totals.consumption += n(row.consumption_point);
    totals.birthday += n(row.birthday_month_member_point);
    const values: (string | number)[] = [
      row.billno,
      String(row.sale_datetime || row.sale_date || "").trim() || "—",
      String(row.transaction_type || "").trim() || "—",
      row.invoice_no != null && `${row.invoice_no}` !== "" ? row.invoice_no : "—",
      row.cashier || "—",
      n(row.quantity),
      n(row.effective_sales),
      n(row.net_profit),
      marginPctDisplay(row.ticket_margin),
      n(row.authorized_discount), n(row.mzk), n(row.lq),
      n(row.consumption_point), n(row.birthday_month_member_point),
    ];
    if (includePricedSalesAmount) values.splice(6, 0, n(row.priced_sales_amount));
    return values;
  });
  const footer: (string | number)[] = [
    "合计", "", "", "", "", totals.quantity, totals.sales, totals.profit,
    totals.sales > 0 ? Math.round((totals.profit / totals.sales) * 10000) / 100 : 0,
    totals.authorized, totals.mzk, totals.lq, totals.consumption, totals.birthday,
  ];
  if (includePricedSalesAmount) footer.splice(6, 0, totals.priced);
  return [header, ...body, footer];
}
```

Add `includePricedSalesAmount?: boolean` to `exportTicketsToExcel` options and write the builder result.

- [ ] **Step 5: Run the export tests**

Run the Step 2 command.

Expected: both tests PASS and no `.xlsx` file is created because the tests call only pure builders.

### Task 4: Render and total the conditional columns

**Files:**
- Modify: `client/src/pages/sales-dashboard.tsx`
- Modify: `client/src/lib/sales-dashboard-drilldown.test.mjs`

- [ ] **Step 1: Add page-source contract assertions that initially fail**

In `sales-dashboard-drilldown.test.mjs`, read `../pages/sales-dashboard.tsx` and assert the page contains:

```js
assert.match(pageSource, /isCenterCosmeticsRetailPriceScope/);
assert.match(pageSource, /priced_sales_amount/);
assert.match(pageSource, />零售价</);
assert.match(pageSource, /includePricedSalesAmount/);
```

Run the drilldown test and confirm these new assertions FAIL.

- [ ] **Step 2: Add types and the shared visibility boolean**

Import `isCenterCosmeticsRetailPriceScope`. Add `priced_sales_amount: number` to `GroupSummary` and `TicketSummary`. Near other derived state, add:

```ts
const showPricedSalesAmount = isCenterCosmeticsRetailPriceScope(selectedStore, selectedDepartment);
```

- [ ] **Step 3: Include the field in group and ticket totals**

Add `priced_sales_amount` to each reducer accumulator and zero initializer:

```ts
priced_sales_amount: acc.priced_sales_amount + Number(row.priced_sales_amount || 0),
```

and:

```ts
priced_sales_amount: 0,
```

- [ ] **Step 4: Pass the visibility flag into both exports**

Change the group export call to:

```ts
exportGroupsToExcel(rows, currentStartDate, currentEndDate, {
  includePricedSalesAmount: showPricedSalesAmount,
});
```

Add to the ticket export options:

```ts
includePricedSalesAmount: showPricedSalesAmount,
```

- [ ] **Step 5: Render the group column and dynamic spans**

Immediately before the group “本期销售收入” header/cell/footer, conditionally render:

```tsx
{showPricedSalesAmount && <TableHead className="text-right">零售价</TableHead>}
```

```tsx
{showPricedSalesAmount && (
  <TableCell className="py-2 text-right">{money(row.priced_sales_amount)}</TableCell>
)}
```

```tsx
{showPricedSalesAmount && (
  <TableCell className="py-2 text-right font-semibold tabular-nums">
    {money(groupsTableTotals.priced_sales_amount)}
  </TableCell>
)}
```

Change the empty/loading row span from `9` to `showPricedSalesAmount ? 10 : 9`.

- [ ] **Step 6: Render the ticket column and dynamic spans**

Immediately before the ticket “销售收入” header/cell/footer, conditionally render the same structure using `row.priced_sales_amount` and `ticketsTableTotals.priced_sales_amount`.

Change the empty/loading row span from `14` to `showPricedSalesAmount ? 15 : 14`.

- [ ] **Step 7: Run frontend tests and build**

Run:

```bash
node --experimental-strip-types --test \
  client/src/lib/sales-dashboard-drilldown.test.mjs \
  client/src/lib/export-sales-excel.test.mjs
npm --prefix client run build
```

Expected: all Node tests PASS; TypeScript and Vite build complete successfully.

### Task 5: Regression and browser verification

**Files:**
- Verify only; no expected code changes.

- [ ] **Step 1: Run the focused regression suite**

```bash
./.venv/bin/python -m unittest tests.test_sales_ticket_filters -v
node --experimental-strip-types --test \
  client/src/lib/sales-dashboard-drilldown.test.mjs \
  client/src/lib/export-sales-excel.test.mjs
npm --prefix client run build
```

Expected: every command exits `0`.

- [ ] **Step 2: Check patch boundaries**

```bash
git diff --check -- \
  python_app/routers/sales.py \
  tests/test_sales_ticket_filters.py \
  client/src/lib/sales-dashboard-drilldown.ts \
  client/src/lib/sales-dashboard-drilldown.test.mjs \
  client/src/lib/export-sales-excel.ts \
  client/src/lib/export-sales-excel.test.mjs \
  client/src/pages/sales-dashboard.tsx
```

Expected: no whitespace errors. Review `git diff` and confirm unrelated pre-existing hunks remain intact.

- [ ] **Step 3: Verify the cosmetics path in the local browser**

Open the local ShopView sales dashboard and drill through:

```text
门店 → 常州购物中心 → 中心一部（化妆） → 柜组 → 小票
```

Confirm:

- 柜组表 shows “零售价” before “本期销售收入”.
- Group row values and the footer total render as currency.
- Ticket table shows “零售价” before “销售收入”.
- Ticket row values and the footer total render as currency.
- Group and ticket Excel exports contain “零售价” in the same position.

- [ ] **Step 4: Verify a non-target department**

Return to departments and open any department other than “中心一部（化妆）”. Confirm neither the group table nor its Excel export contains “零售价”.

- [ ] **Step 5: Record final evidence**

Report the exact files changed, commands run, pass counts, build result, browser route checked, and any verification blocked by unavailable local services. Do not claim deployed port `8020` was changed unless a deployment was separately performed.
