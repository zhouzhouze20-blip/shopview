import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { navigationItems } from "./navigation-items.ts";

function findItem(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findItem(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("groups revenue map and dashboard under revenue management", () => {
  const revenueManagement = findItem(navigationItems, "revenue-management");

  assert.ok(revenueManagement);
  assert.equal(revenueManagement.name, "收益管理");
  assert.deepEqual(
    (revenueManagement.subItems ?? []).map((item) => item.id),
    ["revenue-map", "revenue-dashboard"],
  );
});

test("wires the revenue dashboard page and permission", async () => {
  const [permissions, dashboard, roleTree] = await Promise.all([
    readFile(new URL("./module-permissions.ts", import.meta.url), "utf8"),
    readFile(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("./role-permission-tree.ts", import.meta.url), "utf8"),
  ]);

  assert.match(permissions, /["']revenue-dashboard["']:\s*\[["']revenue\.dashboard\.view["']\]/);
  assert.match(roleTree, /id:\s*["']revenue-dashboard["'][\s\S]*permissionCodes:\s*\[["']revenue\.dashboard\.view["']\]/);
  assert.match(dashboard, /import\s+RevenueDashboardPage\s+from\s+["']\.\/revenue-dashboard["']/);
  assert.match(dashboard, /case\s+["']revenue-dashboard["']:[\s\S]*<RevenueDashboardPage\s*\/>/);
});

test("revenue dashboard drills from stores to departments to groups", async () => {
  const page = await readFile(new URL("../pages/revenue-dashboard.tsx", import.meta.url), "utf8");

  assert.match(page, /type DrillLevel = ["']stores["'] \| ["']departments["'] \| ["']groups["']/);
  assert.match(page, /const drillToStore = \(row: SummaryRow\)/);
  assert.match(page, /setLevel\(["']departments["']\)/);
  assert.match(page, /const drillToDepartment = \(row: SummaryRow\)/);
  assert.match(page, /setLevel\(["']groups["']\)/);
  assert.match(page, /点击任意一行继续向下钻取/);
  assert.doesNotMatch(page, /<Select/);
});

test("cabinet profit and fee amounts open their matching detail sheets", async () => {
  const page = await readFile(new URL("../pages/revenue-dashboard.tsx", import.meta.url), "utf8");

  assert.match(page, /openDetail\(row,\s*["']gross-profit["']\)/);
  assert.match(page, /openDetail\(row,\s*["']fees["']\)/);
  assert.match(page, /每日毛利明细/);
  assert.match(page, /付款单号/);
  assert.match(page, /结算单号/);
  assert.match(page, /费用项目/);
  assert.match(page, /柜位表费用收益/);
  assert.match(page, /费用明细合计/);
});
