import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  SalesDashboardTimeoutError,
  getSalesDashboardData,
  isSalesDashboardTimeoutError,
  salesDashboardRangeDays,
  validateSalesDashboardDateRanges,
} from "./sales-dashboard-request.ts";

test("sales dashboard aborts a stalled request and reports a timeout", async () => {
  const request = (_endpoint, options) =>
    new Promise((_resolve, reject) => {
      options.signal.addEventListener("abort", () => {
        const error = new Error("aborted");
        error.name = "AbortError";
        reject(error);
      });
    });

  await assert.rejects(
    getSalesDashboardData("/api/sales/summary/stores", request, { timeoutMs: 5 }),
    SalesDashboardTimeoutError,
  );
});

test("sales dashboard recognizes a gateway timeout response", async () => {
  const request = async () => {
    throw new Error("API请求失败: 504 - Gateway Time-out");
  };

  await assert.rejects(
    getSalesDashboardData("/api/sales/summary/stores", request, { timeoutMs: 100 }),
    SalesDashboardTimeoutError,
  );
});

test("sales dashboard preserves successful data and non-timeout errors", async () => {
  const rows = [{ store_id: "1" }];
  assert.deepEqual(
    await getSalesDashboardData("/api/sales/summary/stores", async () => rows, { timeoutMs: 100 }),
    rows,
  );

  const permissionError = new Error("API请求失败: 403 - 无功能权限");
  await assert.rejects(
    getSalesDashboardData(
      "/api/sales/summary/stores",
      async () => {
        throw permissionError;
      },
      { timeoutMs: 100 },
    ),
    permissionError,
  );
  assert.equal(isSalesDashboardTimeoutError(permissionError), false);
});

test("sales dashboard validates all four dates before running an expensive query", () => {
  const valid = {
    currentStartDate: "2026-07-01",
    currentEndDate: "2026-07-18",
    priorStartDate: "2025-07-01",
    priorEndDate: "2025-07-18",
  };

  assert.equal(validateSalesDashboardDateRanges(valid), null);
  assert.equal(
    validateSalesDashboardDateRanges({ ...valid, currentStartDate: "" }),
    "请完整选择本期和同期日期。",
  );
  assert.equal(
    validateSalesDashboardDateRanges({ ...valid, currentStartDate: "2026-07-19" }),
    "本期开始日期不能晚于结束日期。",
  );
  assert.equal(
    validateSalesDashboardDateRanges({ ...valid, priorStartDate: "2025-07-19" }),
    "同期开始日期不能晚于结束日期。",
  );
  assert.equal(salesDashboardRangeDays("2025-08-19", "2026-07-18"), 334);
});

test("sales dashboard waits for an explicit query and avoids hidden store requests in drilldowns", async () => {
  const source = await readFile(new URL("../pages/sales-dashboard.tsx", import.meta.url), "utf8");

  assert.match(source, /const \[draftCurrentStartDate, setDraftCurrentStartDate\]/);
  assert.match(source, /enabled: activeTab === "stores"/);
  assert.match(source, /onClick=\{applyDateRange\}/);
  assert.match(source, /查询未完成/);
});
