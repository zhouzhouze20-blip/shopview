import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { navigationItems } from "./navigation-items.ts";
import { filterAccessibleModuleTree } from "./module-permissions.ts";
import {
  buildNonRentalMonthlyRevenueParams,
  financialMonthPeriodLabel,
  formatNonRentalMetric,
} from "./non-rental-monthly-revenue.ts";

function findNode(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findNode(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("builds a fiscal-year query and omits the all-department sentinel", () => {
  assert.equal(
    buildNonRentalMonthlyRevenueParams({
      financialYear: 2026,
      storeId: " 602 ",
      departmentId: "all",
    }).toString(),
    "financial_year=2026&store_id=602",
  );
  assert.equal(
    financialMonthPeriodLabel(2026, 1),
    "2026-01-01 至 2026-01-28",
  );
  assert.equal(
    financialMonthPeriodLabel(2026, 3),
    "2026-03-01 至 2026-03-28",
  );
  assert.equal(
    financialMonthPeriodLabel(2026, 12),
    "2026-11-29 至 2026-12-31",
  );
});

test("formats amounts in ten-thousand yuan and rates as percentages", () => {
  const metrics = {
    tax_included_sales: 123456,
    tax_excluded_sales: 100000,
    gross_profit: 20000,
    fee: 3000,
    contribution: 23000,
    gross_margin: 0.2,
    contract_profit: 18000,
    concession_loss: 2000,
    concession_loss_rate: 0.02,
  };
  assert.equal(formatNonRentalMetric(metrics, "tax_included_sales", "amount"), "12.35");
  assert.equal(formatNonRentalMetric(metrics, "gross_margin", "rate"), "20.00%");
});

test("navigation, permission gate and main dashboard expose the report", async () => {
  const visible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.non_rental_monthly_revenue.view"],
  });
  const item = findNode(visible, "non-rental-monthly-revenue");
  assert.ok(item);
  assert.equal(item.name, "非租赁品牌月度收益表");

  const dashboard = await readFile(
    new URL("../pages/main-dashboard.tsx", import.meta.url),
    "utf8",
  );
  assert.match(dashboard, /NonRentalMonthlyRevenuePage/);
  assert.match(dashboard, /case "non-rental-monthly-revenue"/);
  assert.match(dashboard, /非租赁品牌月度收益表/);
});

test("page states that buy amount is excluded and special sale is separate", async () => {
  const page = await readFile(
    new URL("../pages/sales-reports/non-rental-monthly-revenue.tsx", import.meta.url),
    "utf8",
  );
  assert.match(page, /第一版不含买单额/);
  assert.match(page, /非租赁品牌月度收益表/);
  assert.match(page, /特卖（单独）/);
  assert.match(page, /特卖单独按品牌展示/);
  assert.match(page, /key: "brand_name", label: "品牌"/);
  assert.match(page, /财务年为1月1日至12月31日/);
  assert.match(page, /12月财务月为11月29日至12月31日/);
  assert.match(page, /贡献值＝毛利额＋收费/);
});
