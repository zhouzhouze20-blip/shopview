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


test("supplier workbook has send-ready sections and styles", () => {
  const workbook = buildSupplierWorkbook(report, "常州购物中心", "销售收入与购买会员数均较同期增长。");

  assert.deepEqual(workbook.SheetNames, ["经营摘要", "会员结构", "老客经营", "流入来源", "数据口径"]);
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
  assert.equal(workbook.Sheets["数据口径"].A12.v.includes("不包含会员姓名"), true);
  assert.equal(workbook.Sheets["会员结构"].A17.v, "会员等级消费分析");
  assert.equal(workbook.Sheets["会员结构"].A19.v, "银星会员");
  assert.equal(workbook.Sheets["会员结构"].D19.z, "#,##0;[Red]-#,##0");
  assert.equal(workbook.Sheets["会员结构"].H18.v, "本期客单（元）");
  assert.equal(workbook.Sheets["会员结构"].H19.v, 2400);
  assert.equal(workbook.Sheets["会员结构"].I18.v, "同期购买会员");
  assert.equal(workbook.Sheets["会员结构"].O18.v, "同期客单（元）");
  assert.equal(workbook.Sheets["会员结构"].O19.v, 2400);
  assert.equal(workbook.Sheets["会员结构"].O19.z, "#,##0;[Red]-#,##0");
});
