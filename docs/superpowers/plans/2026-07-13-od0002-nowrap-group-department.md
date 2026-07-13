# OD0002名称不折行与柜组部门 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 OD0002 层级名称固定为“名称一行、编码一行”且名称不折行，并让柜组维度在在线页面和 Excel 中同时展示所属部门。

**Architecture:** 后端仍以现有权限过滤后的 `base` 数据为唯一事实来源，只把 `groups` 聚合粒度扩展为门店、部门、柜组并透传部门字段。前端复用一个不折行的层级单元格组件，柜组页签按查询范围展示门店、部门、柜组；Excel 为柜组增加专用十五列写入器，其他页签和工作表维持原结构。

**Tech Stack:** FastAPI、SQLAlchemy text SQL、PostgreSQL、pytest、React、TypeScript、Tailwind CSS、Node test runner、openpyxl、Vite。

**Design:** `docs/superpowers/specs/2026-07-13-od0002-nowrap-group-department-design.md`

---

## 文件结构

- Modify `python_app/services/od0002_report.py`：扩展柜组 SQL 粒度并在标准化响应中保留部门字段。
- Modify `tests/test_od0002_report.py`：锁定柜组按部门分组、同编码跨部门不合并和字段透传行为。
- Modify `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`：统一两行不折行组件，给柜组表增加部门列。
- Modify `client/src/lib/od0002-report.test.mjs`：验证不折行样式、柜组部门列及单门店/多门店结构。
- Modify `python_app/services/od0002_excel.py`：增加柜组十五列专用表头和数据写入逻辑。
- Modify `tests/test_od0002_excel.py`：验证柜组列顺序、格式、空数据和公式注入防护。

### Task 1: 后端柜组按部门聚合并透传部门字段

**Files:**
- Modify: `tests/test_od0002_report.py`
- Modify: `python_app/services/od0002_report.py:394-406,544-609`

- [ ] **Step 1: 写入柜组 SQL 粒度和响应字段的失败测试**

在 `tests/test_od0002_report.py` 增加：

```python
def test_group_query_aggregates_by_store_department_and_group():
    sql, _ = build_report_query(
        date(2026, 1, 1), date(2026, 1, 31),
        date(2025, 1, 1), date(2025, 1, 31),
        TrustedScopeSql(""), {},
    )
    compact = " ".join(sql.lower().split())
    block = compact.split("groups as (", 1)[1].split("), floors as", 1)[0]

    assert "department_code, department_name" in block
    assert (
        "group by store_code, store_name, department_code, department_name, "
        "group_code, group_name"
    ) in block


def test_normalize_rows_keeps_group_department_and_does_not_merge_duplicate_group_codes():
    rows = [
        {
            "dimension_type": "groups", "store_code": "603", "store_name": "商城",
            "department_code": "6030101", "department_name": "新世纪一部",
            "dimension_code": "0105", "dimension_name": "L'oreal欧莱雅厅",
            "sales_current": 100, "profit_current": 10,
            "sales_prior": 80, "profit_prior": 8,
        },
        {
            "dimension_type": "groups", "store_code": "603", "store_name": "商城",
            "department_code": "6030102", "department_name": "新世纪二部",
            "dimension_code": "0105", "dimension_name": "同编码测试厅",
            "sales_current": 60, "profit_current": 6,
            "sales_prior": 50, "profit_prior": 5,
        },
    ]

    dimensions, _quality = normalize_rows(rows)

    assert [
        (row["department_code"], row["department_name"], row["dimension_code"])
        for row in dimensions["groups"]
    ] == [
        ("6030101", "新世纪一部", "0105"),
        ("6030102", "新世纪二部", "0105"),
    ]
```

- [ ] **Step 2: 运行测试并确认按当前实现失败**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_od0002_report.py::test_group_query_aggregates_by_store_department_and_group \
  tests/test_od0002_report.py::test_normalize_rows_keeps_group_department_and_does_not_merge_duplicate_group_codes \
  -q
