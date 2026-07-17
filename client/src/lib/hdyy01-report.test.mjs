import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { promisify } from "node:util";
import { QueryClient } from "@tanstack/query-core";

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
  assert.equal(formatHdyy01Money(Number.NaN), "—");
  assert.equal(formatHdyy01Money(-0), "0.00");
});

test("HDYY01 area formatter uses exactly two decimals", () => {
  assert.equal(formatHdyy01Area(1234.567), "1,234.57");
  assert.equal(formatHdyy01Area(-2), "-2.00");
  assert.equal(formatHdyy01Area(null), "—");
  assert.equal(formatHdyy01Area(Number.POSITIVE_INFINITY), "—");
  assert.equal(formatHdyy01Area(-0), "0.00");
});

test("HDYY01 quantity formatter keeps up to four decimals", () => {
  assert.equal(formatHdyy01Quantity(1234.56789), "1,234.5679");
  assert.equal(formatHdyy01Quantity(-2.5), "-2.5");
  assert.equal(formatHdyy01Quantity(2), "2");
  assert.equal(formatHdyy01Quantity(null), "—");
  assert.equal(formatHdyy01Quantity(Number.NEGATIVE_INFINITY), "—");
  assert.equal(formatHdyy01Quantity(-0), "0");
});

test("HDYY01 count formatter renders an integer", () => {
  assert.equal(formatHdyy01Count(1234.6), "1,235");
  assert.equal(formatHdyy01Count(-2.4), "-2");
  assert.equal(formatHdyy01Count(null), "—");
  assert.equal(formatHdyy01Count(Number.NaN), "—");
  assert.equal(formatHdyy01Count(-0), "0");
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

test("paginateRows falls back to fifty for invalid page sizes", () => {
  const rows = Array.from({ length: 121 }, (_, index) => index + 1);
  for (const pageSize of [0, -10, Number.NaN, Number.POSITIVE_INFINITY, 12.5]) {
    assert.deepEqual(paginateRows(rows, 2, pageSize), rows.slice(50, 100));
  }
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
    getHdyy01QueryMessage({ error: new Error("HTTP 403 Forbidden") }),
    "无权限查看此报表",
  );
  assert.equal(
    getHdyy01QueryMessage({ error: new Error("无功能权限") }),
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

test("getHdyy01QueryMessage does not treat unrelated 403 text as a permission status", () => {
  for (const message of [
    "API请求失败: 500 - body record 403 unavailable",
    "record 403 is archived",
    "用户无权限状态统计失败",
  ]) {
    assert.equal(
      getHdyy01QueryMessage({ error: new Error(message) }),
      "报表加载失败，请稍后重试",
    );
  }
});

test("contentDispositionFilename parses UTF-8 and quoted names and strips paths", () => {
  assert.equal(
    contentDispositionFilename("attachment; filename*=UTF-8''reports%2FHDYY01_%E6%9F%9C%E7%BB%84.xlsx"),
    "HDYY01_柜组.xlsx",
  );
  assert.equal(
    contentDispositionFilename("attachment; filename*=UTF-8'zh-CN'HDYY01_%E7%BB%8F%E8%90%A5.xlsx"),
    "HDYY01_经营.xlsx",
  );
  assert.equal(
    contentDispositionFilename('attachment; filename="..\\exports\\HDYY01 report.xlsx"'),
    "HDYY01 report.xlsx",
  );
  assert.equal(contentDispositionFilename(null), null);
});

test("contentDispositionFilename falls back to a valid plain name after invalid extended values", () => {
  assert.equal(
    contentDispositionFilename(
      "attachment; filename*=UTF-8''HDYY01_%E0%A4%A.xlsx; filename=HDYY01_fallback.xlsx",
    ),
    "HDYY01_fallback.xlsx",
  );
  assert.equal(
    contentDispositionFilename(
      "attachment; filename*=UTF-8''unsafe%0Aname.xlsx; filename=HDYY01_safe.xlsx",
    ),
    "HDYY01_safe.xlsx",
  );
  assert.equal(
    contentDispositionFilename("attachment; filename*=UTF-8''HDYY01_%E0%A4%A.xlsx"),
    null,
  );
});

test("contentDispositionFilename rejects unsafe or meaningless names", () => {
  for (const header of [
    'attachment; filename="."',
    'attachment; filename=".."',
    'attachment; filename="bad\u0000name.xlsx"',
    'attachment; filename="bad\nname.xlsx"',
    'attachment; filename="bad\u007fname.xlsx"',
    'attachment; filename="   "',
  ]) {
    assert.equal(contentDispositionFilename(header), null);
  }
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

test("global store sync resets department on cold start", () => {
  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "all",
    departmentId: "6030117",
  };
  assert.deepEqual(syncHdyy01DraftFromGlobalStore(draft, "603", false), {
    ...draft,
    storeId: "603",
    departmentId: "all",
  });
});

test("global store sync resets department on a later store change", () => {
  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "603",
    departmentId: "6030117",
  };
  assert.deepEqual(syncHdyy01DraftFromGlobalStore(draft, "602", false), {
    ...draft,
    storeId: "602",
    departmentId: "all",
  });
});

test("global store sync resets department when the global store becomes all", () => {
  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "603",
    departmentId: "6030117",
  };
  assert.deepEqual(syncHdyy01DraftFromGlobalStore(draft, null, false), {
    ...draft,
    storeId: "all",
    departmentId: "all",
  });
});

test("global store sync preserves the draft when the store is unchanged", () => {
  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "603",
    departmentId: "6030117",
  };
  assert.strictEqual(syncHdyy01DraftFromGlobalStore(draft, "603", false), draft);
});

test("global store sync preserves a dirty draft", () => {
  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "603",
    departmentId: "6030117",
  };
  assert.strictEqual(syncHdyy01DraftFromGlobalStore(draft, "602", true), draft);
});

test("global store sync receives the ERP code mapped from the authorized internal store id", () => {
  const authorizedStores = [
    { store_id: 4, store_code: "604", store_name: "四店" },
  ];
  const selectedStoreId = 4;
  const globalStoreCode = authorizedStores.find(
    (store) => String(store.store_id) === String(selectedStoreId),
  )?.store_code ?? null;
  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "all",
    departmentId: "6030117",
  };

  assert.equal(globalStoreCode, "604");
  assert.deepEqual(syncHdyy01DraftFromGlobalStore(draft, globalStoreCode, false), {
    ...draft,
    storeId: "604",
    departmentId: "all",
  });
});

