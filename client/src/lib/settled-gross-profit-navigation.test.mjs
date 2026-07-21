import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
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

test("shows settlement gross profit under sales reports with OD0002 access", async () => {
  const visible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.od0002.view"],
  });
  const item = findNode(visible, "settled-gross-profit-ranking");
  const dashboard = await readFile(
    new URL("../pages/main-dashboard.tsx", import.meta.url),
    "utf8",
  );

  assert.ok(item);
  assert.equal(item.name, "结算后销售毛利排行表");
  assert.match(dashboard, /SettledGrossProfitRankingPage/);
  assert.match(dashboard, /case "settled-gross-profit-ranking"/);
});
