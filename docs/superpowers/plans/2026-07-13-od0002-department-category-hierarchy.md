# OD0002“部门（含品类）”Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 OD0002 新增“部门（含品类）”在线页签和 Excel 同名工作表，按门店、部门、区域、品类展示明细及区域/部门小计，同时保持现有六个维度不变。

**Architecture:** 在 OD0002 现有 `base` CTE 上新增 `department_categories` 聚合，SQL 保留部门、区域、品类结构字段。后端把品类明细确定性展开为品类行、区域小计和部门小计，并将同一响应交给页面及 Excel；前端和工作簿生成器只负责展示，不重新统计。

**Tech Stack:** FastAPI、SQLAlchemy text SQL、pytest、React、TypeScript、Node test runner、openpyxl、Vite。

---

## File map

- Modify `python_app/services/od0002_report.py`: 新维度 SQL、结构字段、层级归并、总计。
- Modify `tests/test_od0002_report.py`: SQL 粒度、跨部门隔离、小计与总计测试。
- Modify `client/src/lib/od0002-report.ts`: 新维度类型、页签和层级行辅助函数。
- Modify `client/src/lib/od0002-report.contract.ts`: 响应契约样例增加新维度。
- Modify `client/src/lib/od0002-report.test.mjs`: 页签顺序、层级行和页面接线测试。
- Modify `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`: “部门（含品类）”层级表格。
- Modify `python_app/services/od0002_excel.py`: “部门（含品类）”工作表及层级样式。
- Modify `tests/test_od0002_excel.py`: Sheet 顺序、十三列、层级行、合计和空数据测试。

### Task 1: Add the backend department-category dimension

**Files:**
- Modify: `tests/test_od0002_report.py`
- Modify: `python_app/services/od0002_report.py`

- [ ] **Step 1: Write failing SQL and hierarchy tests**

Add tests that require the new CTE, structured fields, deterministic hierarchy rows and non-duplicated totals:

```python
def test_report_query_adds_department_category_dimension_without_merging_departments():
    sql, _ = build_report_query(
        date(2026, 1, 1), date(2026, 1, 31),
        date(2025, 1, 1), date(2025, 1, 31), TrustedScopeSql(""), {},
    )
    compact = " ".join(sql.lower().split())
    block = compact.split("department_categories as", 1)[1].split("),", 1)[0]
    assert "'department_categories' as dimension_type" in block
    assert "department_code" in block and "area_code" in block and "category_code" in block
    assert "group by store_code, store_name, department_code, department_name" in block
    assert "area_code, area_name, category_code, category_name" in block
    assert "union all select * from department_categories" in compact


def test_normalize_rows_builds_category_area_and_department_rows_in_order():
    rows = [
        {"dimension_type": "department_categories", "store_code": "603", "store_name": "商城",
         "department_code": "6030102", "department_name": "新世纪二部",
         "area_code": "A1", "area_name": "女装区", "category_code": "C2",
         "category_name": "中淑女装", "dimension_code": "C2", "dimension_name": "中淑女装",
         "sales_current": 50, "profit_current": 5, "sales_prior": 40, "profit_prior": 4},
        {"dimension_type": "department_categories", "store_code": "603", "store_name": "商城",
         "department_code": "6030102", "department_name": "新世纪二部",
         "area_code": "A1", "area_name": "女装区", "category_code": "C1",
         "category_name": "中式女装", "dimension_code": "C1", "dimension_name": "中式女装",
         "sales_current": 30, "profit_current": 3, "sales_prior": 20, "profit_prior": 2},
    ]
    dimensions, _ = normalize_rows(rows)
    hierarchy = dimensions["department_categories"]
    assert [row["row_type"] for row in hierarchy] == [
        "category", "category", "area_subtotal", "department_subtotal"
    ]
    assert [row["category_code"] for row in hierarchy[:2]] == ["C1", "C2"]
    assert hierarchy[2]["metrics"]["sales_current"] == 80
    assert hierarchy[3]["metrics"]["sales_current"] == 80


def test_load_report_total_counts_only_department_category_detail_rows():
    rows = [{
        "dimension_type": "department_categories", "store_code": "603", "store_name": "商城",
        "department_code": "D1", "department_name": "一部", "area_code": "A1",
        "area_name": "女装区", "category_code": "C1", "category_name": "女装",
        "dimension_code": "C1", "dimension_name": "女装",
        "sales_current": 100, "profit_current": 20, "sales_prior": 80, "profit_prior": 16,
    }]
    payload = load_od0002_report(
        FakeDb(rows), TrustedScopeSql(""), {}, start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31), prior_start_date=date(2025, 1, 1),
        prior_end_date=date(2025, 1, 31),
    )
    assert payload["totals"]["department_categories"]["sales_current"] == 100


def test_department_category_reuses_base_permission_and_department_filter():
    scope = " AND s.sglmarket::text = ANY(:scope_allow_store)"
    sql, params = build_report_query(
        date(2026, 1, 1), date(2026, 1, 31),
        date(2025, 1, 1), date(2025, 1, 31), TrustedScopeSql(scope),
        {"scope_allow_store": ["603"]}, selected_store="603",
        selected_department="6030102",
    )
    base = " ".join(sql.split()).split("base AS", 1)[1].split("), departments AS", 1)[0]
    assert scope in base
    assert "s.sglmarket::text = :selected_store" in base
    assert "= UPPER(:selected_department)" in base
    assert params["scope_allow_store"] == ["603"]
    assert params["selected_department"] == "6030102"
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python_app/.venv/bin/pytest tests/test_od0002_report.py -q`