test("store options trim, dedupe, and use the authorized label fallback", () => {
  assert.deepEqual(
    normalizeHdyy01StoreOptions([
      { store_id: 1, store_code: " 603 ", store_name: " 三店 " },
      { store_id: 2, store_code: "603", store_name: "三店（最新）" },
      { store_id: 3, store_code: "603", store_name: "  " },
      { store_id: 4, store_code: " 602 ", store_name: "  " },
      { store_id: 5, store_code: "   ", store_name: "忽略" },
    ]),
    [
      { value: "603", label: "三店（最新）" },
      { value: "602", label: "602" },
    ],
  );
});

test("default HDYY01 dates use the full month containing yesterday in local time", async () => {
  const module = await import("./hdyy01-report.ts");
  assert.equal(typeof module.defaultHdyy01DateRange, "function");

  assert.deepEqual(module.defaultHdyy01DateRange(new Date(2026, 7, 1, 12)), {
    start: "2026-07-01",
    end: "2026-07-31",
  });
  assert.deepEqual(module.defaultHdyy01DateRange(new Date(2026, 0, 1, 12)), {
    start: "2025-12-01",
    end: "2025-12-31",
  });
  assert.deepEqual(module.defaultHdyy01DateRange(new Date(2026, 6, 13, 12)), {
    start: "2026-07-01",
    end: "2026-07-12",
  });
});

test("authorized internal store ids resolve to ERP store codes only", async () => {
  const module = await import("./hdyy01-report.ts");
  assert.equal(typeof module.resolveHdyy01GlobalStoreCode, "function");

  const stores = [{ store_id: 4, store_code: " 604 ", store_name: "四店" }];
  assert.equal(module.resolveHdyy01GlobalStoreCode(stores, 4), "604");
  assert.equal(module.resolveHdyy01GlobalStoreCode(stores, "4"), "604");
  assert.equal(module.resolveHdyy01GlobalStoreCode(stores, 999), null);
  assert.equal(module.resolveHdyy01GlobalStoreCode(stores, null), null);
});