```

Expected: 两个测试均 `FAILED`；SQL 中部门字段仍为 `NULL`，标准化柜组行中还没有 `department_code`。

- [ ] **Step 3: 最小修改柜组 CTE 与标准化逻辑**

将 `python_app/services/od0002_report.py` 的 `groups AS` 替换为：

```python
groups AS (
  SELECT 'groups' AS dimension_type, store_code, store_name,
         group_code AS dimension_code, group_name AS dimension_name,
         department_code, department_name,
         NULL::text AS area_code, NULL::text AS area_name,
         NULL::text AS category_code, NULL::text AS category_name,
         SUM(sales_current) AS sales_current, SUM(profit_current) AS profit_current,
         SUM(sales_prior) AS sales_prior, SUM(profit_prior) AS profit_prior
  FROM base
  GROUP BY store_code, store_name, department_code, department_name,
           group_code, group_name
),
```

把 `normalize_rows` 中层级字段复制逻辑改为：

```python
        if dimension_type in ("department_categories", "groups"):
            normalized.update(
                {
                    "department_code": row.get("department_code"),
                    "department_name": row.get("department_name"),
                }
            )
        if dimension_type == "department_categories":
            normalized.update(
                {
                    "area_code": row.get("area_code"),
                    "area_name": row.get("area_name"),
                    "category_code": row.get("category_code"),
                    "category_name": row.get("category_name"),
                }
            )
```

- [ ] **Step 4: 运行后端 OD0002 测试并确认通过**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py -q`

Expected: 文件内测试全部 `PASSED`，仅保留已有的可选数据库测试 `SKIPPED`。

- [ ] **Step 5: 提交后端改动**

```bash
git add python_app/services/od0002_report.py tests/test_od0002_report.py
git commit -m "feat: include departments in OD0002 groups"
```

### Task 2: 在线层级固定两行且柜组展示部门

**Files:**
- Modify: `client/src/lib/od0002-report.test.mjs`
- Modify: `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx:71-79,275-373`

- [ ] **Step 1: 写入页面结构的失败测试**

在 `client/src/lib/od0002-report.test.mjs` 增加：

```javascript
test("OD0002 hierarchy values do not wrap and groups render department and group columns", async () => {
  const source = await readFile(
    new URL("../pages/sales-reports/od0002-sales-gross-profit.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /function HierarchyValue[\s\S]*whitespace-nowrap/);
  assert.match(source, /activeTab === "groups"[\s\S]*>部门</);
  assert.match(source, /activeTab === "groups" \? "柜组" : "维度"/);
  assert.match(source, /name=\{row\.department_name\}[\s\S]*code=\{row\.department_code\}/);
  assert.match(source, /name=\{row\.dimension_name\}[\s\S]*code=\{row\.dimension_code\}/);
  assert.match(source, /visible\.includes\("store"\)[\s\S]*HierarchyValue/);
});
```

- [ ] **Step 2: 运行测试并确认当前页面未满足要求**

Run: `cd client && node --test --experimental-strip-types src/lib/od0002-report.test.mjs`

Expected: 新测试 `FAILED`，错误指出缺少 `whitespace-nowrap` 或柜组部门列。

- [ ] **Step 3: 让层级值固定两行且每行不折行**

将 `HierarchyValue` 替换为：

```tsx
function HierarchyValue({ name, code }: { name?: string | null; code?: string | null }) {
  if (!name && !code) return null;
  return (
    <div className="min-w-[8rem] whitespace-nowrap">
      <div className="font-medium whitespace-nowrap">{name || "未匹配"}</div>
      <div className="text-xs text-muted-foreground whitespace-nowrap">{code || "—"}</div>
    </div>
  );
}
```

这使“欧美进口品”和 `0101` 固定占两行，表格宽度不足时由现有 `overflow-auto` 容器横向滚动。

- [ ] **Step 4: 在通用表分支给柜组增加部门列**

将通用表头的标识列改为：

```tsx
{visible.includes("store") && <TableHead rowSpan={2}>门店</TableHead>}
{activeTab === "groups" && <TableHead rowSpan={2}>部门</TableHead>}
<TableHead rowSpan={2}>{activeTab === "groups" ? "柜组" : "维度"}</TableHead>
```

将通用表体的标识单元格改为：

