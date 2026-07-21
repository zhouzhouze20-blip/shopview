import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  buildSettledGrossProfitParams,
  formatSettledMoney,
  paginateSettledRows,
  settledGrossProfitMessage,
} from "./settled-gross-profit-report.ts";

test("builds bound report parameters and omits all selectors", () => {
  assert.equal(
    buildSettledGrossProfitParams("2026-05-29", "2026-06-28", "603", "6030101").toString(),
    "start_date=2026-05-29&end_date=2026-06-28&store_id=603&department_id=6030101",
  );
  assert.equal(
    buildSettledGrossProfitParams("2026-05-29", "2026-06-28", "all", "all").toString(),
    "start_date=2026-05-29&end_date=2026-06-28",
  );
});

test("formats amounts and paginates detail rows", () => {
  assert.equal(formatSettledMoney(68685.4), "68,685.40");
  assert.equal(formatSettledMoney(null), "—");
  const rows = Array.from({ length: 101 }, (_, index) => index + 1);
  assert.deepEqual(paginateSettledRows(rows, 2), rows.slice(50, 100));
  assert.deepEqual(paginateSettledRows(rows, 99), rows.slice(100));
});

test("distinguishes loading, permission, generic failure, and empty data", () => {
  assert.equal(settledGrossProfitMessage({ isLoading: true }), "正在加载报表…");
  assert.equal(settledGrossProfitMessage({ error: new Error("403 无功能权限") }), "无权限查看此报表");
  assert.equal(settledGrossProfitMessage({ error: new Error("500") }), "报表加载失败，请稍后重试");
  assert.equal(settledGrossProfitMessage({ hasData: true, rowCount: 0 }), "暂无数据");
});

test("page contains the report endpoint, quality warning, totals, and export", async () => {
  const source = await readFile(
    new URL("../pages/sales-reports/settled-gross-profit-ranking.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /结算后销售毛利排行表/);
  assert.match(source, /\/api\/sales\/reports\/settled-gross-profit\?/);
  assert.match(source, /\/api\/sales\/reports\/settled-gross-profit\/export\?/);
  assert.match(source, /数据质量提示/);
  assert.match(source, /未匹配合同/);
  assert.match(source, /含税销售保底成本/);
  assert.match(source, /<TableFooter>/);
  assert.match(source, />合计</);
  assert.match(source, /导出 Excel/);
});