test("submitted query snapshot is isolated from later draft edits", async () => {
  const module = await import("./hdyy01-report.ts");
  assert.equal(typeof module.createHdyy01QuerySnapshot, "function");

  const draft = {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "604",
    departmentId: "60401",
  };
  const snapshot = module.createHdyy01QuerySnapshot(draft);
  draft.start = "2026-06-01";
  draft.end = "2026-06-30";
  draft.storeId = "603";
  draft.departmentId = "all";

  assert.deepEqual(snapshot.filters, {
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "604",
    departmentId: "60401",
  });
  assert.equal(
    snapshot.queryString,
    "start_date=2026-07-01&end_date=2026-07-12&store_id=604&department_id=60401",
  );
});

test("same submitted query explicitly refreshes while a changed query uses a new key", async () => {
  const module = await import("./hdyy01-report.ts");
  assert.equal(typeof module.shouldRefetchHdyy01Query, "function");

  const current = module.createHdyy01QuerySnapshot({
    start: "2026-07-01",
    end: "2026-07-12",
    storeId: "604",
    departmentId: "all",
  });
  const same = module.createHdyy01QuerySnapshot({ ...current.filters });
  const changed = module.createHdyy01QuerySnapshot({ ...current.filters, storeId: "603" });

  assert.equal(module.shouldRefetchHdyy01Query(null, current), false);
  assert.equal(module.shouldRefetchHdyy01Query(current, same), true);
  assert.equal(module.shouldRefetchHdyy01Query(current, changed), false);
  assert.notEqual(current.queryString, changed.queryString);
});

test("HDYY01 refetches an A-B-A filter sequence despite the global infinite stale time", async () => {
  const module = await import("./hdyy01-report.ts");
  assert.equal(module.HDYY01_REPORT_STALE_TIME, 0);

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { staleTime: Infinity, retry: false },
    },
  });
  const networkCalls = [];
  const fetchReport = (queryString) => queryClient.fetchQuery({
    queryKey: ["/api/sales/reports/hdyy01", queryString],
    queryFn: async () => {
      networkCalls.push(queryString);
      return { queryString };
    },
    staleTime: module.HDYY01_REPORT_STALE_TIME,
  });
  const filterA = "start_date=2026-07-01&end_date=2026-07-12&store_id=604";
  const filterB = "start_date=2026-07-01&end_date=2026-07-12&store_id=603";

  await fetchReport(filterA);
  await fetchReport(filterB);
  await fetchReport(filterA);

  assert.deepEqual(networkCalls, [filterA, filterB, filterA]);
});

