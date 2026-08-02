import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { navigationItems } from "./navigation-items.ts";
import { filterAccessibleModuleTree } from "./module-permissions.ts";
import { buildOd0005Params, formatOd0005Number } from "./od0005-micro-mall.ts";

function findNode(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findNode(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("builds the date, store and optional department query", () => {
  assert.equal(buildOd0005Params({
    startDate: "2026-08-01",
    endDate: "2026-08-01",
    storeId: "601",
    departmentId: "__all__",
  }).toString(), "start_date=2026-08-01&end_date=2026-08-01&store_id=601");
  assert.equal(formatOd0005Number(0.1234, "rate"), "12.34%");
});

test("navigation and dashboard expose OD0005 in all three store folders", async () => {
  const visible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.od0005.view"],
  });
  assert.equal(findNode(visible, "od0005-micro-mall-brand-sales").name, "OD0005 微商城品牌销售统计");
  assert.ok(findNode(visible, "new-century-reports"));
  assert.ok(findNode(visible, "center-reports"));
  assert.ok(findNode(visible, "building-reports"));

  const dashboard = await readFile(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8");
  assert.match(dashboard, /Od0005MicroMallBrandSalesPage/);
  assert.match(dashboard, /case "od0005-micro-mall-brand-sales"/);
});

test("page keeps the supplied source fields visible", async () => {
  const page = await readFile(new URL("../pages/sales-reports/od0005-micro-mall-brand-sales.tsx", import.meta.url), "utf8");
  assert.match(page, /销售收入\+总折扣\(A\)/);
  assert.match(page, /YZQ/);
  assert.match(page, /NZD/);
  assert.match(page, /导出 Excel/);
});
