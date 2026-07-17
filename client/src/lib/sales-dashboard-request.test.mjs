import assert from "node:assert/strict";
import test from "node:test";

import {
  SalesDashboardTimeoutError,
  getSalesDashboardData,
  isSalesDashboardTimeoutError,
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