test("HDYY01 page source exposes only the four approved filters and report endpoints", async () => {
  const source = await readFile(
    new URL("../pages/sales-reports/hdyy01-group-operation-analysis.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /HDYY01柜组经营分析表/);
  for (const label of ["开始日期", "结束日期", "门店", "部门"]) {
    assert.match(source, new RegExp(`>${label}<`));
  }
  for (const endpoint of [
    "/api/sales/reports/hdyy01/stores",
    "/api/sales/reports/hdyy01/departments",
    "/api/sales/reports/hdyy01?",
    "/api/sales/reports/hdyy01/export?",
  ]) {
    assert.match(source, new RegExp(endpoint.replace(/[?]/g, "\\?")));
  }
  assert.doesNotMatch(source, /prior|yoy|同期|同比/i);
  assert.match(source, /defaultHdyy01DateRange\(\)/);
});

test("HDYY01 page source maps StoreContext ids through the tested ERP-code helper", async () => {
  const source = await readFile(
    new URL("../pages/sales-reports/hdyy01-group-operation-analysis.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /resolveHdyy01GlobalStoreCode\(storesQuery\.data\s*\?\?\s*\[\],\s*selectedStoreId\)/);
  assert.match(source, /syncHdyy01DraftFromGlobalStore\(current,\s*globalStoreCode,\s*draftDirty\)/);
  assert.doesNotMatch(source, /syncHdyy01DraftFromGlobalStore\(current,\s*selectedStoreId/);
  assert.doesNotMatch(source, /storesQuery\.data\?\.find/);
});

test("HDYY01 page source fixes pagination, authenticated export, columns, and quality labels", async () => {
  const source = await readFile(
    new URL("../pages/sales-reports/hdyy01-group-operation-analysis.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /const PAGE_SIZE = 50/);
  assert.match(source, /paginateRows\([^,]+,\s*page,\s*PAGE_SIZE\)/);
  assert.match(source, /useEffect\(\(\)\s*=>\s*\{\s*setPage\(1\);\s*\},\s*\[draft\.storeId\]\)/s);
  assert.match(source, /import\s*\{[^}]*apiRequest[^}]*\}\s*from\s*["']@\/lib\/api["']/s);
  assert.match(source, /apiRequest\(`\/api\/sales\/reports\/hdyy01\/export\?\$\{submitted\.queryString\}`\)/);
  assert.match(source, /contentDispositionFilename\(/);
  assert.match(source, /scheduleObjectUrlRevoke\(/);
  assert.match(source, /<TableHeader className="sticky/);
  assert.match(source, /overflow-x-auto/);
  assert.match(source, /<TableFooter>/);
  assert.match(source, />合计</);

  const columnLabels = [
    "机构", "部门", "柜组编码", "柜组名称", "面积", "楼层", "数量", "销售收入",
    "含税销售成本", "毛利", "消费次数", "客单", "会员销售", "储值卡销售",
  ];
  for (const label of columnLabels) {
    assert.match(source, new RegExp(`label:\\s*["']${label}["']`));
  }
  assert.equal((source.match(/label:\s*["'][^"']+["']/g) ?? []).filter((entry) =>
    columnLabels.some((label) => entry.includes(`"${label}"`) || entry.includes(`'${label}'`))
  ).length, 14);

  for (const removedLabel of ["一级编码", "一级名称", "二级编码", "二级名称", "等级"]) {
    assert.doesNotMatch(source, new RegExp(`label:\\s*["']${removedLabel}["']`));
  }
  assert.match(source, /label:\s*["']楼层["'][^}]*row\.floor_name/);

  for (const [label, field] of [
    ["销售收入", "sales_amount"],
    ["含税销售成本", "tax_cost"],
    ["毛利", "profit"],
    ["客单", "average_ticket"],
    ["会员销售", "member_sales"],
    ["储值卡销售", "stored_card_sales"],
  ]) {
    assert.match(source, new RegExp(`label:\\s*["']${label}["'][^}]*row\\.${field}`));
  }

  for (const label of [
    "未匹配组织柜组数", "未匹配组织金额", "未匹配层级柜组数", "未匹配层级金额",
    "缺失等级柜组数", "缺失等级金额", "未匹配会员小票数",
  ]) {
    assert.match(source, new RegExp(`label:\\s*["']${label}["']`));
  }
  assert.match(
    source,
    /unmatched_member_ticket_count\s*===\s*null\s*\?\s*["']不可计算["']/,
  );
});

test("HDYY01 page source uses stable submitted query keys and explicit same-filter refresh", async () => {
  const source = await readFile(
    new URL("../pages/sales-reports/hdyy01-group-operation-analysis.tsx", import.meta.url),
    "utf8",
  );

  assert.doesNotMatch(source, /queryVersion/);
  assert.match(source, /const \[submitted, setSubmitted\] = useState<.*Hdyy01QuerySnapshot.*>\(null\)/);
  assert.match(source, /queryKey:\s*\["\/api\/sales\/reports\/hdyy01",\s*submittedQueryString\]/);
  assert.match(source, /staleTime:\s*HDYY01_REPORT_STALE_TIME/);
  assert.match(source, /createHdyy01QuerySnapshot\(draft\)/);
  assert.match(source, /shouldRefetchHdyy01Query\(submitted,\s*nextSubmitted\)/);
  assert.match(source, /reportQuery\.refetch\(\)/);
  assert.match(source, /enabled:\s*Boolean\(submitted\)/);
  assert.match(source, /isLoading:\s*hasSubmitted\s*&&\s*reportQuery\.isFetching/);
  assert.match(source, /disabled=\{exporting\s*\|\|\s*reportQuery\.isFetching\s*\|\|\s*!hasSubmitted/);
});

test("frontend model accepts the complete backend response and rejects wrong quality keys", async () => {
  await promisify(execFile)("./node_modules/.bin/tsc", [
    "--noEmit", "--strict", "--target", "ES2020", "--module", "ESNext",
    "--moduleResolution", "bundler", "--allowImportingTsExtensions", "--skipLibCheck",
    new URL("./hdyy01-report.contract.ts", import.meta.url).pathname,
  ]);
});
