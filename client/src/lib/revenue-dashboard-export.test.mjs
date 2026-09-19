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
    raw_sales_gross_profit_amount: 100,
    raw_fee_amount: 55,
    raw_extra_amount: 12,
    sales_adjustment_amount: 0,
    fee_adjustment_amount: -5,
    extra_adjustment_amount: -2,
    close_adjustment_amount: -7,
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
    raw_sales_gross_profit_amount: 200,
    raw_fee_amount: 15,
    raw_extra_amount: 0,
    sales_adjustment_amount: 0,
    fee_adjustment_amount: 0,
    extra_adjustment_amount: 0,
    close_adjustment_amount: 0,
    sales_gross_profit_amount: 200,
    fee_amount: 15,
    extra_amount: 0,
    total_amount: 215,
    fee_breakdown: [
      { fee_type_code: "02", fee_type_name: "物业管理费", tax_excluded_amount: 15 },
    ],
  },
];

const extraRows = [
  {
    id: "detail-2",
    store_id: 3,
    store_code: "603",
    store_name: "常州新世纪商城",
    revenue_date: "2026-07-28",
    subject_code: "605110",
    subject_name: "综合管理费",
    extra_type: "营运收费",
    department_code: "3125",
    department_name: "新世纪市场部-运营",
    explanation: "装修管理费第二笔",
    voucher_no: "V002",
    amount: 200,
    source_detail_key: "PK002",
    unit_code: "后台部门收益",
    match_method: "BACKOFFICE_FALLBACK",
  },
  {
    id: "detail-1",
    store_id: 3,
    store_code: "603",
    store_name: "常州新世纪商城",
    revenue_date: "2026-07-27",
    subject_code: "605110",
    subject_name: "综合管理费",
    extra_type: "营运收费",
    department_code: "3125",
    department_name: "新世纪市场部-运营",
    explanation: "装修管理费第一笔",
    voucher_no: "V001",
    amount: 100,
    source_detail_key: "PK001",
    unit_code: "后台部门收益",
    match_method: "BACKOFFICE_FALLBACK",
  },
  {
    id: "detail-3",
    store_id: 3,
    store_code: "603",
    store_name: "常州新世纪商城",
    revenue_date: "2026-07-26",
    subject_code: "605109",
    subject_name: "停车收入",
    extra_type: "营运收费",
    department_code: "3125",
    department_name: "新世纪市场部-运营",
    explanation: "停车场收入",
    voucher_no: "V003",
    amount: 50,
    source_detail_key: "PK003",
    unit_code: "后台部门收益",
    match_method: "BACKOFFICE_FALLBACK",
  },
];

test("revenue dashboard export expands every fee type using the active dashboard basis", () => {
  const data = buildRevenueDashboardExportData(rows, "2026-07-01", "2026-07-28");
  const header = data.summaryRows[0];

  assert.deepEqual(data.feeColumns, ["01 广告服务费", "02 物业管理费"]);
  assert.equal(header.includes("富基收费（调整前）"), true);
  assert.equal(header.includes("01 广告服务费（看板口径）"), true);
  assert.equal(header.includes("02 物业管理费（看板口径）"), true);
  assert.equal(data.summaryRows[1][header.indexOf("01 广告服务费（看板口径）")], 20);
  assert.equal(data.summaryRows[1][header.indexOf("02 物业管理费（看板口径）")], 30);
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
  assert.equal(total[header.indexOf("富基收费（调整前）")], 70);
  assert.equal(total[header.indexOf("富基收费对应月结调整")], -5);
  assert.equal(total[header.indexOf("富基收费（调整后）")], 65);
  assert.equal(total[header.indexOf("NC非富基收费（调整前）")], 12);
  assert.equal(total[header.indexOf("NC非富基对应月结调整")], -2);
  assert.equal(total[header.indexOf("NC非富基收费（调整后）")], 10);
  assert.equal(total[header.indexOf("月结调整合计")], -7);
  assert.equal(
    data.summaryRows[1][header.indexOf("总收益")],
    data.summaryRows[1][header.indexOf("销售毛利（不含税）")]
      + data.summaryRows[1][header.indexOf("富基收费（调整前）")]
      + data.summaryRows[1][header.indexOf("NC非富基收费（调整前）")]
      + data.summaryRows[1][header.indexOf("月结调整合计")],
  );
  assert.equal(data.feeDetailRows.length, 4);
  assert.equal(
    data.notesRows.some(
      (row) =>
        row[0] === "日期口径"
        && row[1] === "销售毛利按财务日期；收费按付款日期且剔除票减及保证金；其他收益按财务期间",
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

test("revenue dashboard export organizes other income by NC subject and keeps voucher detail", () => {
  const data = buildRevenueDashboardExportData(
    rows,
    "2026-07-01",
    "2026-07-28",
    extraRows,
  );
  const subjectHeader = data.extraSubjectRows[0];
  const subjectTotal = data.extraSubjectRows.at(-1);
  const detailHeader = data.extraDetailRows[0];
  const detailTotal = data.extraDetailRows.at(-1);

  assert.equal(data.extraSubjectRows.length, 4);
  assert.equal(data.extraSubjectRows[1][subjectHeader.indexOf("科目编码")], "605109");
  assert.equal(data.extraSubjectRows[2][subjectHeader.indexOf("科目编码")], "605110");
  assert.equal(data.extraSubjectRows[2][subjectHeader.indexOf("明细笔数")], 2);
  assert.equal(data.extraSubjectRows[2][subjectHeader.indexOf("科目金额")], 300);
  assert.equal(subjectTotal[subjectHeader.indexOf("明细笔数")], 3);
  assert.equal(subjectTotal[subjectHeader.indexOf("科目金额")], 350);

  assert.equal(data.extraDetailRows[1][detailHeader.indexOf("NC凭证")], "V003");
  assert.equal(data.extraDetailRows[2][detailHeader.indexOf("NC凭证")], "V001");
  assert.equal(data.extraDetailRows[2][detailHeader.indexOf("摘要")], "装修管理费第一笔");
  assert.equal(data.extraDetailRows[2][detailHeader.indexOf("来源明细键")], "PK001");
  assert.equal(detailTotal[detailHeader.indexOf("金额")], 350);
  assert.equal(
    data.notesRows.some((row) => row[0] === "其他收益科目汇总"),
    true,
  );
});
