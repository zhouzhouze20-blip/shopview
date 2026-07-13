import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import test from "node:test";
import { promisify } from "node:util";
import { readFile } from "node:fs/promises";

import {
  buildOd0002Params,
  contentDispositionFilename,
  formatMoneyWan,
  formatPercent,
  getOd0002QueryMessage,
  OD0002_TABS,
  paginateRows,
  previousYearDate,
  normalizeOd0002StoreOptions,
  scheduleObjectUrlRevoke,
  syncOd0002DraftFromGlobalStore,
  visibleOd0002Columns,
} from "./od0002-report.ts";

test("previousYearDate returns the same calendar day in the previous year", () => {
  assert.equal(previousYearDate("2026-07-10"), "2025-07-10");
});

test("previousYearDate clamps leap day to February 28", () => {
  assert.equal(previousYearDate("2024-02-29"), "2023-02-28");
});

test("previousYearDate rejects invalid ISO dates with a clear error", () => {
  assert.throws(
    () => previousYearDate("2026-02-30"),
    /Invalid ISO date: 2026-02-30/,
  );
  assert.throws(
    () => previousYearDate("not-a-date"),
    /Invalid ISO date: not-a-date/,
  );
});

test("previousYearDate rejects dates without a representable previous year", () => {
  assert.throws(
    () => previousYearDate("0001-01-01"),
    /Invalid ISO date: 0001-01-01/,
  );
});

test("buildOd0002Params omits the all-store sentinel", () => {
  assert.equal(
    buildOd0002Params("2026-05-29", "2026-06-28", "all").toString(),
    "start_date=2026-05-29&end_date=2026-06-28",
  );
});

test("buildOd0002Params omits an empty store", () => {
  assert.equal(
    buildOd0002Params("2026-05-29", "2026-06-28", "   ").toString(),
    "start_date=2026-05-29&end_date=2026-06-28",
  );
});

test("buildOd0002Params trims a selected store", () => {
  assert.equal(
    buildOd0002Params("2026-05-29", "2026-06-28", " 601 ").toString(),
    "start_date=2026-05-29&end_date=2026-06-28&store_id=601",
  );
});

test("department filter defaults to all and is reset when store changes", async () => {
  const module = await import("./od0002-report.ts");
  assert.equal(module.OD0002_ALL_DEPARTMENTS, "all");
  assert.deepEqual(
    module.changeOd0002Store(
      { start: "2026-01-01", end: "2026-01-31", storeId: "603", departmentId: "6030117" },
      "602",
    ),
    { start: "2026-01-01", end: "2026-01-31", storeId: "602", departmentId: "all" },
  );
});

test("buildOd0002Params sends one selected department", () => {
  const params = buildOd0002Params("2026-01-01", "2026-01-31", "603", " 6030117 ");
  assert.equal(params.get("department_id"), "6030117");
});

test("OD0002 exposes department with categories after department", () => {
  assert.deepEqual(
    OD0002_TABS.map((tab) => tab.label),
    ["分店", "部门", "部门（含品类）", "区域", "品类", "柜组", "楼层"],
  );
  assert.equal(OD0002_TABS[2].key, "department_categories");
});

test("department category rows expose four hierarchy identifiers", async () => {
  const module = await import("./od0002-report.ts");
  assert.equal(module.isOd0002DepartmentCategoryTab("department_categories"), true);
  assert.equal(module.isOd0002DepartmentCategoryTab("departments"), false);
  assert.deepEqual(module.OD0002_HIERARCHY_COLUMNS, ["store", "department", "area", "category"]);
});

test("formatMoneyWan converts yuan to ten-thousand yuan and preserves negative values", () => {
  assert.equal(formatMoneyWan(123456.78), "12.35");
  assert.equal(formatMoneyWan(-12345), "-1.23");
  assert.equal(formatMoneyWan(null), "—");
});

test("formatPercent renders ratios with two decimal places and null as dash", () => {
  assert.equal(formatPercent(0.12345), "12.35%");
  assert.equal(formatPercent(-0.2), "-20.00%");
  assert.equal(formatPercent(null), "—");
});

