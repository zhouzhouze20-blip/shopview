import assert from "node:assert/strict";
import test from "node:test";

import {
  buildBirthdayCouponWorkbook,
  birthdayCouponExportFilename,
  birthdayCouponAssetLabel,
  birthdayCouponStatusLabel,
  centerCouponGroupsForDepartment,
  maskBirthdayCouponMemberName,
  maskBirthdayCouponMemberNo,
} from "./birthday-coupon-analysis.ts";

test("birthday coupon status labels cover operational states", () => {
  assert.equal(birthdayCouponStatusLabel("REDEEMED"), "已核销");
  assert.equal(birthdayCouponStatusLabel("EXPIRED_UNUSED"), "已过期未用");
  assert.equal(birthdayCouponStatusLabel("UNUSED"), "有效期内未用");
});

test("member number is masked on the dashboard", () => {
  assert.equal(maskBirthdayCouponMemberNo("1234567890"), "12****7890");
  assert.equal(maskBirthdayCouponMemberNo("1234"), "1234");
  assert.equal(maskBirthdayCouponMemberNo(""), "—");
});

test("member names and coupon asset references are masked for drilldown display", () => {
  assert.equal(maskBirthdayCouponMemberName("张三"), "张*");
  assert.equal(maskBirthdayCouponMemberName("欧阳娜娜"), "欧***");
  assert.equal(birthdayCouponAssetLabel("", "123456789", 0), "资产序号 …456789");
  assert.equal(birthdayCouponAssetLabel("0", "123456789", 0), "资产序号 …456789");
  assert.equal(birthdayCouponAssetLabel("L-001", "123456789", 0), "L-001");
});

test("export filename includes the selected coupon and cohort range", () => {
  const filename = birthdayCouponExportFilename({
    scope: { coupon_type: "C", coupon_name: "美妆券", start_month: "2026-06", end_month: "2026-08" },
    summary: {},
    monthly: [],
    daily: [],
    departments: [],
    groups: [],
    members: [],
    quality_issues: [],
    detail: {},
    source: {},
  });
  assert.equal(filename, "中心美妆券C券分析_2026-06_2026-08.xlsx");
});

test("department drilldown returns only its coupon-use groups", () => {
  const report = {
    scope: {}, summary: {}, monthly: [], daily: [], departments: [], members: [], quality_issues: [], detail: {}, source: {},
    groups: [
      { department_code: "6010117", group_code: "G1", group_name: "女装一组" },
      { department_code: "6010113", group_code: "G2", group_name: "女装二组" },
      { department_code: "6010117", group_code: "G3", group_name: "女装三组" },
    ],
  };
  assert.deepEqual(
    centerCouponGroupsForDepartment(report, "6010117").map((row) => row.group_code),
    ["G1", "G3"],
  );
});

test("export workbook includes member-level, monthly-ticket, and coupon usage drilldowns", () => {
  const report = {
    scope: { coupon_type: "C", coupon_name: "美妆券", start_month: "2026-08", end_month: "2026-08" },
    summary: {}, monthly: [], daily: [], departments: [], groups: [], members: [], quality_issues: [], detail: {}, source: {},
  };
  const workbook = buildBirthdayCouponWorkbook(report, {
    member_levels: [{ period_month: "2026-08-01", customer_level: "黑钻卡会员", issued_member_count: 282 }],
    level_members: [{ period_month: "2026-08-01", member_no: "123456", customer_level: "黑钻卡会员", monthly_sales_amount: 1000 }],
    member_sales: [{ period_month: "2026-08-01", member_no: "123456", groups: "示例柜组", sales_amount: 1000 }],
    usage_flows: [{ period_month: "2026-08-01", member_no: "123456", group_names: "示例柜组", sales_amount: 1000 }],
    followups: [{ period_month: "2026-08-01", member_no: "123456", followup_group_name: "示例柜组", manager_name: "示例主管", followup_status_label: "未到店" }],
    detail: {},
  });

  assert.deepEqual(
    workbook.SheetNames.filter((name) => ["会员级别汇总", "会员月消费", "会员月消费小票", "用券明细"].includes(name)),
    ["会员级别汇总", "会员月消费", "会员月消费小票", "用券明细"],
  );
  assert.equal(workbook.Sheets["用券明细"].O1.v, "消费柜组");
  assert.equal(workbook.Sheets["用券明细"].O2.v, "示例柜组");
  assert.equal(workbook.Sheets["会员月消费小票"].K2.v, "示例柜组");
  assert.equal(workbook.Sheets["C券会员跟进"].F2.v, "示例柜组");
  assert.equal(workbook.Sheets["C券会员跟进"].H2.v, "示例主管");
});
