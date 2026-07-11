import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import * as pointsActivityAnalysis from "./points-activity-analysis.ts";

const {
  DEPARTMENT_SCOPE_ALL_LABEL,
  DEPARTMENT_SCOPE_ALL_VALUE,
  POINTS_ACTIVITY_START_DATE,
  clampPointsActivityEndDate,
  memberLevelLabel,
  memberLevelSearchKeyword,
  pointAnalysisQueryMessage,
  pointsActivityDefaultEndDate,
  pointTicketTimeLabel,
  salesSharePercent,
  pointStatusLabel,
  pointStatusTone,
} = pointsActivityAnalysis;

function queryMessage(state) {
  try {
    return pointAnalysisQueryMessage(state);
  } catch (error) {
    return `threw: ${error instanceof Error ? error.message : String(error)}`;
  }
}

test("maps backend point statuses to user-facing labels", () => {
  assert.equal(pointStatusLabel("OK"), "正常");
  assert.equal(pointStatusLabel("POINT_DIFF"), "积分差异");
  assert.equal(pointStatusLabel("MISSING_RATE"), "缺积分倍率");
  assert.equal(pointStatusLabel("ZERO_RATE"), "积分率为0");
  assert.equal(pointStatusLabel("ALLOCATION_IMBALANCE"), "付款分摊不平");
  assert.equal(pointStatusLabel("unknown"), "待复核");
});

test("marks degraded statuses as warning or danger", () => {
  assert.equal(pointStatusTone("OK"), "success");
  assert.equal(pointStatusTone("POINT_DIFF"), "danger");
  assert.equal(pointStatusTone("MISSING_RATE"), "warning");
});

test("reports the mid-year celebration loading state", () => {
  assert.equal(queryMessage({ isLoading: true }), "正在加载中心年中庆活动数据...");
});

test("reports a permission-specific message for dashboard status 403", () => {
  assert.equal(
    queryMessage({ isError: true, error: new Error("API请求失败: 403 - Forbidden") }),
    "无中心年中庆活动查看权限",
  );
});

test("reports a retryable timeout message for status 504 or timeout text", () => {
  const message = "中心年中庆活动数据查询超时，请缩短日期范围后重试";

  assert.equal(queryMessage({ isError: true, error: new Error("API请求失败: 504 - Gateway Timeout") }), message);
  assert.equal(queryMessage({ isError: true, error: new Error("请求超时，请稍后重试") }), message);
});

test("reports the generic mid-year celebration dashboard error", () => {
  assert.equal(
    queryMessage({ isError: true, error: new Error("API请求失败: 500 - Internal Server Error") }),
    "中心年中庆活动数据加载失败，请稍后重试或检查后端服务",
  );
});

test("reports the scoped empty state only after successful dashboard data", () => {
  const emptyData = { departments: [], groups: [], members: [], tickets: [] };

  assert.equal(queryMessage({ data: emptyData }), "当前日期和权限范围内暂无数据");
  assert.equal(queryMessage({ data: { ...emptyData, departments: [{ department_name: "中心二部" }] } }), null);
  assert.equal(queryMessage({}), null);
});

test("clamps the default points activity date range to the activity start", () => {
  assert.equal(POINTS_ACTIVITY_START_DATE, "2026-07-09");
  assert.equal(typeof pointsActivityDefaultEndDate, "function");
  assert.equal(pointsActivityDefaultEndDate("2026-07-08"), "2026-07-09");
  assert.equal(pointsActivityDefaultEndDate("2026-07-09"), "2026-07-09");
  assert.equal(pointsActivityDefaultEndDate("2026-07-10"), "2026-07-10");
});

test("clamps the candidate end date to the current start date", () => {
  assert.equal(typeof clampPointsActivityEndDate, "function");
  assert.equal(clampPointsActivityEndDate("2026-07-10", "2026-07-09"), "2026-07-10");
  assert.equal(clampPointsActivityEndDate("2026-07-10", "2026-07-11"), "2026-07-11");
});

test("maps member level codes to business labels", () => {
  assert.equal(memberLevelLabel("01"), "银星");
  assert.equal(memberLevelLabel("02"), "金星");
  assert.equal(memberLevelLabel("03"), "黑金");
  assert.equal(memberLevelLabel("04"), "黑钻");
  assert.equal(memberLevelLabel(""), "未标识");
});

test("maps member level labels back to searchable codes", () => {
  assert.equal(memberLevelSearchKeyword("黑金"), "03");
  assert.equal(memberLevelSearchKeyword("黑钻"), "04");
  assert.equal(memberLevelSearchKeyword("880100029069"), "880100029069");
});

