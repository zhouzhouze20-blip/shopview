import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import XLSX from "xlsx-js-style";
import { summarizeHolderPeriod, holderPeriodDetails } from "./coupon-live.ts";
import { buildLiveWorkbook, liveExportSheets, includesMemberSheets, liveExportFilename } from "./coupon-live-export.ts";

const member = "001234567890123456789";
const day = "2026-09-18";
const detail = (bill, sales, changes = {}) => ({ holder_member_no: member, used_coupon_types: ["E", "H"],
  checkout_member_no: member, billno: bill, original_billno: "0", sale_time: `${day} 12:00:00`,
  ticket_kind: sales < 0 ? "退货" : "销售", event_type: "本人购物", ticket_coupon_types: ["E"],
  coupon_types: "E", department: "三部", department_code: "D3", group_code: "G1", group_name: "一柜",
  brand_code: "BR1", brand_name: "品牌", supplier_code: "SP1", sales, gross_profit: sales / 10, ...changes });
const report = () => {
  const result = { status: "ready", tracking_start: day, valid_to: "2026-09-27", query_start: day, query_end: day,
  today: day, generated_at: `${day}T13:00:00`, periods: [], trajectory_available: true, member_period_available: true,
  scope: { mode: "business_scope", store_code: "601", label: "三部授权范围" },
  holders: [{ holder_member_no: member, used_coupon_types: ["E", "H"] },
    { holder_member_no: "M2", used_coupon_types: ["E"] }, { holder_member_no: "ZERO", used_coupon_types: ["E"] }],
  member_trajectory: [detail("001", 100), detail("001", 200, { group_code: "G2" }),
    detail("002", 50, { ticket_coupon_types: ["H"] }),
    detail("003", -20, { original_billno: "002", ticket_coupon_types: ["H"] }),
    detail("004", 800, { checkout_member_no: "M2" }), detail("005", -100, { checkout_member_no: "" }),
    detail("004", 800, { holder_member_no: "M2", used_coupon_types: ["E"], checkout_member_no: "M2" }),
    detail("001", 100)], // Duplicate evidence must not double-count the same source grain.
  coupons: [], daily: [], departments: [], groups: [], tickets: [],
  };
  return { ...result, trajectory: [...result.member_trajectory] };
};
const view = (changes = {}) => ({ tab: "members", coupon: "E", member: "", ticketCoupon: "all",
  departmentCoupon: null, department: null, holder: null, detailMode: "other", ...changes });

test("member total includes all own receipt groups and signed returns, not proxy receipts", () => {
  const rows = summarizeHolderPeriod(report(), "E", "");
  const own = rows.find(row => row.holder_member_no === member);
  assert.equal(own.period_own_sales, 330);
  assert.equal(own.period_other_sales, 30);
  assert.equal(own.period_own_returns, -20);
  assert.equal(own.period_sale_tickets, 2);
  assert.equal(own.period_return_tickets, 1);
  assert.equal(own.period_related_sales, 700);
  assert.equal(rows.find(row => row.holder_member_no === "M2").period_own_sales, 800);
  assert.equal(rows.find(row => row.holder_member_no === "ZERO").period_own_sales, 0);
  assert.equal(rows.reduce((total, row) => total + row.period_own_sales, 0), 1130);
});

test("click details distinguish other purchases, all own shopping and mismatched receipts", () => {
  const r = report();
  assert.deepEqual(holderPeriodDetails(r, "E", "", member, "other").map(row => row.billno), ["002", "003"]);
  assert.equal(holderPeriodDetails(r, "E", "", member, "own").length, 4);
  assert.deepEqual(holderPeriodDetails(r, "E", "", member, "related").map(row => row.billno), ["004", "005"]);
  assert.equal(holderPeriodDetails(r, "E", "", member, "all").length, 6);
  assert.equal(summarizeHolderPeriod(r, "H", "")[0].period_other_sales, 300);
  assert.equal(summarizeHolderPeriod(r, "all", "").find(row => row.holder_member_no === member).period_other_sales, 0);
  assert.deepEqual(holderPeriodDetails(r, "B", "", member, "all"), []);
  assert.deepEqual(holderPeriodDetails(r, "E", "M2", member, "all"), []);
});

test("same group with different supplier is retained and cent totals are stable", () => {
  const r = report();
  r.member_trajectory = [detail("1", .1), detail("1", .2, { supplier_code: "SP2" })];
  assert.equal(summarizeHolderPeriod(r, "E", member)[0].period_own_sales, .3);
  assert.equal(summarizeHolderPeriod(r, "E", member)[0].period_sale_tickets, 1);
});

