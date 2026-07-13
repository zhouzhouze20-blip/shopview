import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import test from "node:test";
import { promisify } from "node:util";

import {
  HDYY01_ALL_DEPARTMENTS,
  HDYY01_ALL_STORES,
  buildHdyy01Params,
  changeHdyy01Store,
  contentDispositionFilename,
  formatHdyy01Area,
  formatHdyy01CodeName,
  formatHdyy01Count,
  formatHdyy01Money,
  formatHdyy01Quantity,
  getHdyy01QueryMessage,
  normalizeHdyy01StoreOptions,
  paginateRows,
  scheduleObjectUrlRevoke,
  syncHdyy01DraftFromGlobalStore,
} from "./hdyy01-report.ts";

test("buildHdyy01Params keeps required dates and omits all or blank filters", () => {
  assert.equal(HDYY01_ALL_STORES, "all");
  assert.equal(HDYY01_ALL_DEPARTMENTS, "all");
  assert.equal(
    buildHdyy01Params("2026-07-01", "2026-07-12", "all").toString(),
    "start_date=2026-07-01&end_date=2026-07-12",
  );
  assert.equal(
    buildHdyy01Params("2026-07-01", "2026-07-12", "   ", " all ").toString(),
    "start_date=2026-07-01&end_date=2026-07-12",
  );
});

test("buildHdyy01Params trims selected store and department values", () => {
  assert.equal(
    buildHdyy01Params("2026-07-01", "2026-07-12", " 603 ", " 6030117 ").toString(),
    "start_date=2026-07-01&end_date=2026-07-12&store_id=603&department_id=6030117",
  );
});

test("changeHdyy01Store resets the department filter", () => {
  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "603",
    departmentId: "6030117",
  };
  assert.deepEqual(changeHdyy01Store(draft, " 602 "), {
    ...draft,
    storeId: " 602 ",
    departmentId: "all",
  });
});

test("HDYY01 money formatter uses yuan with exactly two decimals", () => {
  assert.equal(formatHdyy01Money(123456.789), "123,456.79");
  assert.equal(formatHdyy01Money(-1234.5), "-1,234.50");
  assert.equal(formatHdyy01Money(null), "—");
  assert.equal(formatHdyy01Money(undefined), "—");
});

test("HDYY01 area formatter uses exactly two decimals", () => {
  assert.equal(formatHdyy01Area(1234.567), "1,234.57");
  assert.equal(formatHdyy01Area(-2), "-2.00");
  assert.equal(formatHdyy01Area(null), "—");
});

test("HDYY01 quantity formatter keeps up to four decimals", () => {
  assert.equal(formatHdyy01Quantity(1234.56789), "1,234.5679");
  assert.equal(formatHdyy01Quantity(-2.5), "-2.5");
  assert.equal(formatHdyy01Quantity(2), "2");
  assert.equal(formatHdyy01Quantity(null), "—");
});

test("HDYY01 count formatter renders an integer", () => {
  assert.equal(formatHdyy01Count(1234.6), "1,235");
  assert.equal(formatHdyy01Count(-2.4), "-2");
  assert.equal(formatHdyy01Count(null), "—");
});

test("code and name formatter falls back without hiding known values", () => {
  assert.equal(formatHdyy01CodeName("6030117", "  女装部  "), "女装部（6030117）");
  assert.equal(formatHdyy01CodeName("6030117", null), "6030117");
  assert.equal(formatHdyy01CodeName(null, "女装部"), "女装部");
  assert.equal(formatHdyy01CodeName(" ", " "), "—");
});

test("paginateRows returns fifty-row pages and clamps page bounds", () => {
  const rows = Array.from({ length: 121 }, (_, index) => index + 1);
  assert.deepEqual(paginateRows(rows, 2), rows.slice(50, 100));
  assert.deepEqual(paginateRows(rows, 99), rows.slice(100));
  assert.deepEqual(paginateRows(rows, 0), rows.slice(0, 50));
  assert.deepEqual(paginateRows(rows, Number.NaN), rows.slice(0, 50));
});

