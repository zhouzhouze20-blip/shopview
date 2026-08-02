import assert from "node:assert/strict";
import test from "node:test";

import { buildRevenueDashboardExportData } from "./revenue-dashboard-export.ts";

const rows = [
  {
    store_id: 1,
    store_code: "601",
    store_name: "常州购物中心",
    department_code: "60101",
    department_name: "中心一部",
    group_code: "6010101001",
    group_name: "测试柜组",
    unit_codes: "A001",
    unit_count: 1,
    sales_gross_profit_amount: 100,
    fee_amount: 50,
    extra_amount: 10,
    total_amount: 160,
    fee_breakdown: [
      { fee_type_code: "02", fee_type_name: "物业管理费", tax_excluded_amount: 30 },
      { fee_type_code: "01", fee_type_name: "广告服务费", tax_excluded_amount: 20 },
    ],
  },
  {
    store_id: 1,
    store_code: "601",
    store_name: "常州购物中心",
    department_code: "60102",
    department_name: "中心二部",
    group_code: "6010201001",
    group_name: "另一个柜组",
    unit_codes: "B001",
    unit_count: 1,
    sales_gross_profit_amount: 200,
    fee_amount: 15,
    extra_amount: 0,
    total_amount: 215,
    fee_breakdown: [
      { fee_type_code: "02", fee_type_name: "物业管理费", tax_excluded_amount: 15 },
    ],
  },
];

test("revenue dashboard export expands every untaxed fee type into its own column", () => {
  const data = buildRevenueDashboardExportData(rows, "2026-07-01", "2026-07-28");
  const header = data.summaryRows[0];

  assert.deepEqual(data.feeColumns, ["01 广告服务费", "02 物业管理费"]);
  assert.equal(header.includes("去税收费汇总"), true);
  assert.equal(header.includes("01 广告服务费（不含税）"), true);
  assert.equal(header.includes("02 物业管理费（不含税）"), true);
  assert.equal(data.summaryRows[1][header.indexOf("01 广告服务费（不含税）")], 20);
  assert.equal(data.summaryRows[1][header.indexOf("02 物业管理费（不含税）")], 30);
  assert.equal(data.summaryRows[1][header.indexOf("收费分类校验差额")], 0);
});

test("revenue dashboard export includes hierarchy, fee detail and grand totals", () => {
  const data = buildRevenueDashboardExportData(rows, "2026-07-01", "2026-07-28");
  const header = data.summaryRows[0];
  const total = data.summaryRows.at(-1);

  assert.equal(data.summaryRows[1][header.indexOf("门店")], "常州购物中心");
  assert.equal(data.summaryRows[1][header.indexOf("部门")], "中心一部");
  assert.equal(data.summaryRows[1][header.indexOf("柜组")], "测试柜组");
  assert.equal(total[header.indexOf("销售毛利（不含税）")], 300);
  assert.equal(total[header.indexOf("去税收费汇总")], 65);
  assert.equal(total[header.indexOf("其他收益")], 10);
  assert.equal(data.feeDetailRows.length, 4);
  assert.equal(
    data.notesRows.some(
      (row) =>
        row[0] === "日期口径"
        && row[1] === "销售毛利按财务日期；收费按付款日期；其他收益按确认收益日期",
    ),
    true,
  );
  assert.equal(
    data.notesRows.some(
      (row) =>
        row[0] === "未付款收费"
        && String(row[1]).includes("不进入本次导出"),
    ),
    true,
  );
  assert.match(data.filename, /收益看板_柜组最明细_2026-07-01_2026-07-28\.xlsx/);
});