test("formats ticket sale time to seconds", () => {
  assert.equal(pointTicketTimeLabel("2026-07-09T10:48:54"), "2026-07-09 10:48:54");
  assert.equal(pointTicketTimeLabel("2026-07-09 10:48:54"), "2026-07-09 10:48:54");
  assert.equal(pointTicketTimeLabel(null), "-");
});

test("formats sales share percentages for the summary strip", () => {
  assert.equal(salesSharePercent(25, 100), "25.0%");
  assert.equal(salesSharePercent(1, 3), "33.3%");
  assert.equal(salesSharePercent(0, 0), "0.0%");
});

test("labels all department option as scoped to permissions", () => {
  assert.equal(DEPARTMENT_SCOPE_ALL_VALUE, "__scope_all_departments__");
  assert.equal(DEPARTMENT_SCOPE_ALL_LABEL, "权限内全部部门");
});

test("points page exposes department to group drilldown labels", () => {
  const page = readFileSync(new URL("../pages/activity-analysis/points.tsx", import.meta.url), "utf8");

  assert.match(page, /部门汇总/);
  assert.match(page, /柜组汇总/);
  assert.match(page, /返回部门汇总/);
  assert.match(page, /黑金人数/);
  assert.match(page, /黑钻人数/);
  assert.ok(page.indexOf("黑钻人数") < page.indexOf("黑金人数"), "黑钻人数应排在黑金人数前面");
  assert.match(page, /实际积分发放数/);
  assert.match(page, /actual_point/);
  assert.match(page, /合计/);
  assert.match(page, /黑钻会员销售/);
  assert.match(page, /黑金会员销售/);
  assert.match(page, /金星会员销售/);
  assert.match(page, /银星会员销售/);
  assert.match(page, /非会员销售/);
  assert.match(page, /占比/);
  assert.match(page, /总人数/);
  assert.match(page, /人数/);
  assert.match(page, /人数占比/);
});

test("uses the mid-year celebration name in the dashboard label and page heading", () => {
  const dashboard = readFileSync(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8");
  const page = readFileSync(new URL("../pages/activity-analysis/points.tsx", import.meta.url), "utf8");

  assert.match(dashboard, /"points-activity-analysis": "中心年中庆活动"/);
  assert.match(page, /<h1[^>]*>中心年中庆活动<\/h1>/);
});

test("uses the activity date boundary for both points page date inputs", () => {
  const page = readFileSync(new URL("../pages/activity-analysis/points.tsx", import.meta.url), "utf8");

  assert.match(page, /useState\(POINTS_ACTIVITY_START_DATE\)/);
  assert.match(page, /useState\(\(\) => pointsActivityDefaultEndDate\(localDate\(\)\)\)/);
  assert.equal((page.match(/min=\{POINTS_ACTIVITY_START_DATE\}/g) || []).length, 2);
  assert.match(page, /setEndDate\(\(currentEndDate\) => clampPointsActivityEndDate\(value, currentEndDate\)\)/);
  assert.match(page, /setEndDate\(clampPointsActivityEndDate\(startDate, value\)\)/);
});

test("loads department options from the single dashboard query", () => {
  const page = readFileSync(new URL("../pages/activity-analysis/points.tsx", import.meta.url), "utf8");

  assert.match(page, /type DashboardResponse = \{[\s\S]*?department_options: Row\[\];/);
  assert.doesNotMatch(page, /DepartmentOptionsResponse/);
  assert.equal((page.match(/\buseQuery\s*</g) || []).length, 1);
  assert.doesNotMatch(page, /\/api\/activity-analysis\/points\/department-options/);
  assert.doesNotMatch(page, /departmentOptions\.refetch\(\)/);
  assert.match(page, /dashboard\.data\?\.department_options/);
  assert.equal((page.match(/dashboard\.refetch\(\)/g) || []).length, 1);
  assert.match(page, /pointAnalysisQueryMessage\(dashboard\)/);
});

test("shows query feedback before content and hides dashboard content on HTTP errors", () => {
  const page = readFileSync(new URL("../pages/activity-analysis/points.tsx", import.meta.url), "utf8");
  const messageIndex = page.indexOf("{queryMessage ?");
  const summaryIndex = page.indexOf("总销售额");

  assert.ok(messageIndex >= 0, "query message should be rendered");
  assert.ok(summaryIndex > messageIndex, "query message should be rendered before summary/detail content");
  assert.match(page, /\{!dashboard\.isError \? \(\s*<>/);
});
