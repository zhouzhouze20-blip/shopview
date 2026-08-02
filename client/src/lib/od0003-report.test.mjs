import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { navigationItems } from "./navigation-items.ts";
import { MODULE_PERMISSION_REQUIREMENTS } from "./module-permissions.ts";
import {
  buildOd0003Sheets,
  OD0003_METRIC_HEADERS,
  OD0003_SHEETS,
  od0003MetricHeaders,
  od0003MetricValues,
  od0003WeekGroups,
} from "./od0003-report.ts";

const metric = {
  sales_current: 120_000,
  sales_prior: 100_000,
  sales_yoy: 0.2,
  profit_current: 24_000,
  profit_prior: 15_000,
  profit_yoy: 0.6,
  margin_current: 0.2,
  margin_prior: 0.15,
  margin_change: 0.05,
};

const report = {
  financial_month: "2026-07",
  dates: {
    start_date: "2026-06-29",
    end_date: "2026-07-28",
    prior_start_date: "2025-06-29",
    prior_end_date: "2025-07-28",
  },
  dimension: "groups",
  selected_store: "603",
  selected_department: "6030101",
  scope_description: "当前用户权限范围",
  days: [{ date: "2026-06-29", prior_date: "2025-06-29", label: "06-29" }],
  rows: [{
    store_code: "603",
    store_name: "常州新世纪商城",
    department_code: "6030101",
    department_name: "中心一部（化妆）",
    area_name: "化妆区",
    category_name: "合资品",
    floor_code: "1F",
    operation_method: "联营",
    is_key_brand: true,
    manager_name: "张三",
    dimension_code: "6030101001",
    dimension_name: "欧珀莱厅",
    daily: [{ ...metric, date: "2026-06-29", prior_date: "2025-06-29" }],
    totals: metric,
  }],
  daily_totals: [{ ...metric, date: "2026-06-29", prior_date: "2025-06-29" }],
  totals: metric,
  generated_at: "2026-07-27T12:00:00Z",
};

function findNavigationItem(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findNavigationItem(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("OD0003 is an independent sales report module", () => {
  const reports = findNavigationItem(navigationItems, "sales-reports");
  assert.equal(
    findNavigationItem(reports?.subItems ?? [], "od0003-center-sales-followup")?.name,
    "OD0003 中心销售跟进表",
  );
  assert.deepEqual(
    MODULE_PERMISSION_REQUIREMENTS["od0003-center-sales-followup"],
    ["sales.od0003.view"],
  );
});

test("OD0003 query UI supports all stores and optional department", () => {
  const source = readFileSync(
    new URL("../pages/sales-reports/od0003-center-sales-followup.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /全部门店/);
  assert.match(source, /全部门/);
  assert.match(source, /DAILY_FOLLOWUP_ALL_STORES/);
  assert.match(source, /DAILY_FOLLOWUP_ALL_DEPARTMENTS/);
  assert.doesNotMatch(source, /请选择门店和中心/);
});

test("OD0003 creates the six source workbook views and subtotal hierarchy", () => {
  const sheets = buildOd0003Sheets(report);
  assert.deepEqual(sheets.map((sheet) => sheet.name), [...OD0003_SHEETS]);
  assert.deepEqual(
    sheets[0].dimensionHeaders,
    ["楼层", "部门名称", "区域名称", "类别名称", "品牌厅名称", "重点/业绩", "商品主管"],
  );
  assert.deepEqual(
    sheets[0].rows[0].labels,
    ["1F", "中心一部（化妆）", "化妆区", "合资品", "欧珀莱厅", "重点品牌", "张三"],
  );
  assert.deepEqual(
    sheets[0].rows.map((row) => row.kind),
    ["detail", "categorySubtotal", "areaSubtotal", "departmentSubtotal", "grandTotal"],
  );
  assert.equal(OD0003_METRIC_HEADERS.length, 11);
  assert.deepEqual(od0003MetricHeaders("2026-07"), [
    "26年销", "25年销", "25同比额", "25同比率",
    "26年毛", "25年毛", "25同比额", "25同比率",
    "26年率", "25年率", "25同比",
  ]);
  assert.deepEqual(od0003MetricValues(metric).slice(0, 4), [12, 10, 2, 0.2]);
  assert.deepEqual(
    od0003WeekGroups([
      { date: "2026-06-29", prior_date: "2025-06-29", label: "06-29" },
      { date: "2026-07-05", prior_date: "2025-07-05", label: "07-05" },
      { date: "2026-07-06", prior_date: "2025-07-06", label: "07-06" },
    ]),
    [
      { label: "第一周06.29-07.05", dayIndexes: [0, 1] },
      { label: "第二周07.06-07.06", dayIndexes: [2] },
    ],
  );
});

test("OD0003 exporter keeps the original workbook palette and six sheet loop", () => {
  const source = readFileSync(new URL("./export-od0003-excel.ts", import.meta.url), "utf8");
  for (const color of ["D8E4BC", "CCC0DA", "B7DEE8", "8DB4E2", "FFC000"]) {
    assert.match(source, new RegExp(color));
  }
  assert.ok(source.includes("for (const sheet of buildOd0003Sheets(report))"));
});
