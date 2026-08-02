import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { navigationItems } from "./navigation-items.ts";
import { MODULE_PERMISSION_REQUIREMENTS } from "./module-permissions.ts";
import {
  buildDailyFollowupParams,
  financialMonthForDate,
  financialMonthLabel,
  financialMonthRange,
  formatDailyDate,
  formatDailyMoneyWan,
  formatDailyPercent,
  formatDailyPercentagePointChange,
} from "./daily-followup-report.ts";
import {
  DAILY_FOLLOWUP_AMOUNT_FORMAT,
  DAILY_FOLLOWUP_DECLINE_COLOR,
  DAILY_FOLLOWUP_GROWTH_COLOR,
  DAILY_FOLLOWUP_SIGNED_PERCENT_FORMAT,
  buildDailyFollowupExportData,
  buildDailyFollowupWorkbookData,
  dailyFollowupTrendColor,
} from "./daily-followup-export-data.ts";

const dailyFollowupPageSource = readFileSync(
  new URL("../pages/sales-reports/daily-followup.tsx", import.meta.url),
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

test("financial month changes on the 29th", () => {
  assert.equal(financialMonthForDate(new Date(2026, 6, 28, 12)), "2026-07");
  assert.equal(financialMonthForDate(new Date(2026, 6, 29, 12)), "2026-08");
  assert.equal(financialMonthForDate(new Date(2026, 11, 29, 12)), "2027-01");
});

test("financial month range follows previous month 29 through current month 28", () => {
  assert.deepEqual(financialMonthRange("2026-08"), {
    start: "2026-07-29",
    end: "2026-08-28",
  });
  assert.deepEqual(financialMonthRange("2026-01"), {
    start: "2025-12-29",
    end: "2026-01-28",
  });
  assert.deepEqual(financialMonthRange("2026-03"), {
    start: "2026-03-01",
    end: "2026-03-28",
  });
  assert.deepEqual(financialMonthRange("2024-03"), {
    start: "2024-02-29",
    end: "2024-03-28",
  });
  assert.equal(
    financialMonthLabel("2026-08"),
    "2026年8月财务月（07-29—08-28）",
  );
});

test("daily follow-up params omit all-scope sentinels and include selected scope", () => {
  assert.equal(
    buildDailyFollowupParams({
      financialMonth: "2026-08",
      dimension: "departments",
      storeId: "all",
      departmentId: "all",
    }).toString(),
    "financial_year=2026&financial_month=8&dimension=departments",
  );
  const selected = buildDailyFollowupParams({
    financialMonth: "2026-08",
    dimension: "groups",
    storeId: " 603 ",
    departmentId: " 6030117 ",
  });
  assert.equal(selected.get("store_id"), "603");
  assert.equal(selected.get("department_id"), "6030117");
});

test("daily follow-up formats report units", () => {
  assert.equal(formatDailyMoneyWan(123456.78), "12.35");
  assert.equal(formatDailyPercent(0.1234), "12.3%");
  assert.equal(formatDailyPercent(null), "—");
  assert.equal(formatDailyPercentagePointChange(0.0123), "+1.2个百分点");
  assert.equal(formatDailyPercentagePointChange(-0.0123), "-1.2个百分点");
  assert.equal(formatDailyPercentagePointChange(0), "0.0个百分点");
  assert.equal(formatDailyDate("2026-06-29"), "06-29");
});

test("daily follow-up is visible under sales reports with its own permission", () => {
  const reports = findNavigationItem(navigationItems, "sales-reports");
  const dailyFollowup = findNavigationItem(reports?.subItems ?? [], "daily-sales-followup");
  assert.ok(dailyFollowup);
  assert.deepEqual(
    MODULE_PERMISSION_REQUIREMENTS["daily-sales-followup"],
    ["sales.od0001.view"],
  );
  assert.equal(
    dailyFollowup.name,
    "OD0001 销售逐日跟进表",
  );
});

test("daily follow-up export refreshes every workbook dimension before writing", () => {
  assert.match(
    dailyFollowupPageSource,
    /const \[departmentReport, groupReport, specialSaleReport\] = await Promise\.all/,
  );
  assert.match(
    dailyFollowupPageSource,
    /exportDailyFollowupExcel\(activeReport,/,
  );
});

test("daily follow-up export keeps the current view and readable date headers", () => {
  const marginCurrent = 12_345 / 123_456;
  const marginPrior = 10_000 / 100_000;
  const salesYoy = 123_456 / 100_000 - 1;
  const profitYoy = 12_345 / 10_000 - 1;
  const metric = {
    sales_current: 123_456,
    sales_prior: 100_000,
    sales_yoy: salesYoy,
    profit_current: 12_345,
    profit_prior: 10_000,
    profit_yoy: profitYoy,
    margin_current: marginCurrent,
    margin_prior: marginPrior,
    margin_change: marginCurrent - marginPrior,
  };
  const row = {
    store_code: "602",
    store_name: "常州购物中心",
    department_code: "60201",
    department_name: "营运一部",
    area_name: "化妆区",
    category_name: "合资品",
    operation_method: "经销",
    brand_code: "B1",
    brand_name: "品牌一",
    dimension_code: "6020101001",
    dimension_name: "Aupres欧珀莱厅",
    daily: [{ ...metric, date: "2026-06-29", prior_date: "2025-06-29" }],
    totals: metric,
  };
  const report = {
    financial_month: "2026-07",
    dates: {
      start_date: "2026-06-29",
      end_date: "2026-07-28",
      prior_start_date: "2025-06-29",
      prior_end_date: "2025-07-28",
    },
    cumulative_dates: {
      start_date: "2026-06-29",
      end_date: "2026-07-27",
      prior_start_date: "2025-06-29",
      prior_end_date: "2025-07-27",
    },
    dimension: "groups",
    selected_store: "602",
    selected_department: null,
    scope_description: "权限范围：常州购物中心",
    days: [{ date: "2026-06-29", prior_date: "2025-06-29", label: "0629" }],
    rows: [row],
    daily_totals: row.daily,
    totals: metric,
    generated_at: "2026-07-27T12:00:00",
  };

  const data = buildDailyFollowupExportData(report, {
    metricView: "sales",
    rows: [row],
  });

  assert.equal(data.currentViewRows[3][4], "06-29");
  assert.equal(data.currentViewRows[4][4], 12.3456);
  assert.equal(data.currentViewRows[1][3], "2026-06-29 至 2026-07-27");
  assert.equal(data.currentViewRows[1][5], "2025-06-29 至 2025-07-27");
  assert.equal(data.detailRows[1][0], "2026-06-29");
  assert.match(data.filename, /2026-07_柜组逐日_销售收入\.xlsx$/);

  const workbook = buildDailyFollowupWorkbookData(report, [row]);
  assert.equal(workbook.trackingSheet.sheetName, "柜组");
  assert.deepEqual(workbook.trackingSheet.rows[2], [
    "本期范围",
    "2026-06-29 至 2026-07-27",
  ]);
  assert.deepEqual(workbook.trackingSheet.rows[3], [
    "同期范围",
    "2025-06-29 至 2025-07-27",
  ]);
  assert.equal(workbook.trackingSheet.rows[5][6], "累计");
  assert.equal(workbook.trackingSheet.rows[5][15], "06-29");
  assert.deepEqual(
    workbook.trackingSheet.rows[6].slice(0, 15),
    [
      "门店",
      "部门",
      "区域",
      "类别",
      "经营方式",
      "柜组名称",
      "本期销售",
      "同期销售",
      "销售同比",
      "本期毛利",
      "同期毛利",
      "毛利同比",
      "本期毛利率",
      "同期毛利率",
      "毛利率同比",
    ],
  );
  assert.deepEqual(
    workbook.trackingSheet.rows[7].slice(6, 15),
    [12.3456, 10, salesYoy, 1.2345, 1, profitYoy, marginCurrent, marginPrior, marginCurrent - marginPrior],
  );
  assert.deepEqual(
    workbook.trackingSheet.rows[7].slice(15, 24),
    [12.3456, 10, salesYoy, 1.2345, 1, profitYoy, marginCurrent, marginPrior, marginCurrent - marginPrior],
  );
  const trackingTotal = workbook.trackingSheet.rows.at(-1);
  assert.deepEqual(trackingTotal.slice(6, 15), [
    12.3456,
    10,
    salesYoy,
    1.2345,
    1,
    profitYoy,
    marginCurrent,
    marginPrior,
    marginCurrent - marginPrior,
  ]);
  assert.deepEqual(trackingTotal.slice(15, 24), trackingTotal.slice(6, 15));
  assert.deepEqual(
    workbook.viewSheets.map((sheet) => sheet.sheetName),
    ["柜组逐日-销售收入", "柜组逐日-毛利"],
  );
  assert.equal(workbook.viewSheets[0].currentViewRows[4][4], 12.3456);
  assert.equal(workbook.viewSheets[1].currentViewRows[4][4], 1.2345);
  assert.equal(workbook.detailSheetName, "同期同比明细");
  assert.equal(DAILY_FOLLOWUP_AMOUNT_FORMAT, "#,##0.00");
  assert.equal(DAILY_FOLLOWUP_SIGNED_PERCENT_FORMAT, "+0.0%;[Red]-0.0%;0.0%");
  assert.equal(dailyFollowupTrendColor(0.1), DAILY_FOLLOWUP_GROWTH_COLOR);
  assert.equal(dailyFollowupTrendColor(-0.1), DAILY_FOLLOWUP_DECLINE_COLOR);
  assert.equal(dailyFollowupTrendColor(0), undefined);
  assert.match(workbook.filename, /2026-07_柜组逐日\.xlsx$/);

  const departmentRow = {
    ...row,
    dimension_code: "60201",
    dimension_name: "营运一部",
  };
  const departmentReport = {
    ...report,
    dimension: "departments",
    rows: [departmentRow],
  };
  const combinedWorkbook = buildDailyFollowupWorkbookData(
    report,
    [row],
    { report: departmentReport, rows: [departmentRow] },
    {
      report: { ...report, dimension: "special_sales" },
      rows: [row],
    },
  );
  assert.deepEqual(
    combinedWorkbook.trackingSheets.map((sheet) => sheet.sheetName),
    ["部门", "区域", "柜组", "柜组销售", "特卖"],
  );
  assert.equal(combinedWorkbook.trackingSheets[0].fixedColumnCount, 2);
  assert.equal(combinedWorkbook.trackingSheets[1].fixedColumnCount, 2);
  assert.equal(combinedWorkbook.trackingSheets[2].fixedColumnCount, 6);
  assert.equal(combinedWorkbook.trackingSheets[3].fixedColumnCount, 6);
  assert.equal(combinedWorkbook.trackingSheets[3].metricColumnsPerDay, 3);
  const areaRow = combinedWorkbook.trackingSheets[1].rows[7];
  assert.deepEqual(areaRow.slice(2, 11), [
    12.3456,
    10,
    salesYoy,
    1.2345,
    1,
    profitYoy,
    marginCurrent,
    marginPrior,
    marginCurrent - marginPrior,
  ]);
  assert.equal(combinedWorkbook.trackingSheets[0].rows[5][2], "累计");
  assert.equal(combinedWorkbook.trackingSheets[0].rows[5][11], "06-29");
  const groupSalesSheet = combinedWorkbook.trackingSheets[3];
  assert.equal(groupSalesSheet.rows[5][6], "累计");
  assert.equal(groupSalesSheet.rows[5][9], "06-29");
  assert.deepEqual(
    groupSalesSheet.rows[6].slice(0, 9),
    [
      "门店",
      "部门",
      "区域",
      "类别",
      "经营方式",
      "柜组名称",
      "本期销售",
      "同期销售",
      "销售同比",
    ],
  );
  assert.equal(groupSalesSheet.rows[6].includes("本期毛利"), false);
  assert.deepEqual(
    groupSalesSheet.rows[7].slice(6, 9),
    [12.3456, 10, salesYoy],
  );
  assert.deepEqual(
    groupSalesSheet.rows[7].slice(9, 12),
    [12.3456, 10, salesYoy],
  );
  const specialSaleSheet = combinedWorkbook.trackingSheets[4];
  assert.equal(specialSaleSheet.rows[5][8], "累计");
  assert.equal(specialSaleSheet.rows[5][17], "06-29");
  assert.deepEqual(
    specialSaleSheet.rows[6].slice(0, 17),
    [
      "门店编码",
      "门店名称",
      "部门编码",
      "部门名称",
      "柜组编码",
      "柜组名称",
      "品牌编码",
      "品牌名称",
      "本期销售",
      "同期销售",
      "销售同比",
      "本期毛利",
      "同期毛利",
      "毛利同比",
      "本期毛利率",
      "同期毛利率",
      "毛利率同比",
    ],
  );
  assert.deepEqual(
    specialSaleSheet.rows[7].slice(0, 8),
    ["602", "常州购物中心", "60201", "营运一部", "6020101001", "Aupres欧珀莱厅", "B1", "品牌一"],
  );
  assert.match(combinedWorkbook.filename, /OD0001销售逐日跟进表_2026-07\.xlsx$/);
  assert.match(dailyFollowupPageSource, /label="本期毛利率"/);
  assert.match(dailyFollowupPageSource, /label="同期毛利率"/);
  assert.match(dailyFollowupPageSource, /label="毛利率同比"/);
});
