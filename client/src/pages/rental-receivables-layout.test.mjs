import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const pagesDir = dirname(fileURLToPath(import.meta.url));
const pageSource = readFileSync(join(pagesDir, "rental-receivables.tsx"), "utf8");
const hookSource = readFileSync(join(pagesDir, "../hooks/useRentalReceivables.ts"), "utf8");

test("desktop receivables places the amount after settlement period and keeps settlement number last", () => {
  const tableStart = pageSource.indexOf('<Table className="min-w-[1540px] table-fixed');
  const tableEnd = pageSource.indexOf("</Table>", tableStart);
  const tableSource = pageSource.slice(tableStart, tableEnd);
  const headerEnd = tableSource.indexOf("</TableHeader>");
  const headers = Array.from(tableSource.slice(0, headerEnd).matchAll(/<TableHead[^>]*>([^<]+)<\/TableHead>/g), (match) => match[1]);

  assert.ok(tableStart >= 0);
  assert.equal(headers.indexOf("应收未收"), headers.indexOf("结算期间") + 1);
  assert.equal(headers.indexOf("原结算额"), headers.indexOf("应收未收") + 1);
  assert.equal(headers.at(-1), "结算单号");
});

test("desktop receivable entity cells stay compact at two visible lines", () => {
  assert.match(pageSource, /px-3 py-2\.5/);
  assert.match(pageSource, /truncate font-medium/);
  assert.match(pageSource, /truncate text-xs text-muted-foreground/);
});

test("desktop receivables shows supplier actual receivable after sales refunds", () => {
  const metricStart = pageSource.indexOf('<div className="grid gap-4 sm:grid-cols-2');
  const metricEnd = pageSource.indexOf("</div>", metricStart);
  const metricSource = pageSource.slice(metricStart, metricEnd);

  assert.ok(metricStart >= 0);
  assert.match(metricSource, /xl:grid-cols-5/);
  assert.ok(metricSource.indexOf('title="供应商实际应收金额"') > metricSource.indexOf('title="销售返款（不计应收）"'));
  assert.match(metricSource, /supplierActualReceivableAmount\(summary\?\.receivable_amount, summary\?\.sales_refund_amount\)/);
});

test("desktop receivables exports permission-scoped expense details beside search", () => {
  assert.match(pageSource, /导出费用明细/);
  assert.match(pageSource, /downloadRentalReceivableExpenseDetails\(submitted\)/);
  assert.match(hookSource, /\/api\/rental-receivables\/export\/expense-details/);
  assert.match(hookSource, /department_code/);
  assert.match(hookSource, /group_prefix/);
  assert.match(hookSource, /keyword/);
});
