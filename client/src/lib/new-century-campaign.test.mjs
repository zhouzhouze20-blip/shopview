import assert from "node:assert/strict";
import test from "node:test";

import {
  buildNewCenturyCampaignWorkbook,
  filterGiftRedemptionDetails,
} from "./new-century-campaign.ts";

const giftDetails = [
  { template_id: 101, gift_name: "礼品券甲" },
  { template_id: 102, gift_name: "礼品券乙" },
  { template_id: 101, gift_name: "礼品券甲" },
];

test("gift detail filter supports all gifts and a single template", () => {
  assert.equal(filterGiftRedemptionDetails(giftDetails, "all").length, 3);
  assert.deepEqual(
    filterGiftRedemptionDetails(giftDetails, "101").map((row) => row.gift_name),
    ["礼品券甲", "礼品券甲"],
  );
});

test("whole-campaign workbook contains summary, detail, and definition sheets", () => {
  const report = {
    scope: {
      store_name: "常州新世纪商城",
      start_date: "2026-08-01",
      end_date: "2026-08-19",
      compare_start_date: "2025-08-01",
      compare_end_date: "2025-08-19",
    },
    quality: { message: "数据正常" },
    overview: {
      current: { sales_amount: 100, ticket_count: 2, average_ticket: 50, consuming_member_count: 1, member_sales_amount: 80, new_member_count: 1 },
      comparison: { sales_amount: 90, ticket_count: 2, average_ticket: 45, consuming_member_count: 1, member_sales_amount: 70, new_member_count: 1 },
      change_percent: { sales_amount: 11.1, ticket_count: 0, average_ticket: 11.1, consuming_member_count: 0, member_sales_amount: 14.3, new_member_count: 0 },
    },
    daily_sales: [{ business_date: "2026-08-01", sales_amount: 100, ticket_count: 2, member_count: 1 }],
    recharge: {
      summary: { increase_face_amount: 20, reversal_face_amount: 0, net_face_amount: 20, member_count: 1, flow_count: 1 },
      details: [],
    },
    gift_redemption: {
      summary: { redemption_count: 1, member_day_count: 1, consuming_member_day_count: 1, conversion_rate: 100, same_day_ticket_count: 2, same_day_sales_amount: 100, spend_per_consumer: 100, unmatched_redemption_count: 0 },
      daily: [],
      templates: [],
      details: [],
    },
    definitions: { sales: "603 门店销售" },
  };

  const workbook = buildNewCenturyCampaignWorkbook(report);
  assert.deepEqual(workbook.SheetNames, [
    "活动总览",
    "逐日销售",
    "增值汇总",
    "增值明细",
    "礼品券整体汇总",
    "礼品券类型汇总",
    "礼品券核销消费明细",
    "数据口径",
  ]);

  const overview = workbook.Sheets["活动总览"];
  assert.equal(overview.A1.v, "新世纪活动分析｜活动总览");
  assert.deepEqual(overview["!freeze"], { xSplit: 0, ySplit: 4 });
  assert.equal(overview["!autofilter"].ref, "A4:D10");
  assert.equal(overview.D5.v, 0.111);
  assert.equal(overview.D5.z, "0.0%;[Green]-0.0%;0.0%");
  assert.equal(overview.D5.s.font.color.rgb, "DC2626");
  assert.equal(overview.B5.z, '"¥"#,##0.00;[Green]-"¥"#,##0.00;"¥"0.00');
  assert.equal(overview.B6.z, "#,##0;[Green]-#,##0;0");

  const dailySales = workbook.Sheets["逐日销售"];
  assert.equal(dailySales.A5.z, "yyyy-mm-dd");
  assert.equal(dailySales.B5.z, '"¥"#,##0.00;[Green]-"¥"#,##0.00;"¥"0.00');
  assert.equal(dailySales.B5.s.alignment.horizontal, "right");

  const rechargeSummary = workbook.Sheets["增值汇总"];
  assert.equal(rechargeSummary.B5.z, '"¥"#,##0.00;[Green]-"¥"#,##0.00;"¥"0.00');
  assert.equal(rechargeSummary.B8.z, "#,##0;[Green]-#,##0;0");

  const giftSummary = workbook.Sheets["礼品券整体汇总"];
  assert.equal(giftSummary.B8.z, "0.0%;[Green]-0.0%;0.0%");
  assert.equal(giftSummary.B9.z, "#,##0;[Green]-#,##0;0");
});
