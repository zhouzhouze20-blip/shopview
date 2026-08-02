import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const cardSource = readFileSync(
  new URL("../components/multi-business-unit-card.tsx", import.meta.url),
  "utf8",
);
const unitSource = readFileSync(new URL("../lib/multi-business-unit.ts", import.meta.url), "utf8");
const revenueMapSource = readFileSync(new URL("./revenue-map.tsx", import.meta.url), "utf8");
const contractsSource = readFileSync(new URL("./contracts.tsx", import.meta.url), "utf8");

test("multi-business uses one dedicated store-level logical unit", () => {
  assert.match(unitSource, /MULTI_BUSINESS_UNIT_CODE = "多经"/);
  assert.match(cardSource, /店级逻辑柜位 · 不归属实体楼层/);
  assert.match(cardSource, /可绑定本门店多经合同/);
});

test("multi-business logical unit is visible and selectable on both maps", () => {
  assert.match(revenueMapSource, /<MultiBusinessUnitCard/);
  assert.match(revenueMapSource, /selectMapUnit\(multiBusinessUnit\.id\)/);
  assert.match(contractsSource, /<MultiBusinessUnitCard/);
  assert.match(contractsSource, /selectLogicalUnit\(multiBusinessUnit\.id\)/);
});

test("multi-business remains outside physical cabinet counts", () => {
  assert.match(revenueMapSource, /storeLogicalFloorIds\.has\(unit\.floor_id\)/);
  assert.match(contractsSource, /storeLogicalFloorIds\.has\(unit\.floor_id\)/);
  assert.match(revenueMapSource, /geoRows\.length \+ \(mobileSpecialSaleUnit \? 1 : 0\)/);
  assert.doesNotMatch(revenueMapSource, /geoRows\.length \+ \(multiBusinessUnit/);
  assert.match(contractsSource, /geoRows\.length \+ \(mobileSpecialSaleUnit \? 1 : 0\)/);
  assert.doesNotMatch(contractsSource, /geoRows\.length \+ \(multiBusinessUnit/);
});