```tsx
<TableRow key={`${row.store_code ?? "all"}-${row.department_code ?? "department"}-${row.dimension_code ?? row.dimension_name ?? index}`}>
  {visible.includes("store") && (
    <TableCell className="py-2">
      <HierarchyValue name={row.store_name} code={row.store_code} />
    </TableCell>
  )}
  {activeTab === "groups" && (
    <TableCell className="py-2">
      <HierarchyValue name={row.department_name} code={row.department_code} />
    </TableCell>
  )}
  <TableCell className="py-2">
    <HierarchyValue name={row.dimension_name} code={row.dimension_code} />
  </TableCell>
  {metricCells(row.metrics).map((cell, cellIndex) => (
    <TableCell
      key={cellIndex}
      className={`py-2 text-right tabular-nums ${cell.isYoy ? yoyColorClass(cell.rawValue) : ""}`}
    >
      {cell.value}
    </TableCell>
  ))}
</TableRow>
```

在通用表合计行中增加柜组专用的部门空单元格：

```tsx
{visible.includes("store") && <TableCell className="py-2" />}
{activeTab === "groups" && <TableCell className="py-2" />}
<TableCell className="py-2">合计</TableCell>
```

- [ ] **Step 5: 运行前端测试和类型检查**

Run:

```bash
cd client && \
node --test --experimental-strip-types src/lib/od0002-report.test.mjs && \
npx tsc --noEmit
```

Expected: Node 测试全部 `PASSED`，TypeScript 退出码为 `0`。

- [ ] **Step 6: 提交在线页面改动**

```bash
git add client/src/lib/od0002-report.test.mjs client/src/pages/sales-reports/od0002-sales-gross-profit.tsx
git commit -m "feat: show OD0002 group departments online"
```

### Task 3: Excel柜组工作表增加部门列

**Files:**
- Modify: `tests/test_od0002_excel.py`
- Modify: `python_app/services/od0002_excel.py:31-145,226-238`

- [ ] **Step 1: 给测试样本补充柜组部门并写入失败测试**

在 `sample_report` 构造完通用维度后增加：

```python
    if not empty:
        dimensions["groups"][0].update(
            {
                "department_code": "6010101",
                "department_name": "一店一部(化妆)",
                "dimension_code": "6010101005",
                "dimension_name": "L'oreal欧莱雅厅",
            }
        )
```

在 `tests/test_od0002_excel.py` 增加：

```python
def test_group_sheet_has_department_before_group_and_fifteen_columns():
    from python_app.services.od0002_excel import build_od0002_workbook

    workbook = load_workbook(BytesIO(build_od0002_workbook(sample_report())))
    sheet = workbook["柜组"]

    assert sheet["A1"].value == "OD0002 门店销售毛利汇总表（柜组）"
    assert "A1:O1" in {str(item) for item in sheet.merged_cells.ranges}
    assert [sheet.cell(6, column).value for column in range(1, 7)] == [
        "门店编码", "门店名称", "部门编码", "部门名称", "柜组编码", "柜组名称",
    ]
    assert [sheet.cell(8, column).value for column in range(1, 7)] == [
        "601", "一店", "6010101", "一店一部(化妆)", "6010101005", "L'oreal欧莱雅厅",
    ]
    assert sheet["G8"].value == 12
    assert sheet["I8"].number_format == "0.00%"
    assert sheet.max_column == 15
    assert sheet.freeze_panes == "A8"


def test_empty_group_sheet_keeps_fifteen_columns_and_total():
    from python_app.services.od0002_excel import build_od0002_workbook

    workbook = load_workbook(BytesIO(build_od0002_workbook(sample_report(empty=True))))
    sheet = workbook["柜组"]

    assert sheet["F6"].value == "柜组名称"
    assert sheet["A8"].value == "合计"
    assert sheet.max_column == 15


def test_group_sheet_escapes_formula_like_department_and_group_text():
    from python_app.services.od0002_excel import build_od0002_workbook

    report = sample_report()
    report["dimensions"]["groups"][0].update(
        {
            "department_code": "=1+1",
            "department_name": "+SUM(A1:A2)",
            "dimension_code": "-2+3",
            "dimension_name": "@cmd",
        }
    )
    workbook = load_workbook(BytesIO(build_od0002_workbook(report)), data_only=False)
    sheet = workbook["柜组"]

    for column in range(3, 7):
        cell = sheet.cell(8, column)
        assert cell.data_type == "s"
        assert cell.value.startswith("'")
```