Expected: FAIL because `department_categories` is absent from SQL and `DIMENSION_TYPES`.

- [ ] **Step 3: Add the SQL dimension and structured union columns**

In `od0002_report.py`, add `"department_categories"` after `"departments"` in `DIMENSION_TYPES`. Add a CTE grouped by the complete business key:

```sql
department_categories AS (
  SELECT 'department_categories' AS dimension_type, store_code, store_name,
         category_code AS dimension_code, category_name AS dimension_name,
         department_code, department_name, area_code, area_name,
         category_code, category_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior
  FROM base
  GROUP BY store_code, store_name, department_code, department_name,
           area_code, area_name, category_code, category_name
)
```

Give the other dimension and quality CTEs six compatible nullable text columns and add `UNION ALL SELECT * FROM department_categories` immediately after departments. Keep selected store, department and permission predicates inside the existing `base` CTE.

- [ ] **Step 4: Implement one backend hierarchy builder**

Add a helper that recalculates ratios from summed sales/profit inputs:

```python
def _combined_metrics(rows: Iterable[Mapping[str, Any]]) -> dict[str, float | None]:
    items = list(rows)
    return metric_triplet(
        sum(_number(row["metrics"].get("sales_current")) for row in items),
        sum(_number(row["metrics"].get("profit_current")) for row in items),
        sum(_number(row["metrics"].get("sales_prior")) for row in items),
        sum(_number(row["metrics"].get("profit_prior")) for row in items),
    )
```

Create `_build_department_category_hierarchy(rows)` that sorts by store, `department_display_sort_key`, area code/name, category code/name; emits copied `category` rows, then an `area_subtotal` row per area and a `department_subtotal` row per department. Preserve store and relevant parent identifiers on subtotal rows and set lower-level identifiers to `None`.

In `normalize_rows`, include hierarchy fields for `department_categories`, build the hierarchy after reading all SQL rows, and leave existing dimensions unchanged.

In `load_od0002_report`, compute `totals.department_categories` only from `row_type == "category"`; other dimension totals continue to use every row. Attach the same total to all hierarchy rows.

- [ ] **Step 5: Run report tests and verify GREEN**

Run: `python_app/.venv/bin/pytest tests/test_od0002_report.py -q`

Expected: all focused tests PASS; the PostgreSQL integration test may remain skipped when `OD0002_TEST_DATABASE_URL` is unset.

- [ ] **Step 6: Commit backend dimension**

```bash
git add python_app/services/od0002_report.py tests/test_od0002_report.py
git commit -m "feat: add OD0002 department category hierarchy"
```

### Task 2: Add the frontend contract and hierarchy helpers

**Files:**
- Modify: `client/src/lib/od0002-report.test.mjs`
- Modify: `client/src/lib/od0002-report.ts`
- Modify: `client/src/lib/od0002-report.contract.ts`

- [ ] **Step 1: Write failing contract tests**

