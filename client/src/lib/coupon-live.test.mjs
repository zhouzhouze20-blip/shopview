import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { LIVE_COUPON_TYPES, trajectoryColumns, filterTrajectory, filterCouponDepartments, filterCouponGroups, couponLiveQueryUrl, validateLiveQueryRange } from "./coupon-live.ts";
import { MODULE_PERMISSION_REQUIREMENTS } from "./module-permissions.ts";

test("coupon monitor uses the requested name in the menu, tab and page title", async () => {
  const [navigation, dashboard, page] = await Promise.all([
    readFile(new URL("./navigation-items.ts", import.meta.url), "utf8"),
    readFile(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../pages/activity-analysis/coupon-live.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(navigation, /id: "coupon-live", name: "秋v卡券跟进"/);
  assert.match(dashboard, /"coupon-live": "秋v卡券跟进"/);
  assert.match(page, /<h1[^>]*>秋v卡券跟进<\/h1>/);
  for (const source of [navigation, dashboard, page]) assert.doesNotMatch(source, /四券实时跟进/);
});

test("trajectory starts from holder use cohort and supports resetting to all", () => {
  const rows = [
    { holder_member_no: "0001", used_coupon_types: ["E", "R"] },
    { holder_member_no: "0002", used_coupon_types: ["J"] },
  ];
  assert.deepEqual(filterTrajectory(rows, "E", ""), [rows[0]]);
  assert.deepEqual(filterTrajectory(rows, "all", ""), rows);
  assert.deepEqual(filterTrajectory(rows, "all", "0002"), [rows[1]]);
  assert.equal(rows[0].holder_member_no, "0001");
});

test("native module reuses permission and clears data across errors and scope changes", async () => {
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["coupon-live"], ["activity_analysis.campaign.view"]);
  const page = await readFile(new URL("../pages/activity-analysis/coupon-live.tsx", import.meta.url), "utf8");
  assert.match(page, /queryKey: \["coupon-live", menuUser\?\.user_id, end, range\?\.start, range\?\.end\]/);
  assert.match(page, /!query.isError && !adminViewLoading && !loading/);
  assert.match(page, /refetchInterval: auto \? 60_000 : false/);
  assert.match(page, /gcTime: 0/);
  assert.doesNotMatch(page, /placeholderData/);
  assert.match(page, /不等于销售增长/);
});

test("coupon drilldown includes only authorized rows of the clicked coupon", () => {
  const visibleRows = [
    { department: "三部", coupon_type: "E", redeemed_amount: 100 },
    { department: "四部", coupon_type: "R", redeemed_amount: 200 },
    { department: "一部", coupon_type: "E", redeemed_amount: 300 },
    { department: "二部", coupon_type: "J", redeemed_amount: 50 },
  ];
  assert.deepEqual(filterCouponDepartments(visibleRows, "E"), [visibleRows[0], visibleRows[2]]);
  assert.deepEqual(filterCouponDepartments(visibleRows, "R"), [visibleRows[1]]);
  assert.deepEqual(filterCouponDepartments([visibleRows[0]], "E"), [visibleRows[0]]);
  assert.deepEqual(filterCouponDepartments(visibleRows, "D"), []);
  assert.deepEqual(filterCouponDepartments(visibleRows, null), []);
  assert.equal(visibleRows.length, 4);
});

test("summary coupon buttons open department detail with a return path", async () => {
  const page = await readFile(new URL("../pages/activity-analysis/coupon-live.tsx", import.meta.url), "utf8");
  assert.match(page, /onCouponClick=\{openDepartments\}/);
  assert.match(page, /aria-label=\{`查看\$\{row.coupon_type\}券各部门使用情况`\}/);
  assert.match(page, /filterCouponDepartments\(data\?\.departments \|\| \[\], departmentCoupon\)/);
  assert.match(page, /onClick=\{returnToSummary\}/);
  assert.match(page, /返回卡券汇总/);
  assert.match(page, /setDepartmentCoupon\(null\)/);
  assert.doesNotMatch(page, /rows=\{data.departments \|\| \[\]\}/);
});

test("department drilldown keeps coupon and department identity within supplied scope", () => {
  const rows = [
    { department_code: "D3", department: "女装", coupon_type: "R", group_code: "G1" },
    { department_code: "D3", department: "女装", coupon_type: "E", group_code: "G1" },
    { department_code: "D4", department: "女装", coupon_type: "R", group_code: "G2" },
    { department_code: "D3", department: "女装", coupon_type: "R", group_code: "G3" },
    { department_code: "", department: "未识别部门", coupon_type: "R", group_code: "G4" },
  ];
  const selected = { code: "D3", name: "女装" };
  assert.deepEqual(filterCouponGroups(rows, "R", selected), [rows[0], rows[3]]);
  assert.deepEqual(filterCouponGroups([rows[0]], "R", selected), [rows[0]]);
  assert.deepEqual(filterCouponGroups(rows, "D", selected), []);
  assert.deepEqual(filterCouponGroups(rows, null, selected), []);
  assert.deepEqual(filterCouponGroups(rows, "R", null), []);
  assert.deepEqual(filterCouponGroups(rows, "R", { code: "", name: "未识别部门" }), [rows[4]]);
  assert.equal(rows.length, 5);
});

test("department rows open group detail with an accessible button and return to same coupon", async () => {
  const page = await readFile(new URL("../pages/activity-analysis/coupon-live.tsx", import.meta.url), "utf8");
  assert.match(page, /onDepartmentClick=\{openGroups\}/);
  assert.match(page, /aria-label=\{`查看\$\{row.department\}柜组使用情况`\}/);
  assert.match(page, /filterCouponGroups\(data\?\.groups \|\| \[\], departmentCoupon, selectedDepartment\)/);
  assert.match(page, /rows=\{groupRows\} columns=\{groupColumns\}/);
  assert.match(page, /onClick=\{returnToDepartments\}/);
  assert.match(page, /返回\{departmentCoupon\}券部门列表/);
  const returnHandler = page.match(/const returnToDepartments = \(\) => \{([\s\S]*?)\n  \};/)[1];
  assert.match(returnHandler, /setSelectedDepartment\(null\)/);
  assert.doesNotMatch(returnHandler, /setDepartmentCoupon/);
  assert.match(page, /setSelectedDepartment\(null\);\s+setDepartmentCoupon\(null\);\s+\}, \[menuUser\?\.user_id, end, range\?\.start, range\?\.end\]\)/);
});

