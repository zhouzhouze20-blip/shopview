import test from "node:test";
import assert from "node:assert/strict";

import { buildSupplierWorkbook } from "./export-brand-member-supplier.ts";


const period = (start, end) => ({
  period: { start_date: start, end_date: end },
  summary: {
    sales_revenue: 100000,
    positive_revenue: 105000,
    refund_revenue: -5000,
    ticket_count: 30,
    member_buyer_count: 20,
    member_sales_revenue: 80000,
    member_ticket_count: 25,
    nonmember_sales_revenue: 20000,
    refund_only_member_sales_revenue: 0,
    spend_per_buyer: 4000,
    purchase_frequency: 1.25,
    member_sales_quantity: 50,
    items_per_ticket: 2,
    average_item_price: 1600,
    department_rank: 3,
    department_group_count: 20,
    old_customer_repurchase_rate: 0.2,
  },
  segments: [
    { code: "brand_returning", label: "品牌老客", buyer_count: 10, sales_revenue: 50000, ticket_count: 12, buyer_share: 0.5, sales_share: 0.625 },
    { code: "same_department_inflow", label: "同部门流入", buyer_count: 5, sales_revenue: 15000, ticket_count: 6, buyer_share: 0.25, sales_share: 0.1875 },
    { code: "cross_department_inflow", label: "跨部门流入", buyer_count: 3, sales_revenue: 10000, ticket_count: 4, buyer_share: 0.15, sales_share: 0.125 },
    { code: "external_new", label: "外部招新", buyer_count: 2, sales_revenue: 5000, ticket_count: 3, buyer_share: 0.1, sales_share: 0.0625 },
  ],
  member_level_consumption: [
    { level_code: "01", level_label: "银星会员", buyer_count: 4, sales_revenue: 12000, ticket_count: 5, buyer_share: 0.2, sales_share: 0.15, spend_per_buyer: 3000, purchase_frequency: 1.25, average_ticket_value: 2400 },
    { level_code: "02", level_label: "金星会员", buyer_count: 5, sales_revenue: 18000, ticket_count: 6, buyer_share: 0.25, sales_share: 0.225, spend_per_buyer: 3600, purchase_frequency: 1.2, average_ticket_value: 3000 },
    { level_code: "03", level_label: "黑金会员", buyer_count: 5, sales_revenue: 22000, ticket_count: 7, buyer_share: 0.25, sales_share: 0.275, spend_per_buyer: 4400, purchase_frequency: 1.4, average_ticket_value: 3142.857 },
    { level_code: "04", level_label: "黑钻会员", buyer_count: 4, sales_revenue: 20000, ticket_count: 5, buyer_share: 0.2, sales_share: 0.25, spend_per_buyer: 5000, purchase_frequency: 1.25, average_ticket_value: 4000 },
    { level_code: "UNIDENTIFIED", level_label: "未标识会员", buyer_count: 2, sales_revenue: 8000, ticket_count: 2, buyer_share: 0.1, sales_share: 0.1, spend_per_buyer: 4000, purchase_frequency: 1, average_ticket_value: 4000 },
  ],
  purchase_frequency_analysis: [
    { code: "single_purchase", label: "一次客", buyer_count: 15, buyer_share: 0.75, sales_revenue: 50000, sales_share: 0.625, ticket_count: 15, sales_quantity: 27, spend_per_buyer: 3333.33, purchase_frequency: 1, average_ticket_value: 3333.33, items_per_ticket: 1.8, average_item_price: 1851.85 },
    { code: "repeat_purchase", label: "多次客", buyer_count: 5, buyer_share: 0.25, sales_revenue: 30000, sales_share: 0.375, ticket_count: 10, sales_quantity: 23, spend_per_buyer: 6000, purchase_frequency: 2, average_ticket_value: 3000, items_per_ticket: 2.3, average_item_price: 1304.35 },
  ],
  old_customer_funnel: { historical_target_member_count: 100, store_visit_count: 40, department_visit_count: 25, target_repurchase_count: 10 },
  inflow_sources: [{ segment_code: "same_department_inflow", group_code: "G2", group_name: "来源柜组", department_name: "目标部门", buyer_count: 5, historical_sales: 120000 }],
});

