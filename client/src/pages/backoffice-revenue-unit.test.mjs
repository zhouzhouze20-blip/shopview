import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const cardSource = readFileSync(
  new URL("../components/backoffice-revenue-unit-card.tsx", import.meta.url),
  "utf8",
);
const unitSource = readFileSync(new URL("../lib/backoffice-revenue-unit.ts", import.meta.url), "utf8");
const revenueMapSource = readFileSync(new URL("./revenue-map.tsx", import.meta.url), "utf8");
const contractsSource = readFileSync(new URL("./contracts.tsx", import.meta.url), "utf8");

test("backoffice revenue uses a dedicated store-level logical unit", () => {
  assert.match(unitSource, /BACKOFFICE_REVENUE_UNIT_CODE = "后台部门收益"/);
  assert.match(cardSource, /店级逻辑柜位 · 不归属实体楼层/);
});

test("backoffice revenue unit remains selectable without a base map", () => {
  assert.match(revenueMapSource, /<BackofficeRevenueUnitCard/);
  assert.match(revenueMapSource, /selectMapUnit\(backofficeRevenueUnit\.id\)/);
  assert.match(contractsSource, /<BackofficeRevenueUnitCard/);
  assert.match(contractsSource, /selectLogicalUnit\(backofficeRevenueUnit\.id\)/);
});

test("backoffice revenue and mobile special sale share the map logical-unit dock", () => {
  assert.match(revenueMapSource, /data-testid="logical-revenue-unit-dock"/);
  assert.match(revenueMapSource, /left-4 top-4 z-20 flex w-64 origin-top-left scale-50/);
  assert.match(revenueMapSource, /storeRevenueByUnitId\.get\(backofficeRevenueUnit\.id\)/);
  assert.match(contractsSource, /data-testid="logical-revenue-unit-dock"/);
  assert.match(contractsSource, /left-4 top-4 z-20 flex w-64 origin-top-left scale-50/);
  assert.match(contractsSource, /storeBackofficeUnitsQuery/);
});