test("visible columns show store outside the stores tab only for all-store queries", () => {
  assert.equal(visibleOd0002Columns("departments", "all").includes("store"), true);
  assert.equal(visibleOd0002Columns("departments", "601").includes("store"), false);
  assert.equal(visibleOd0002Columns("stores", "all").includes("store"), false);
  assert.equal(visibleOd0002Columns("stores", "all").includes("dimension"), true);
});

test("paginateRows returns the requested fifty-row page and clamps invalid pages", () => {
  const rows = Array.from({ length: 121 }, (_, index) => index + 1);
  assert.deepEqual(paginateRows(rows, 2), rows.slice(50, 100));
  assert.deepEqual(paginateRows(rows, 99), rows.slice(100));
  assert.deepEqual(paginateRows(rows, 0), rows.slice(0, 50));
});

test("query message distinguishes permission, generic error, and empty results", () => {
  assert.equal(getOd0002QueryMessage({ error: new Error("API请求失败: 403 - 无功能权限") }), "无权限查看此报表");
  assert.equal(getOd0002QueryMessage({ error: new Error("API请求失败: 500") }), "报表加载失败，请稍后重试");
  assert.equal(getOd0002QueryMessage({ hasData: true, rowCount: 0 }), "暂无数据");
  assert.equal(getOd0002QueryMessage({ isLoading: true }), "正在加载报表…");
  assert.equal(getOd0002QueryMessage({ hasData: true, rowCount: 2 }), null);
});

test("contentDispositionFilename supports UTF-8 and quoted filenames safely", () => {
  assert.equal(
    contentDispositionFilename("attachment; filename*=UTF-8''OD0002_%E9%94%80%E5%94%AE.xlsx"),
    "OD0002_销售.xlsx",
  );
  assert.equal(contentDispositionFilename('attachment; filename="OD0002 report.xlsx"'), "OD0002 report.xlsx");
  assert.equal(contentDispositionFilename(null), null);
});

test("authorized store options use store codes accepted by the report endpoint", () => {
  assert.deepEqual(
    normalizeOd0002StoreOptions([{ store_id: 1, store_code: "601", store_name: "一店" }]),
    [{ value: "601", label: "一店" }],
  );
});

test("global store sync handles cold start and later changes without overwriting dirty drafts", () => {
  const draft = { start: "2026-07-01", end: "2026-07-09", storeId: "all" };
  assert.deepEqual(syncOd0002DraftFromGlobalStore(draft, 601, false), { ...draft, storeId: "601" });
  assert.deepEqual(syncOd0002DraftFromGlobalStore({ ...draft, storeId: "601" }, 602, false), { ...draft, storeId: "602" });
  assert.deepEqual(syncOd0002DraftFromGlobalStore({ ...draft, storeId: "601" }, 602, true), { ...draft, storeId: "601" });
  assert.deepEqual(syncOd0002DraftFromGlobalStore({ ...draft, storeId: "601" }, null, false), draft);
});

test("store options normalize the permission summary and only supplement from scoped report rows", () => {
  assert.deepEqual(
    normalizeOd0002StoreOptions(
      [{ store_id: 1, store_code: "601", store_name: "一店" }],
      [
        { store_code: "601", store_name: "一店重复" },
        { store_code: "602", store_name: "二店" },
      ],
    ),
    [
      { value: "601", label: "一店" },
      { value: "602", label: "二店" },
    ],
  );
});

test("object URL cleanup is deferred to allow the browser download to start", () => {
  const calls = [];
  scheduleObjectUrlRevoke("blob:test", (url) => calls.push(["revoke", url]), (fn, delay) => {
    calls.push(["schedule", delay]);
    fn();
    return 1;
  });
  assert.deepEqual(calls, [["schedule", 0], ["revoke", "blob:test"]]);
});