- [ ] **Step 2: 运行新测试并确认十三列旧结构失败**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_od0002_excel.py::test_group_sheet_has_department_before_group_and_fifteen_columns \
  tests/test_od0002_excel.py::test_empty_group_sheet_keeps_fifteen_columns_and_total \
  tests/test_od0002_excel.py::test_group_sheet_escapes_formula_like_department_and_group_text \
  -q
```

Expected: 三个测试均 `FAILED`，旧柜组工作表只有十三列且没有部门字段。

- [ ] **Step 3: 让数据行格式支持可变标识列数**

将 `_write_data_row` 替换为：

```python
def _write_data_row(
    sheet,
    row_number: int,
    values: list[Any],
    *,
    identifier_columns: int = 4,
    total: bool = False,
) -> None:
    for column, value in enumerate(values, 1):
        if column <= identifier_columns:
            value = _safe_excel_text(value)
        cell = sheet.cell(row_number, column, value)
        cell.border = BORDER
        metric_column = column - identifier_columns
        if metric_column in (1, 2, 4, 5):
            cell.number_format = "0.00"
        elif metric_column >= 3:
            cell.number_format = "0.00%"
        if total:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D9EAF7")
```

- [ ] **Step 4: 增加柜组专用十五列表头和工作表写入器**

在 `_write_headers` 后增加：

```python
def _write_group_headers(sheet) -> None:
    sheet.merge_cells("A5:F5")
    sheet["A5"] = "维度"
    for start, end, label in ((7, 9, "销售收入"), (10, 12, "毛利额"), (13, 15, "毛利率")):
        sheet.merge_cells(start_row=5, start_column=start, end_row=5, end_column=end)
        sheet.cell(5, start).value = label

    identifiers = (
        "门店编码", "门店名称", "部门编码", "部门名称", "柜组编码", "柜组名称",
    )
    for column, label in enumerate(identifiers, 1):
        sheet.merge_cells(start_row=6, start_column=column, end_row=7, end_column=column)
        sheet.cell(6, column).value = label
    for group_start in (7, 10, 13):
        for offset, label in enumerate(("本期", "同期", "同比")):
            sheet.cell(6, group_start + offset).value = label
            sheet.cell(7, group_start + offset).value = (
                "万元" if group_start < 13 and offset < 2 else "%"
            )

    for row in range(5, 8):
        for column in range(1, 16):
            cell = sheet.cell(row, column)
            cell.fill = PatternFill("solid", fgColor=BLUE)
            cell.font = Font(color=WHITE, bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = BORDER
```

在 `_write_report_sheet` 后增加：

```python
def _write_group_sheet(sheet, report: dict[str, Any]) -> None:
    dates = report["dates"]
    sheet.merge_cells("A1:O1")
    sheet["A1"] = "OD0002 门店销售毛利汇总表（柜组）"
    sheet["A1"].font = Font(size=16, bold=True)
    sheet["A1"].alignment = Alignment(horizontal="center")
    sheet.merge_cells("A2:O2")
    sheet["A2"] = f"本期：{_date_text(dates['start_date'])} 至 {_date_text(dates['end_date'])}"
    sheet.merge_cells("A3:O3")
    sheet["A3"] = f"同期：{_date_text(dates['prior_start_date'])} 至 {_date_text(dates['prior_end_date'])}"
    _write_group_headers(sheet)

    row_number = 8
    for row in report.get("dimensions", {}).get("groups", []):
        identifiers = [
            row.get("store_code"), row.get("store_name"),
            row.get("department_code"), row.get("department_name"),
            row.get("dimension_code"), row.get("dimension_name"),
        ]
        _write_data_row(
            sheet, row_number,
            identifiers + _metric_values(row.get("metrics", {})),
            identifier_columns=6,
        )
        row_number += 1

    total = report.get("totals", {}).get("groups", {})
    _write_data_row(
        sheet, row_number,
        ["合计", None, None, None, None, None] + _metric_values(total),
        identifier_columns=6, total=True,
    )
    sheet.freeze_panes = "A8"
    widths = (14, 18, 16, 24, 18, 28) + (14,) * 9
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width
```

- [ ] **Step 5: 让工作簿构建只对柜组使用专用写入器**

将 `_build_od0002_workbook` 的循环改为：

```python
    for label, dimension_key in SHEETS:
        sheet = workbook.create_sheet(label)
        if dimension_key == "groups":
            _write_group_sheet(sheet, report)
        else:
            _write_report_sheet(sheet, report, label, dimension_key)
        if dimension_key == "departments":
            _write_department_category_sheet(workbook.create_sheet("部门（含品类）"), report)
```

- [ ] **Step 6: 运行 Excel 全文件测试并确认其他工作表未回归**

Run: `.venv/bin/python -m pytest tests/test_od0002_excel.py -q`

Expected: 文件内测试全部 `PASSED`；部门等其他工作表继续保持十三列，柜组为十五列。

- [ ] **Step 7: 提交 Excel 改动**

```bash
git add python_app/services/od0002_excel.py tests/test_od0002_excel.py
git commit -m "feat: export OD0002 group departments"
```

### Task 4: 综合回归与可视化验收

**Files:**
- Verify: `python_app/services/od0002_report.py`
- Verify: `python_app/services/od0002_excel.py`
- Verify: `client/src/pages/sales-reports/od0002-sales-gross-profit.tsx`

- [ ] **Step 1: 运行 OD0002 后端与 Excel 回归测试**

Run: `.venv/bin/python -m pytest tests/test_od0002_report.py tests/test_od0002_excel.py -q`

Expected: 全部可运行测试 `PASSED`，仅环境未配置的 PostgreSQL 集成测试 `SKIPPED`。

- [ ] **Step 2: 运行前端 OD0002 测试、类型检查和生产构建**

Run:

```bash
cd client && \
node --test --experimental-strip-types src/lib/od0002-report.test.mjs src/lib/od0002-navigation.test.mjs && \
npx tsc --noEmit && \
npm run build:no-check
```

Expected: Node 测试全部 `PASSED`，TypeScript 与 Vite 构建退出码均为 `0`。

- [ ] **Step 3: 验证工作簿结构与公式安全**

Run:

```bash
.venv/bin/python - <<'PY'
from io import BytesIO
from openpyxl import load_workbook
from tests.test_od0002_excel import sample_report
from python_app.services.od0002_excel import build_od0002_workbook

workbook = load_workbook(BytesIO(build_od0002_workbook(sample_report())), data_only=False)
group_sheet = workbook["柜组"]
assert group_sheet.max_column == 15
assert [group_sheet.cell(6, column).value for column in range(1, 7)] == [
    "门店编码", "门店名称", "部门编码", "部门名称", "柜组编码", "柜组名称",
]
for sheet in workbook.worksheets:
    for row in sheet.iter_rows():
        for cell in row:
            if cell.data_type == "f":
                raise AssertionError(f"unexpected formula: {sheet.title}!{cell.coordinate}")
print("OD0002 workbook QA passed")
PY
```

Expected: 输出 `OD0002 workbook QA passed`。

- [ ] **Step 4: 在本地页面完成视觉验收**

打开 `http://127.0.0.1:5174/dashboard?storeId=2&view=rooms` 中的 OD0002 报表：

1. 查询一段有数据的日期，进入“部门（含品类）”，确认“欧美进口品”完整在第一行，`0101` 在第二行；
2. 进入“柜组”，确认多门店查询显示门店、部门、柜组，单门店查询只显示部门、柜组；
3. 选择单个部门，确认柜组列表只保留该部门的柜组；
4. 导出 Excel，确认“柜组”工作表 A:F 为门店、部门、柜组的编码和名称，在线与 Excel 合计一致。

Expected: 两个页面场景和导出文件均符合设计文档，名称没有第三行折行。

- [ ] **Step 5: 检查工作区只包含本功能提交**

Run:

```bash
git status --short
git log --oneline --decorate -5
```

Expected: 本功能跟踪文件无未提交修改；用户原有的 `reports/`、`work/` 未跟踪文件保持原样且未进入任何提交。
