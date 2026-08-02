import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import XLSX from "xlsx-js-style";

import { exportMonthlyFollowupExcel } from "./export-monthly-followup-excel.ts";
import { navigationItems } from "./navigation-items.ts";
import { MODULE_PERMISSION_REQUIREMENTS } from "./module-permissions.ts";
import {
  buildMonthlyFollowupParams,
  currentFinancialYear,
} from "./monthly-followup-report.ts";

const pageSource = readFileSync(
  new URL("../pages/sales-reports/od0004-monthly-followup.tsx", import.meta.url),
  "utf8",
);

function findNavigationItem(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findNavigationItem(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("OD0004 queries one financial year and keeps selected business scope", () => {
  assert.equal(currentFinancialYear(new Date(2026, 6, 28, 12)), 2026);
  assert.equal(currentFinancialYear(new Date(2026, 11, 29, 12)), 2026);
  assert.equal(
    buildMonthlyFollowupParams({
      financialYear: 2026,
      dimension: "departments",
      storeId: "all",
      departmentId: "all",
    }).toString(),
    "financial_year=2026&dimension=departments",
  );
  const selected = buildMonthlyFollowupParams({
    financialYear: 2026,
    dimension: "groups",
    storeId: " 603 ",
    departmentId: " 6030117 ",
  });
  assert.equal(selected.get("store_id"), "603");
  assert.equal(selected.get("department_id"), "6030117");
});

test("OD0004 is a grouped sales report with an independent permission", () => {
  const reports = findNavigationItem(navigationItems, "sales-reports");
  const od0004 = findNavigationItem(reports?.subItems ?? [], "od0004-monthly-followup");
  assert.equal(od0004?.name, "OD0004 销售逐月跟进表");
  assert.deepEqual(
    MODULE_PERMISSION_REQUIREMENTS["od0004-monthly-followup"],
    ["sales.od0004.view"],
  );
});

test("OD0004 page fetches all workbook dimensions before export", () => {
  assert.match(
    pageSource,
    /const \[departmentReport, groupReport, specialSaleReport\] = await Promise\.all/,
  );
  assert.match(pageSource, /exportMonthlyFollowupExcel/);
  assert.match(pageSource, /财务年为1月1日至12月31日/);
  assert.match(pageSource, /12月为11月29日至12月31日/);
  assert.match(pageSource, /label="本期毛利率"/);
  assert.match(pageSource, /label="同期毛利率"/);
  assert.match(pageSource, /label="毛利率同比"/);
});

test("OD0004 export writes the OD0001-style workbook sheets with annual and monthly blocks", () => {
  const metric = {
    sales_current: 120_000,
    sales_prior: 100_000,
    sales_yoy: 0.2,
    profit_current: 24_000,
    profit_prior: 20_000,
    profit_yoy: 0.2,
    margin_current: 0.2,
    margin_prior: 0.2,
    margin_change: 0,
  };
  const months = Array.from({ length: 12 }, (_, index) => ({
    financial_month: `2026-${String(index + 1).padStart(2, "0")}`,
    label: `${index + 1}月`,
    start_date: index === 0 ? "2026-01-01" : `2026-${String(index).padStart(2, "0")}-29`,
    end_date: index === 11 ? "2026-12-31" : `2026-${String(index + 1).padStart(2, "0")}-28`,
    prior_start_date: index === 0 ? "2025-01-01" : `2025-${String(index).padStart(2, "0")}-29`,
    prior_end_date: index === 11 ? "2025-12-31" : `2025-${String(index + 1).padStart(2, "0")}-28`,
    comparison_end: index === 11 ? "2026-12-31" : `2026-${String(index + 1).padStart(2, "0")}-28`,
    prior_comparison_end: index === 11 ? "2025-12-31" : `2025-${String(index + 1).padStart(2, "0")}-28`,
  }));
  const row = {
    store_code: "603",
    store_name: "常州新世纪商城",
    department_code: "60301",
    department_name: "中心一部",
    area_name: "女装区",
    category_name: "女装",
    operation_method: "联营",
    dimension_code: "6030101",
    dimension_name: "测试柜组",
    brand_code: "B1",
    brand_name: "测试品牌",
    monthly: months.map((month) => ({
      ...metric,
      financial_month: month.financial_month,
      label: month.label,
    })),
    totals: metric,
  };
  const report = (dimension) => ({
    financial_year: 2026,
    dates: {
      start_date: "2026-01-01",
      end_date: "2026-12-31",
      prior_start_date: "2025-01-01",
      prior_end_date: "2025-12-31",
    },
    dimension,
    selected_store: "603",
    selected_department: null,
    scope_description: "权限范围：常州新世纪商城",
    months,
    rows: [row],
    monthly_totals: row.monthly,
    totals: metric,
    generated_at: "2026-07-31T00:00:00Z",
  });

  const temporaryDirectory = mkdtempSync(join(tmpdir(), "shopview-od0004-"));
  const previousDirectory = process.cwd();
  try {
    process.chdir(temporaryDirectory);
    const filename = exportMonthlyFollowupExcel(
      report("departments"),
      report("groups"),
      report("special_sales"),
    );
    assert.equal(filename, "OD0004销售逐月跟进表_2026.xlsx");
    assert.equal(existsSync(join(temporaryDirectory, filename)), true);
    const workbook = XLSX.readFile(join(temporaryDirectory, filename), { cellNF: true });
    assert.deepEqual(workbook.SheetNames, ["部门", "区域", "柜组", "柜组销售", "特卖"]);
    const departmentRows = XLSX.utils.sheet_to_json(workbook.Sheets["部门"], {
      header: 1,
      raw: true,
    });
    assert.deepEqual(departmentRows[1], ["财务年度", "2026年（逐月）"]);
    assert.deepEqual(departmentRows[2], ["本期范围", "2026-01-01 至 2026-12-31"]);
    assert.deepEqual(departmentRows[3], ["同期范围", "2025-01-01 至 2025-12-31"]);
    assert.equal(departmentRows[5][2], "全年合计");
    assert.equal(departmentRows[5][11], "1月");
    assert.equal(departmentRows[5][110], "12月");
    assert.deepEqual(departmentRows[6].slice(2, 11), [
      "本期销售",
      "同期销售",
      "销售同比",
      "本期毛利",
      "同期毛利",
      "毛利同比",
      "本期毛利率",
      "同期毛利率",
      "毛利率同比",
    ]);
    assert.deepEqual(departmentRows[7].slice(2, 11), [
      12,
      10,
      0.2,
      2.4,
      2,
      0.2,
      0.2,
      0.2,
      0,
    ]);
    assert.equal(workbook.Sheets["部门"].K8.z, "+0.0%;[Red]-0.0%;0.0%");
  } finally {
    process.chdir(previousDirectory);
    rmSync(temporaryDirectory, { recursive: true, force: true });
  }
});