```javascript
test("OD0002 exposes department with categories after department", () => {
  assert.deepEqual(
    OD0002_TABS.map((tab) => tab.label),
    ["分店", "部门", "部门（含品类）", "区域", "品类", "柜组", "楼层"],
  );
  assert.equal(OD0002_TABS[2].key, "department_categories");
});

test("department category rows expose four hierarchy identifiers", async () => {
  const module = await import("./od0002-report.ts");
  assert.equal(module.isOd0002DepartmentCategoryTab("department_categories"), true);
  assert.deepEqual(module.OD0002_HIERARCHY_COLUMNS, ["store", "department", "area", "category"]);
});
```

Extend the static page-source test to require `department_code`, `area_code`, `category_code`, `row_type`, and the subtotal labels.

- [ ] **Step 2: Run the Node test and verify RED**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs`

Expected: FAIL because the new dimension and helpers do not exist.

- [ ] **Step 3: Extend TypeScript types and response fixture**

```typescript
export type Od0002HierarchyRowType = "category" | "area_subtotal" | "department_subtotal";

export interface Od0002Row {
  store_code: string | null;
  store_name: string | null;
  dimension_code: string | null;
  dimension_name: string | null;
  department_code?: string | null;
  department_name?: string | null;
  area_code?: string | null;
  area_name?: string | null;
  category_code?: string | null;
  category_name?: string | null;
  row_type?: Od0002HierarchyRowType;
  metrics: Od0002Metric;
  total: Od0002Metric;
}

export const OD0002_HIERARCHY_COLUMNS = ["store", "department", "area", "category"] as const;
export const isOd0002DepartmentCategoryTab = (tab: Od0002DimensionKey) =>
  tab === "department_categories";
```

Add `"department_categories"` to `Od0002DimensionKey` and after departments in `OD0002_TABS`. Add category, area subtotal and department subtotal rows to `od0002ResponseContract.dimensions.department_categories`, plus its total. Keep the original six dimension keys and their fixture rows unchanged so the contract proves backward compatibility.

- [ ] **Step 4: Run Node and TypeScript tests and verify GREEN**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs && npx tsc --noEmit`

Expected: PASS with no type errors.

- [ ] **Step 5: Commit frontend contract**

```bash
git add client/src/lib/od0002-report.ts client/src/lib/od0002-report.contract.ts client/src/lib/od0002-report.test.mjs
git commit -m "feat: define OD0002 hierarchy contract"
```

### Task 3: Render the online “部门（含品类）” tab

**Files:**
- Modify: `client/src/lib/od0002-report.test.mjs`
- Modify: `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`

- [ ] **Step 1: Add a failing page contract test**

```javascript
test("OD0002 page renders the department category hierarchy", async () => {
  const source = await readFile(new URL("../pages/sales-reports/od0002-sales-gross-profit.tsx", import.meta.url), "utf8");
  assert.match(source, /activeTab === "department_categories"/);
  for (const label of ["门店", "部门", "区域", "品类", "区域小计", "部门小计"]) {
    assert.match(source, new RegExp(label));
  }
  assert.match(source, /row\.department_name/);
  assert.match(source, /row\.area_name/);
  assert.match(source, /row\.category_name/);
});
```

- [ ] **Step 2: Run the page test and verify RED**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs`

Expected: FAIL because the page only renders the generic dimension table.

- [ ] **Step 3: Add the dedicated hierarchy table**

When `activeTab === "department_categories"`, render a table with identifier headers 门店、部门、区域、品类 plus the existing nine metric headers. Use a small local cell component that renders name and code on two lines.

Use `row.row_type` for style and labels:

```typescript
const hierarchyLabel = row.row_type === "area_subtotal"
  ? "区域小计"
  : row.row_type === "department_subtotal"
    ? "部门小计"
    : null;
const subtotalClass = row.row_type === "category" ? "" : "bg-slate-50 font-semibold";
```

Show the store column only when `submitted.storeId === OD0002_ALL_STORES`. Render blank lower-level cells on subtotal rows. Reuse `metricCells`, `yoyColorClass`, `formatMoneyWan`, and `formatPercent`; use `totals.department_categories` in the existing footer.

Keep the generic table path unchanged for the other six tabs. Pagination remains limited to the existing `groups` tab.

- [ ] **Step 4: Run focused frontend verification and verify GREEN**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs && npx tsc --noEmit`

Expected: PASS.

Confirm the existing generic-page assertions for 分店、部门、区域、品类、柜组、楼层 remain green; the new branch must not replace their headers, metric cells, totals or group pagination.

- [ ] **Step 5: Commit page rendering**

