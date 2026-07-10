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

test("OD0002 exposes the six approved tabs in order", () => {
  assert.deepEqual(
    OD0002_TABS.map((tab) => tab.label),
    ["分店", "部门", "区域", "品类", "柜组", "楼层"],
  );
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
  assert.match(source, />重置</);
  assert.match(source, /导出/);
  assert.match(source, /无权限查看此报表|无功能权限/);
  assert.match(source, /暂无数据/);
  assert.match(source, /数据质量提示/);
  assert.match(source, /response\.ok/);
  assert.match(source, /scheduleObjectUrlRevoke\(/);
});

test("frontend model accepts the complete backend response contract", async () => {
  await promisify(execFile)("./node_modules/.bin/tsc", [
    "--noEmit", "--strict", "--target", "ES2020", "--module", "ESNext",
    "--moduleResolution", "bundler", "--allowImportingTsExtensions", "--skipLibCheck",
    new URL("./od0002-report.contract.ts", import.meta.url).pathname,
  ]);
});