test("other classification considers coupon use by any holder on the same receipt", () => {
  const r = report();
  r.member_trajectory = [detail("1", 100, { coupon_types: "H", ticket_coupon_types: ["E", "H"] })];
  assert.equal(summarizeHolderPeriod(r, "E", member)[0].period_other_sales, 0);
  assert.deepEqual(holderPeriodDetails(r, "E", "", member, "other"), []);
});

test("no stale date, unknown member or missing backend fields silently become zero", () => {
  const r = report();
  r.member_trajectory.push(detail("old", 9999, { sale_time: "2026-09-17 12:00:00" }));
  r.member_trajectory.push(detail("hidden", 9999, { holder_member_no: "HIDDEN" }));
  assert.equal(summarizeHolderPeriod(r, "E", member)[0].period_own_sales, 330);
  for (const unavailable of [{ ...r, holders: undefined }, { ...r, member_period_available: false }]) {
    assert.deepEqual(summarizeHolderPeriod(unavailable, "E", ""), []);
    assert.deepEqual(holderPeriodDetails(unavailable, "E", ""), []);
    assert.throws(() => buildLiveWorkbook(unavailable, view()), /尚未就绪|本档/);
  }
  assert.throws(() => buildLiveWorkbook({ ...r, status: "choose_period" }, view()), /尚未就绪/);
});

test("Excel roundtrip matches member view, preserves card text, amounts and scope", () => {
  const r = report();
  const wb = buildLiveWorkbook(r, view({ holder: member }));
  const restored = XLSX.read(XLSX.write(wb, { type: "buffer", bookType: "xlsx" }), { type: "buffer" });
  assert.deepEqual(restored.SheetNames, ["会员期间汇总", "会员期间明细", "导出口径"]);
  assert.equal(restored.Sheets["会员期间汇总"].A2.t, "s");
  assert.equal(restored.Sheets["会员期间汇总"].A2.v, member);
  assert.equal(restored.Sheets["会员期间汇总"].C2.v, 330);
  assert.equal(restored.Sheets["会员期间汇总"].D2.v, 30);
  assert.equal(restored.Sheets["会员期间汇总"].C2.t, "n");
  const details = XLSX.utils.sheet_to_json(restored.Sheets["会员期间明细"]);
  assert.deepEqual(details.map(row => row["小票序号"]), ["002", "003"]);
  assert.equal(details.reduce((sum, row) => sum + row["本范围销售收入（元）"], 0), 30);
  const meta = XLSX.utils.sheet_to_json(restored.Sheets["导出口径"]);
  assert.ok(meta.some(row => row["项目"] === "数据权限" && row["说明"] === "三部授权范围"));
  assert.ok(meta.some(row => row["项目"] === "下钻会员" && row["说明"] === member));
});

test("historical export uses selected September 18 sales, never system September 19 sales", () => {
  const r = report();
  r.today = "2026-09-19";
  r.trajectory = [detail("today", 9999, { sale_time: "2026-09-19 10:00:00" })];
  const wb = buildLiveWorkbook(r, view({ member }));
  const restored = XLSX.read(XLSX.write(wb, { type: "buffer", bookType: "xlsx" }), { type: "buffer" });
  assert.equal(restored.Sheets["会员期间汇总"].C2.v, 330);
  assert.equal(restored.Sheets["会员期间汇总"].D2.v, 30);
  assert.ok(holderPeriodDetails(r, "E", member).every(row => row.sale_time.startsWith(day)));
  const meta = XLSX.utils.sheet_to_json(restored.Sheets["导出口径"]);
  assert.ok(meta.some(row => row["项目"] === "会员消费统计期" && row["说明"] === `${day} 至 ${day}（含首尾日期）`));
  assert.equal(liveExportFilename(r, view()), "秋v卡券跟进_会员期间汇总_2026-09-18_2026-09-18.xlsx");
  assert.match(liveExportFilename(r, view({ tab: "trajectory" })), /2026-09-18_2026-09-18_今日2026-09-19/);
  const trajectory = liveExportSheets(r, view({ tab: "trajectory" }))[0];
  assert.equal(trajectory.rows[0].sales, 9999);
});

