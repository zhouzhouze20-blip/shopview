import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { navigationItems } from "./navigation-items.ts";
import { filterAccessibleModuleTree } from "./module-permissions.ts";
import { buildOd0005Params, formatOd0005Number, OD0005_SHEETS } from "./od0005-micro-mall.ts";

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
  assert.equal(buildOd0005Params({
    startDate: "2026-08-01",
    endDate: "2026-08-02",
    storeId: "603",
    departmentId: "6030101",
    sheet: "daily_yoy",
  }).toString(), "start_date=2026-08-01&end_date=2026-08-02&store_id=603&sheet=daily_yoy&department_id=6030101");
  assert.equal(formatOd0005Number(0.1234, "rate"), "12.34%");
  assert.deepEqual(OD0005_SHEETS.map((sheet) => sheet.label), [
    "微商城品牌销售统计",
    "部门销售统计",
    "逐日销售",
    "逐日同期同比",
    "品牌同比",
  ]);
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
  assert.match(page, /含付款方式 0581/);
  assert.match(page, /report.payment_code/);
  assert.doesNotMatch(page, /收银员|cashier_code/);
  assert.match(page, /销售收入\+总折扣\(A\)/);
  assert.match(page, /YZQ/);
  assert.match(page, /NZD/);
  assert.match(page, /导出 Excel/);
  assert.doesNotMatch(page, /od0005-sheet/);
  assert.doesNotMatch(page, /od0005-department/);
  assert.doesNotMatch(page, /visibleRowCount|countLabel/);
  assert.match(page, /本期销售/);
  assert.match(page, /同期销售/);
  assert.match(page, /同比/);
  assert.match(page, /原因分析/);
  assert.match(page, /缺失商品/);
  assert.match(page, /5个表页/);
  assert.match(page, /Tabs value=\{selectedSheet\}/);
  assert.match(page, /switchSheet\(value as Od0005Sheet\)/);
  assert.match(page, /placeholderData: \(previousData\) => previousData/);
  assert.match(page, /xl:grid-cols-\[minmax\(0,1fr\)_minmax\(0,1fr\)_minmax\(0,1fr\)_auto\]/);
  assert.match(page, /flex items-end gap-3 whitespace-nowrap/);
});