test("query dates are independent from coupon validity and can reset to ongoing period", () => {
  const url = new URL(couponLiveQueryUrl("2026-09-27", { start: "2026-09-19", end: "2026-09-19" }), "http://localhost");
  assert.equal(url.searchParams.get("valid_to"), "2026-09-27");
  assert.equal(url.searchParams.get("start_date"), "2026-09-19");
  assert.equal(url.searchParams.get("end_date"), "2026-09-19");
  assert.equal(couponLiveQueryUrl("", null), "/api/activity-analysis/coupon-live");
  assert.equal(couponLiveQueryUrl("2026-09-27", null), "/api/activity-analysis/coupon-live?valid_to=2026-09-27");
});

test("single-day dates are allowed, reversed, empty and future dates are rejected", () => {
  const validate = (start, end) => validateLiveQueryRange({ start, end }, "2026-09-18", "2026-09-19");
  assert.equal(validate("2026-09-19", "2026-09-19"), "");
  assert.equal(validate("2026-09-18", "2026-09-19"), "");
  assert.ok(validate("", "2026-09-19"));
  assert.ok(validate("2026-09-19", "2026-09-18"));
  assert.ok(validate("2026-09-17", "2026-09-19"));
  assert.ok(validate("2026-09-18", "2026-09-20"));
});

test("date controls apply to drilldown and disclose cumulative issuance and today's trajectory", async () => {
  const page = await readFile(new URL("../pages/activity-analysis/coupon-live.tsx", import.meta.url), "utf8");
  assert.match(page, /id="live-query-start"[^\n]*type="date"/);
  assert.match(page, /id="live-query-end"[^\n]*type="date"/);
  assert.match(page, /apiGet\(couponLiveQueryUrl\(end, range\)\)/);
  assert.match(page, /onClick=\{resetRange\}>本档至今/);
  assert.match(page, /data.query_start\} 至 \{data.query_end\} · 金额单位/);
  assert.match(page, /发放为截至/);
  assert.match(page, /所选期间用券持券人在今天的消费/);
});

test("B, H and G are included consistently in tracking, selectors and drilldowns", async () => {
  assert.deepEqual(LIVE_COUPON_TYPES, ["J", "D", "R", "E", "B", "H", "G"]);
  const page = await readFile(new URL("../pages/activity-analysis/coupon-live.tsx", import.meta.url), "utf8");
  assert.match(page, /LIVE_COUPON_TYPES\.join\(" \/ "\)/);
  assert.equal(page.match(/LIVE_COUPON_TYPES\.map\(/g)?.length, 3);
  assert.doesNotMatch(page, /四券|四种券/);
  assert.deepEqual(trajectoryColumns.find(([key]) => key === "coupon_types"), ["coupon_types", "本票使用跟踪券"]);
  const backend = await readFile(new URL("../../../python_app/services/activity_analysis/coupon_live.py", import.meta.url), "utf8");
  const backendTypes = [...backend.match(/^TYPES = \((.+)\)$/m)[1].matchAll(/"([A-Z])"/g)].map(match => match[1]);
  assert.deepEqual(backendTypes, LIVE_COUPON_TYPES);
  const rows = [
    { coupon_type: "B", used_coupon_types: ["B"], department_code: "D3", department: "三部", group_code: "G1" },
    { coupon_type: "H", used_coupon_types: ["H"], department_code: "D3", department: "三部", group_code: "G2" },
    { coupon_type: "G", used_coupon_types: ["G"], department_code: "D3", department: "三部", group_code: "G4" },
    { coupon_type: "E", used_coupon_types: ["E"], department_code: "D4", department: "四部", group_code: "G3" },
  ];
  for (const [index, type] of ["B", "H", "G"].entries()) {
    assert.deepEqual(filterTrajectory(rows, type, ""), [rows[index]]);
    assert.deepEqual(filterCouponDepartments(rows, type), [rows[index]]);
    assert.deepEqual(filterCouponGroups(rows, type, { code: "D3", name: "三部" }), [rows[index]]);
    assert.deepEqual(filterCouponGroups(rows, type, { code: "D4", name: "四部" }), []);
  }
  assert.deepEqual(filterTrajectory(rows, "all", ""), rows);
});
