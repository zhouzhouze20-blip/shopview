import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import { navigationItems } from "./navigation-items.ts";
import { MODULE_PERMISSION_REQUIREMENTS } from "./module-permissions.ts";
import {
  brandMemberAiFallbackMessage,
  brandMemberCrossShoppingRequest,
  brandMemberRequest,
  buildAiSnapshot,
  filterBrandMemberGroups,
  previousPeriod,
  priorYearPeriod,
  sortBrandMemberCrossShoppingRows,
} from "./brand-member-analysis.ts";


function findItem(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findItem(item.subItems || [], id);
    if (child) return child;
  }
  return null;
}


test("brand member analysis is placed under member analysis and has an independent permission", () => {
  const group = findItem(navigationItems, "member-analysis-group");
  const page = findItem(navigationItems, "brand-member-analysis");

  assert.equal(group.name, "会员经营分析");
  assert.equal(page.name, "品牌会员分析");
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["brand-member-analysis"], ["sales.brand_member_analysis.view"]);
});


test("competitors are optional in the report request", () => {
  const request = brandMemberRequest({
    storeCode: "603",
    targetGroupCode: "6030103081",
    competitorGroupCodes: [],
    currentStart: "2025-01-01",
    currentEnd: "2025-01-31",
    priorStart: "2024-01-01",
    priorEnd: "2024-01-31",
  });

  assert.deepEqual(request.competitor_group_codes, []);
  assert.equal(request.current_start, "2025-01-01");
  assert.equal(request.prior_start, "2024-01-01");
});


test("cross-shopping request only uses the current target-brand period", () => {
  const request = brandMemberCrossShoppingRequest({
    storeCode: "601",
    targetGroupCode: "6010101168",
    competitorGroupCodes: ["OTHER"],
    currentStart: "2026-08-01",
    currentEnd: "2026-08-31",
    priorStart: "2025-08-01",
    priorEnd: "2025-08-31",
  });

  assert.deepEqual(request, {
    store_code: "601",
    target_group_code: "6010101168",
    start_date: "2026-08-01",
    end_date: "2026-08-31",
  });
});


test("cross-shopping rows can rank by amount or unique buyers", () => {
  const rows = [
    { name: "A", buyer_count: 9, sales_revenue: 100 },
    { name: "B", buyer_count: 3, sales_revenue: 300 },
    { name: "C", buyer_count: 12, sales_revenue: 100 },
  ];

  assert.deepEqual(
    sortBrandMemberCrossShoppingRows(rows, "sales_revenue").map((row) => row.name),
    ["B", "C", "A"],
  );
  assert.deepEqual(
    sortBrandMemberCrossShoppingRows(rows, "buyer_count").map((row) => row.name),
    ["C", "A", "B"],
  );
  assert.deepEqual(rows.map((row) => row.name), ["A", "B", "C"]);
});


test("brand member page exposes the cross-shopping tab and department drilldown", async () => {
  const source = await readFile(
    new URL("../pages/member-analysis/brand-member-analysis.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /跨部门 \/ 跨品牌消费/);
  assert.match(source, /\/api\/sales\/brand-member-analysis\/cross-shopping/);
  assert.match(source, /\/api\/sales\/brand-member-analysis\/inflow-sources/);
  assert.match(source, /部门排行/);
  assert.match(source, /setSelectedCrossDepartmentCode\(department\.department_code\)/);
  assert.match(source, /按消费金额/);
  assert.match(source, /按人数/);
  assert.match(source, /按需加载/);
});


test("brand groups support fuzzy name, code, and department lookup", () => {
  const groups = [
    {
      group_code: "6010113060",
      group_name: "Luxemporium睿锦尚品厅",
      department_code: "6010113",
      department_name: "中心二部(女装)",
    },
    {
      group_code: "6010114020",
      group_name: "另一品牌",
      department_code: "6010114",
      department_name: "中心三部",
    },
  ];

  assert.deepEqual(filterBrandMemberGroups(groups, "睿锦"), [groups[0]]);
  assert.deepEqual(filterBrandMemberGroups(groups, "6010113060"), [groups[0]]);
  assert.deepEqual(filterBrandMemberGroups(groups, "luxem 女装"), [groups[0]]);
});


test("comparison period shortcuts keep periods independently selectable", () => {
  assert.deepEqual(priorYearPeriod("2024-02-29", "2024-03-31"), {
    priorStart: "2023-02-28",
    priorEnd: "2023-03-31",
  });
  assert.deepEqual(previousPeriod("2025-03-01", "2025-03-31"), {
    priorStart: "2025-01-29",
    priorEnd: "2025-02-28",
  });
});


test("AI snapshot contains aggregate report sections and no member list", () => {
  const snapshot = buildAiSnapshot({
    scope: { store_code: "603", target_group_code: "G1", competitor_group_codes: [] },
    target: {
      group_code: "G1",
      group_name: "目标柜组",
      department_code: "D1",
      department_name: "目标部门",
      current: { summary: {}, segments: [], member_level_consumption: [], old_customer_funnel: {}, inflow_sources: [], period: {} },
      prior: { summary: {}, segments: [], member_level_consumption: [], old_customer_funnel: {}, inflow_sources: [], period: {} },
    },
    comparison: {},
    competitors: [],
    definitions: {},
  });

  assert.deepEqual(Object.keys(snapshot).sort(), ["comparison", "competitors", "definitions", "target"]);
  assert.equal(JSON.stringify(snapshot).includes("telephone"), false);
  assert.equal(JSON.stringify(snapshot).includes("member_no"), false);
});


test("AI fallback messages distinguish validation from service failures", () => {
  assert.equal(
    brandMemberAiFallbackMessage("guardrail_rejected"),
    "AI结论未通过数据校验，当前展示规则结论。",
  );
  assert.equal(
    brandMemberAiFallbackMessage("failed"),
    "AI服务暂不可用，当前展示规则结论。",
  );
  assert.equal(
    brandMemberAiFallbackMessage("truncated"),
    "AI返回内容不完整，当前展示规则结论。",
  );
});
