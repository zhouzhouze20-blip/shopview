import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const markerSource = readFileSync(
  new URL("../components/mobile-special-sale-marker.tsx", import.meta.url),
  "utf8",
);
const unitSource = readFileSync(new URL("../lib/mobile-special-sale.ts", import.meta.url), "utf8");
const revenueMapSource = readFileSync(new URL("./revenue-map.tsx", import.meta.url), "utf8");
const contractsSource = readFileSync(new URL("./contracts.tsx", import.meta.url), "utf8");

test("mobile special sale uses a dedicated logical unit code", () => {
  assert.match(unitSource, /MOBILE_SPECIAL_SALE_UNIT_CODE = "流动特卖"/);
  assert.match(markerSource, /逻辑柜位 · 不占固定铺位/);
});

test("logical mobile special sale is visible on revenue and contract maps", () => {
  assert.match(revenueMapSource, /<MobileSpecialSaleMarker/);
  assert.match(revenueMapSource, /selectMapUnit\(mobileSpecialSaleUnit\.id\)/);
  assert.match(contractsSource, /<MobileSpecialSaleMarker/);
  assert.match(contractsSource, /selectLogicalUnit\(mobileSpecialSaleUnit\.id\)/);
});