test("selected period includes both endpoint dates and excludes adjacent dates", () => {
  const r = report();
  r.today = "2026-09-20";
  r.query_end = "2026-09-19";
  r.member_trajectory = [
    detail("before", 9999, { sale_time: "2026-09-17 23:59:59" }),
    detail("start", 100, { sale_time: "2026-09-18 00:00:00" }),
    detail("end", 200, { sale_time: "2026-09-19 23:59:59", ticket_coupon_types: [] }),
    detail("after", 9999, { sale_time: "2026-09-20 00:00:00" }),
  ];
  assert.equal(summarizeHolderPeriod(r, "E", member)[0].period_own_sales, 300);
  assert.equal(summarizeHolderPeriod(r, "E", member)[0].period_other_sales, 200);
  r.query_start = "2026-09-19";
  assert.equal(summarizeHolderPeriod(r, "E", member)[0].period_own_sales, 200);
  assert.deepEqual(holderPeriodDetails(r, "E", member).map(row => row.billno), ["end"]);
});

test("historical members remain available after campaign but old backend cannot substitute today", () => {
  const r = { ...report(), today: "2026-10-01", trajectory_available: false, trajectory: [] };
  assert.equal(buildLiveWorkbook(r, view({ member })).Sheets["会员期间汇总"].C2.v, 330);
  for (const missing of [{ ...r, member_trajectory: undefined }, { ...r, query_start: undefined }]) {
    assert.deepEqual(summarizeHolderPeriod(missing, "E", member), []);
    assert.throws(() => buildLiveWorkbook(missing, view()), /尚未就绪/);
  }
});

test("export is not truncated to 50 rows, source strings cannot become formulas", () => {
  const r = report();
  r.member_trajectory = Array.from({ length: 61 }, (_, i) => detail(String(i).padStart(5, "0"), 1, { brand_name: '=HYPERLINK("bad")' }));
  const wb = buildLiveWorkbook(r, view({ member }));
  const sheet = wb.Sheets["会员期间明细"];
  assert.equal(XLSX.utils.sheet_to_json(sheet).length, 61);
  assert.equal(wb.Sheets["会员期间汇总"].C2.v, 61);
  assert.equal(sheet.M2.t, "s");
  assert.equal(sheet.M2.f, undefined);
  assert.equal(sheet.M2.v, '=HYPERLINK("bad")');
});

test("overview and trajectory exports include the displayed member summary and details", () => {
  for (const tab of ["overview", "trajectory"]) {
    const wb = buildLiveWorkbook(report(), view({ tab, coupon: "E", member, holder: "M2" }));
    const restored = XLSX.read(XLSX.write(wb, { type: "buffer", bookType: "xlsx" }), { type: "buffer" });
    assert.ok(restored.SheetNames.includes(tab === "overview" ? "卡券汇总" : "持券人今日轨迹"));
    assert.ok(restored.SheetNames.includes("会员期间汇总"));
    assert.ok(restored.SheetNames.includes("会员期间明细"));
    assert.equal(new Set(restored.SheetNames).size, restored.SheetNames.length);
    const rows = XLSX.utils.sheet_to_json(restored.Sheets["会员期间汇总"]);
    assert.equal(rows.length, 1);
    assert.equal(rows[0]["持券会员卡"], member);
    assert.equal(rows[0]["所选期间用券"], "E、H");
    assert.equal(rows[0]["所选期间本人合计销售（元）"], 330);
    assert.equal(rows[0]["其中其他消费净额（元）"], 30);
    assert.equal(rows[0]["本人退货（负数，已计入合计）"], -20);
    assert.equal(rows[0]["本人销售小票数"], 2);
    assert.equal(rows[0]["本人退货小票数"], 1);
    assert.equal(rows[0]["购物会员不同或未登记关联净额（元）"], 700);
    assert.equal(XLSX.utils.sheet_to_json(restored.Sheets["会员期间明细"]).length, 6);
    const meta = XLSX.utils.sheet_to_json(restored.Sheets["导出口径"]);
    assert.ok(meta.some(row => row["项目"] === "会员附表券种筛选" && row["说明"] === "E"));
    assert.ok(meta.some(row => row["项目"] === "会员查找" && row["说明"] === member));
  }
});

test("member annex follows coupon filter including all and unavailable data stays explicit", () => {
  const r = report();
  const forCoupon = coupon => liveExportSheets(r, view({ tab: "overview", coupon }))
    .find(sheet => sheet.name === "会员期间汇总").rows;
  assert.equal(forCoupon("H").length, 1);
  assert.equal(forCoupon("H")[0].period_other_sales, 300);
  assert.equal(forCoupon("all").length, 3);
  assert.equal(forCoupon("B").length, 0);
  for (const unavailable of [{ ...r, holders: undefined }, { ...r, member_period_available: false }]) {
    const wb = buildLiveWorkbook(unavailable, view({ tab: "overview" }));
    assert.ok(wb.SheetNames.includes("卡券汇总"));
    assert.ok(!wb.SheetNames.includes("会员期间汇总"));
    const meta = XLSX.utils.sheet_to_json(wb.Sheets["导出口径"]);
    assert.ok(meta.some(row => row["项目"] === "会员附表" && /不代表消费为零/.test(row["说明"])));
  }
  assert.equal(includesMemberSheets("overview", "E"), false);
  assert.equal(includesMemberSheets("tickets", null), false);
  const drill = buildLiveWorkbook(r, view({ tab: "overview", departmentCoupon: "E" }));
  assert.deepEqual(drill.SheetNames, ["部门使用情况", "导出口径"]);
});