const report = {
  scope: { store_code: "601", target_group_code: "G1", competitor_group_codes: [] },
  target: {
    group_code: "G1",
    group_name: "测试品牌",
    department_code: "D1",
    department_name: "目标部门",
    current: period("2026-06-01", "2026-06-30"),
    prior: period("2025-06-01", "2025-06-30"),
  },
  comparison: {
    sales_revenue: { current: 100000, prior: 90000, change: 10000, change_rate: 0.1111 },
    member_buyer_count: { current: 20, prior: 18, change: 2, change_rate: 0.1111 },
    spend_per_buyer: { current: 4000, prior: 3900, change: 100, change_rate: 0.0256 },
    purchase_frequency: { current: 1.25, prior: 1.2, change: 0.05, change_rate: 0.0417 },
    old_customer_repurchase_rate: { current: 0.2, prior: 0.18, change: 0.02, change_rate: 0.1111 },
  },
  competitors: [],
  definitions: {},
};

report.target.prior.member_level_consumption[0] = {
  ...report.target.prior.member_level_consumption[0],
  buyer_count: 2,
  buyer_share: 0.1,
  sales_revenue: 6000,
  sales_share: 0.075,
  spend_per_buyer: 3000,
  purchase_frequency: 1,
  average_ticket_value: 2000,
};


test("supplier workbook has send-ready sections and styles", () => {
  const workbook = buildSupplierWorkbook(report, "常州购物中心", "销售收入与购买会员数均较同期增长。");

  assert.deepEqual(workbook.SheetNames, ["经营摘要", "会员结构", "频次客件", "老客经营", "流入来源", "数据口径"]);
  const overview = workbook.Sheets["经营摘要"];
  assert.equal(overview.A1.v, "品牌会员经营沟通简报");
  assert.equal(overview.A10.v, "销售收入与购买会员数均较同期增长。");
  assert.equal(overview.A1.s.fill.fgColor.rgb, "115E59");
  assert.equal(overview.A13.s.fill.fgColor.rgb, "0F766E");
  assert.equal(overview.B5.s.fill.fgColor.rgb, "FFFFFF");
  assert.equal(overview.B14.z, "#,##0;[Red]-#,##0");
  assert.equal(overview.E14.z, "0.0%");
  assert.equal(overview.D19.v, "持平");
  assert.ok(overview["!merges"].length >= 10);
  assert.equal(workbook.Sheets["数据口径"].A14.v.includes("不包含会员姓名"), true);
  assert.equal(workbook.Sheets["会员结构"].A17.v, "会员等级消费分析");
  assert.equal(workbook.Sheets["会员结构"].A19.v, "银星会员");
  assert.deepEqual(
    Array.from({ length: 22 }, (_, index) => workbook.Sheets["会员结构"][`${String.fromCharCode(65 + index)}18`]?.v),
    [
      "会员等级",
      "本期购买会员", "同期购买会员", "人数同比",
      "本期人数占比", "同期人数占比", "人数占比同比",
      "本期销售收入（元）", "同期销售收入（元）", "销售收入同比",
      "本期销售占比", "同期销售占比", "销售占比同比",
      "本期会员人均消费（元）", "同期会员人均消费（元）", "人均消费同比",
      "本期消费频次", "同期消费频次", "消费频次同比",
      "本期客单（元）", "同期客单（元）", "客单同比",
    ],
  );
  assert.equal(workbook.Sheets["会员结构"].B19.v, 4);
  assert.equal(workbook.Sheets["会员结构"].C19.v, 2);
  assert.equal(workbook.Sheets["会员结构"].D19.v, 1);
  assert.equal(workbook.Sheets["会员结构"].H19.v, 12000);
  assert.equal(workbook.Sheets["会员结构"].I19.v, 6000);
  assert.equal(workbook.Sheets["会员结构"].J19.v, 1);
  assert.equal(workbook.Sheets["会员结构"].T19.v, 2400);
  assert.equal(workbook.Sheets["会员结构"].U19.v, 2000);
  assert.equal(workbook.Sheets["会员结构"].V19.v, 0.2);
  assert.equal(workbook.Sheets["会员结构"].V19.z, "0.0%");
  assert.equal(workbook.Sheets["频次客件"].A6.v, "一次客");
  assert.equal(workbook.Sheets["频次客件"].K6.v, 1.8);
  assert.equal(workbook.Sheets["频次客件"].P6.v, 1.8);
  assert.equal(workbook.Sheets["频次客件"].K6.z, "0.00");
  assert.equal(workbook.Sheets["数据口径"].A10.v, "一次客 / 多次客");
});
