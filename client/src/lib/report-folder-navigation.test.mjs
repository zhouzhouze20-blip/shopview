import assert from "node:assert/strict";
import test from "node:test";

import { navigationItems } from "./navigation-items.ts";
import { filterAccessibleModuleTree } from "./module-permissions.ts";

function findNode(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findNode(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("sales reports are grouped into the three store folders and other", () => {
  const reports = findNode(navigationItems, "sales-reports");

  assert.deepEqual((reports?.subItems ?? []).map((item) => [item.id, item.name]), [
    ["new-century-reports", "新世纪报表"],
    ["center-reports", "中心报表"],
    ["building-reports", "大楼报表"],
    ["other-reports", "其他"],
  ]);
  assert.deepEqual(findNode(navigationItems, "new-century-reports").subItems.map((item) => item.id), [
    "daily-sales-followup",
    "od0002-sales-gross-profit",
    "od0004-monthly-followup",
    "od0005-micro-mall-brand-sales",
    "hdyy01-group-operation-analysis",
  ]);
  assert.deepEqual(findNode(navigationItems, "center-reports").subItems.map((item) => item.id), [
    "daily-sales-followup",
    "od0002-sales-gross-profit",
    "od0003-center-sales-followup",
    "od0004-monthly-followup",
    "od0005-micro-mall-brand-sales",
    "hy0001-key-brand-member",
    "hdyy01-group-operation-analysis",
  ]);
  assert.deepEqual(findNode(navigationItems, "building-reports").subItems.map((item) => item.id), [
    "daily-sales-followup",
    "od0002-sales-gross-profit",
    "od0004-monthly-followup",
    "od0005-micro-mall-brand-sales",
    "hdyy01-group-operation-analysis",
    "non-rental-monthly-revenue",
  ]);
  assert.deepEqual(findNode(navigationItems, "other-reports").subItems.map((item) => item.id), [
    "commodity-sales-detail",
    "settled-gross-profit-ranking",
    "store-other-business-income",
  ]);
});

test("permission filtering keeps only folders containing an accessible report", () => {
  const visible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.od0003.view"],
  });

  assert.equal(findNode(visible, "new-century-reports"), null);
  assert.ok(findNode(visible, "center-reports"));
  assert.equal(findNode(visible, "building-reports"), null);
  assert.equal(findNode(visible, "other-reports"), null);
  assert.ok(findNode(visible, "od0003-center-sales-followup"));
});

test("shared report permissions expose every matching store folder", () => {
  const visible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.od0001.view"],
  });

  assert.ok(findNode(visible, "new-century-reports"));
  assert.ok(findNode(visible, "center-reports"));
  assert.ok(findNode(visible, "building-reports"));
  assert.equal(findNode(visible, "other-reports"), null);
});

test("building-only non-rental and general reports stay in their dedicated folders", () => {
  const nonRentalVisible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.non_rental_monthly_revenue.view"],
  });
  const commodityVisible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.commodity_detail.view"],
  });

  assert.equal(findNode(nonRentalVisible, "non-rental-monthly-revenue").name, "非租赁品牌月度收益表");
  assert.ok(findNode(nonRentalVisible, "building-reports"));
  assert.equal(findNode(nonRentalVisible, "other-reports"), null);
  assert.ok(findNode(commodityVisible, "other-reports"));
  assert.equal(findNode(commodityVisible, "new-century-reports"), null);
});