test("G coupon member totals, other shopping and Excel follow the same selected cohort", () => {
  const r = report();
  r.holders = [{ holder_member_no: member, used_coupon_types: ["G"] },
    { holder_member_no: "E_ONLY", used_coupon_types: ["E"] }];
  r.member_trajectory = [detail("001", 100, { used_coupon_types: ["G"], ticket_coupon_types: ["G"] }),
    detail("002", 30, { used_coupon_types: ["G"], ticket_coupon_types: [] }),
    detail("003", -10, { used_coupon_types: ["G"], ticket_coupon_types: [], original_billno: "002" }),
    detail("004", 999, { holder_member_no: "E_ONLY", checkout_member_no: "E_ONLY" })];
  assert.equal(summarizeHolderPeriod(r, "G", "")[0].period_own_sales, 120);
  assert.equal(summarizeHolderPeriod(r, "G", "")[0].period_other_sales, 20);
  assert.deepEqual(holderPeriodDetails(r, "G", "", member, "other").map(row => row.billno), ["002", "003"]);
  for (const tab of ["members", "trajectory", "overview"]) {
    const wb = buildLiveWorkbook(r, view({ tab, coupon: "G" }));
    const restored = XLSX.read(XLSX.write(wb, { type: "buffer", bookType: "xlsx" }), { type: "buffer" });
    const summary = XLSX.utils.sheet_to_json(restored.Sheets["会员期间汇总"]);
    assert.equal(summary.length, 1);
    assert.equal(summary[0]["所选期间用券"], "G");
    assert.equal(summary[0]["所选期间本人合计销售（元）"], 120);
    assert.equal(XLSX.utils.sheet_to_json(restored.Sheets["会员期间明细"]).length, 3);
    const meta = XLSX.utils.sheet_to_json(restored.Sheets["导出口径"]);
    assert.ok(meta.some(row => row["项目"] === "会员附表券种筛选" && row["说明"] === "G"));
  }
  const all = buildLiveWorkbook(r, view({ tab: "overview", coupon: "all" }));
  assert.ok(XLSX.utils.sheet_to_json(all.Sheets["导出口径"])
    .some(row => row["项目"] === "券种筛选" && row["说明"] === "J、D、R、E、B、H、G"));
});

test("exports for other tabs honor coupon and organization drilldown filters", () => {
  const r = report();
  r.tickets = [{ coupon_type: "E", billno: "1" }, { coupon_type: "B", billno: "2" }];
  assert.deepEqual(liveExportSheets(r, view({ tab: "tickets", ticketCoupon: "B" }))[0].rows, [r.tickets[1]]);
  r.groups = [{ department_code: "D3", department: "三部", coupon_type: "E", group_code: "G1" },
    { department_code: "D4", department: "四部", coupon_type: "E", group_code: "G2" }];
  assert.deepEqual(liveExportSheets(r, view({ tab: "overview", departmentCoupon: "E", department: { code: "D3", name: "三部" } }))[0].rows, [r.groups[0]]);
  assert.ok(liveExportSheets(r, view({ tab: "trajectory", member: "M2" }))[0].rows.every(row => row.holder_member_no === "M2"));
});

test("UI exposes member drilldown and guards export while refreshing or denied", async () => {
  const page = await readFile(new URL("../pages/activity-analysis/coupon-live.tsx", import.meta.url), "utf8");
  assert.match(page, /TabsTrigger value="members">会员期间汇总/);
  assert.match(page, /onHolderClick=\{openHolder\}/);
  assert.match(page, /aria-label=\{`查看会员\$\{row.holder_member_no\}所选期间其他消费`\}/);
  assert.match(page, /onClick=\{returnToMembers\}/);
  assert.match(page, /disabled=\{exportDisabled\} onClick=\{exportCurrent\}/);
  assert.match(page, /!ready \|\| !data \|\| query.isFetching \|\| adminViewLoading \|\| loading/);
  assert.match(page, /exportLiveWorkbook\(data,/);
  assert.match(page, /setSelectedHolder\(null\)/);
  assert.match(page, /导出会员汇总及明细/);
  assert.match(page, /导出Excel（含会员汇总）/);
});