test("getHdyy01QueryMessage distinguishes loading, permission, failure, and empty states", () => {
  assert.equal(getHdyy01QueryMessage({ isLoading: true }), "正在加载报表…");
  assert.equal(
    getHdyy01QueryMessage({ error: new Error("API请求失败: 403 - 无功能权限") }),
    "无权限查看此报表",
  );
  assert.equal(
    getHdyy01QueryMessage({ error: new Error("API请求失败: 403 - 无该门店数据权限") }),
    "无权限查看此报表",
  );
  assert.equal(
    getHdyy01QueryMessage({ error: new Error("API请求失败: 500") }),
    "报表加载失败，请稍后重试",
  );
  assert.equal(getHdyy01QueryMessage({ hasData: true, rowCount: 0 }), "当前条件下无数据");
  assert.equal(getHdyy01QueryMessage({ hasData: true, rowCount: 1 }), null);
  assert.equal(getHdyy01QueryMessage({}), null);
});

test("contentDispositionFilename parses UTF-8 and quoted names and strips paths", () => {
  assert.equal(
    contentDispositionFilename("attachment; filename*=UTF-8''reports%2FHDYY01_%E6%9F%9C%E7%BB%84.xlsx"),
    "HDYY01_柜组.xlsx",
  );
  assert.equal(
    contentDispositionFilename('attachment; filename="..\\exports\\HDYY01 report.xlsx"'),
    "HDYY01 report.xlsx",
  );
  assert.equal(contentDispositionFilename(null), null);
});

test("contentDispositionFilename rejects malformed UTF-8 encoding", () => {
  assert.equal(
    contentDispositionFilename("attachment; filename*=UTF-8''HDYY01_%E0%A4%A.xlsx"),
    null,
  );
});

test("scheduleObjectUrlRevoke defers cleanup", () => {
  const calls = [];
  scheduleObjectUrlRevoke("blob:hdyy01", (url) => calls.push(["revoke", url]), (callback, delay) => {
    calls.push(["schedule", delay]);
    callback();
    return 1;
  });
  assert.deepEqual(calls, [["schedule", 0], ["revoke", "blob:hdyy01"]]);
});

test("global store sync handles cold start and changes while preserving dirty drafts", () => {
  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "all",
    departmentId: "all",
  };
  assert.deepEqual(syncHdyy01DraftFromGlobalStore(draft, 603, false), {
    ...draft,
    storeId: "603",
  });
  assert.deepEqual(syncHdyy01DraftFromGlobalStore({ ...draft, storeId: "603" }, 602, false), {
    ...draft,
    storeId: "602",
  });
  assert.deepEqual(syncHdyy01DraftFromGlobalStore({ ...draft, storeId: "603" }, 602, true), {
    ...draft,
    storeId: "603",
  });
  assert.deepEqual(syncHdyy01DraftFromGlobalStore({ ...draft, storeId: "603" }, null, false), draft);
});

test("store options trim, dedupe, and use the authorized label fallback", () => {
  assert.deepEqual(
    normalizeHdyy01StoreOptions([
      { store_id: 1, store_code: " 603 ", store_name: " 三店 " },
      { store_id: 2, store_code: "603", store_name: "三店（最新）" },
      { store_id: 3, store_code: " 602 ", store_name: "  " },
      { store_id: 4, store_code: "   ", store_name: "忽略" },
    ]),
    [
      { value: "603", label: "三店（最新）" },
      { value: "602", label: "602" },
    ],
  );
});

test("frontend model accepts the complete backend response and rejects wrong quality keys", async () => {
  await promisify(execFile)("./node_modules/.bin/tsc", [
    "--noEmit", "--strict", "--target", "ES2020", "--module", "ESNext",
    "--moduleResolution", "bundler", "--allowImportingTsExtensions", "--skipLibCheck",
    new URL("./hdyy01-report.contract.ts", import.meta.url).pathname,
  ]);
});