```bash
git add client/src/pages/sales-reports/od0002-sales-gross-profit.tsx client/src/lib/od0002-report.test.mjs
git commit -m "feat: render OD0002 department category tab"
```

### Task 4: Add the Excel “部门（含品类）” sheet

**Files:**
- Modify: `tests/test_od0002_excel.py`
- Modify: `python_app/services/od0002_excel.py`

- [ ] **Step 1: Extend the workbook fixture and write failing tests**

Add `department_categories` rows to `sample_report` and require:

```python
assert workbook.sheetnames == [
    "分店", "部门", "部门（含品类）", "区域", "品类", "柜组", "楼层", "报表说明"
]
sheet = workbook["部门（含品类）"]
assert sheet["A1"].value == "OD0002 门店销售毛利汇总表（部门（含品类））"
assert [sheet.cell(6, column).value for column in range(1, 5)] == ["门店", "部门", "区域", "品类"]
assert "商城" in sheet["A8"].value and "603" in sheet["A8"].value
assert "新世纪二部" in sheet["B8"].value and "6030102" in sheet["B8"].value
assert "女装区" in sheet["C8"].value
assert "中式女装" in sheet["D8"].value
assert sheet["C10"].value.startswith("女装区小计")
assert sheet["B11"].value.startswith("新世纪二部小计")
assert sheet["A12"].value == "合计"
```

Also assert subtotal fills/fonts, formula-like hierarchy text escaping, freeze pane `A8`, thirteen columns, and a valid empty hierarchy Sheet.

- [ ] **Step 2: Run Excel tests and verify RED**

Run: `python_app/.venv/bin/pytest tests/test_od0002_excel.py -q`

Expected: FAIL because the workbook has no “部门（含品类）” Sheet.

- [ ] **Step 3: Add a dedicated hierarchy worksheet writer**

Keep `SHEETS` for the generic dimensions and insert the hierarchy sheet after “部门”. Add:

```python
def _hierarchy_text(name: Any, code: Any, *, suffix: str = "") -> Any:
    safe_name = str(name or "未匹配") + suffix
    safe_code = str(code or "—")
    return _safe_excel_text(f"{safe_name}\n{safe_code}")
```

Create `_write_department_category_sheet(sheet, report)` using the existing title/date rows and nine metric columns. Its four identifier headers are 门店、部门、区域、品类. For category rows write all four hierarchy cells; for `area_subtotal` write the area cell with “小计” and leave category blank; for `department_subtotal` write the department cell with “小计” and leave area/category blank. Use `_write_data_row` for metrics, apply wrap text to A:D, and apply the existing total fill to subtotal rows.

Write the final total from `totals.department_categories` exactly once. Keep `freeze_panes = "A8"`, thirteen columns, and formula-text protection.

- [ ] **Step 4: Run Excel tests and verify GREEN**

Run: `python_app/.venv/bin/pytest tests/test_od0002_excel.py -q`

Expected: PASS.

- [ ] **Step 5: Commit workbook support**

```bash
git add python_app/services/od0002_excel.py tests/test_od0002_excel.py
git commit -m "feat: export OD0002 department category sheet"
```

### Task 5: Run regression and production verification

**Files:**
- Verify all modified files from Tasks 1–4.

- [ ] **Step 1: Run focused backend and frontend tests**

```bash
python_app/.venv/bin/pytest tests/test_od0002_report.py tests/test_od0002_excel.py -q
cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs
```

Expected: all tests PASS, with only the configured PostgreSQL integration skip allowed.

- [ ] **Step 2: Run broader backend regression tests**

Run: `python_app/.venv/bin/pytest tests test -q`

Expected: all tests PASS except existing environment-dependent skips.

- [ ] **Step 3: Run frontend verification**

Run: `cd client && node --test --experimental-strip-types src/lib/*.test.mjs && npx tsc --noEmit && npm run build`

Expected: Node tests PASS, TypeScript exits 0, and Vite production build completes.

- [ ] **Step 4: Inspect the final diff for scope and whitespace**

```bash
git diff --check HEAD~4..HEAD
git status --short
git log -5 --oneline
```

Expected: no whitespace errors; only planned OD0002 files are modified; worktree is clean.

- [ ] **Step 5: Complete the development branch**

Invoke `superpowers:finishing-a-development-branch`, report verification evidence, and offer merge/PR/keep/cleanup choices without altering the user’s main worktree until they choose.