test("OD0002 page source contains the endpoint, controls, states, quality hints, and authenticated export", async () => {
  const source = await readFile(new URL("../pages/sales-reports/od0002-sales-gross-profit.tsx", import.meta.url), "utf8");
  assert.match(source, /OD0002 门店销售毛利汇总表/);
  assert.match(source, /\/api\/sales\/reports\/od0002\?/);
  assert.match(source, /\/api\/sales\/reports\/od0002\/stores/);
  assert.doesNotMatch(source, /\/api\/sales\/summary\/stores/);
  assert.match(source, /import\s*\{[^}]*apiRequest[^}]*\}\s*from\s*["']@\/lib\/api["']/s);
  assert.match(source, /apiRequest\(`\/api\/sales\/reports\/od0002\/export\?/);
  assert.match(source, /OD0002_TABS\.map/);
  assert.match(source, />查询</);
  assert.doesNotMatch(source, />重置</);
  assert.doesNotMatch(source, /RefreshCw/);
  assert.match(source, />统计期间</);
  assert.match(source, />组织范围</);
  assert.match(source, /grid gap-6 lg:grid-cols-2/);
  assert.match(source, /\/api\/sales\/reports\/od0002\/departments/);
  assert.match(source, />全部部门</);
  assert.match(source, /导出/);
  assert.match(source, /无权限查看此报表|无功能权限/);
  assert.match(source, /暂无数据/);
  assert.match(source, /数据质量提示/);
  assert.match(source, /response\.ok/);
  assert.match(source, /scheduleObjectUrlRevoke\(/);
  assert.match(source, /reportQuery\.data\?\.totals\[activeTab\]/);
  assert.match(source, /<TableFooter>/);
  assert.match(source, />合计</);
  assert.match(source, /metricCells\(activeTotal\)/);
});

test("OD0002 table uses Chinese financial yoy colors and compact data rows", async () => {
  const source = await readFile(new URL("../pages/sales-reports/od0002-sales-gross-profit.tsx", import.meta.url), "utf8");

  assert.match(source, /function yoyColorClass\([^)]*\)[\s\S]*value > 0[\s\S]*text-red-600[\s\S]*value < 0[\s\S]*text-green-600/);
  assert.match(source, /isYoy:\s*true/g);
  assert.match(source, /cell\.isYoy\s*\?\s*yoyColorClass\(cell\.rawValue\)/);
  assert.match(source, /<TableCell className="py-2">\s*<HierarchyValue name=\{row\.store_name\}/);
  assert.match(source, /<TableCell className="py-2">\s*<HierarchyValue name=\{row\.dimension_name\}/);
  assert.match(source, /<TableFooter>[\s\S]*py-2/);
});

test("OD0002 page renders the department category hierarchy", async () => {
  const source = await readFile(
    new URL("../pages/sales-reports/od0002-sales-gross-profit.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /activeTab === "department_categories"/);
  for (const label of ["门店", "部门", "区域", "品类", "区域小计", "部门小计"]) {
    assert.match(source, new RegExp(label));
  }
  assert.match(source, /row\.department_name/);
  assert.match(source, /row\.area_name/);
  assert.match(source, /row\.category_name/);
  assert.match(source, /row\.row_type/);
});

test("OD0002 hierarchy values do not wrap and groups render department and group columns", async () => {
  const source = await readFile(
    new URL("../pages/sales-reports/od0002-sales-gross-profit.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /function HierarchyValue[\s\S]*whitespace-nowrap/);
  assert.match(source, /activeTab === "groups"[\s\S]*>部门</);
  assert.match(source, /activeTab === "groups" \? "柜组" : "维度"/);
  assert.match(source, /name=\{row\.department_name\}[\s\S]*code=\{row\.department_code\}/);
  assert.match(source, /name=\{row\.dimension_name\}[\s\S]*code=\{row\.dimension_code\}/);
  assert.match(source, /visible\.includes\("store"\)[\s\S]*HierarchyValue/);
});

test("frontend model accepts the complete backend response contract", async () => {
  await promisify(execFile)("./node_modules/.bin/tsc", [
    "--noEmit", "--strict", "--target", "ES2020", "--module", "ESNext",
    "--moduleResolution", "bundler", "--allowImportingTsExtensions", "--skipLibCheck",
    new URL("./od0002-report.contract.ts", import.meta.url).pathname,
  ]);
});
