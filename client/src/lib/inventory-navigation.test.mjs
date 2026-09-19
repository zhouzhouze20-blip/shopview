import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { filterAccessibleModuleTree } from "./module-permissions.ts";
import { navigationItems } from "./navigation-items.ts";
import { buildRolePermissionTree } from "./role-permission-tree.ts";

function findNode(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findNode(item.subItems ?? item.children ?? [], id);
    if (child) return child;
  }
  return null;
}

test("moves the inventory query into its own top-level inventory menu", () => {
  const inventoryManagement = findNode(navigationItems, "inventory-management");
  const salesReports = findNode(navigationItems, "sales-reports");

  assert.ok(inventoryManagement);
  assert.equal(inventoryManagement.name, "库存管理");
  assert.deepEqual(
    inventoryManagement.subItems.map((item) => item.id),
    ["inventory-detail", "historical-inventory-detail", "inventory-movement-detail", "inventory-turnover"],
  );
  assert.equal(inventoryManagement.subItems[0].name, "实时库存查询");
  assert.equal(inventoryManagement.subItems[1].name, "历史库存明细报表");
  assert.equal(inventoryManagement.subItems[2].name, "进销存明细报表");
  assert.equal(
    salesReports.subItems.some((item) => item.id === "inventory-detail"),
    false,
  );
});

test("shows the inventory movement report only with its own permission", async () => {
  const visible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.inventory_movement.view"],
  });
  const page = await readFile(
    new URL("../pages/sales-reports/inventory-movement-detail.tsx", import.meta.url),
    "utf8",
  );

  assert.ok(findNode(visible, "inventory-management"));
  assert.equal(findNode(visible, "inventory-movement-detail").name, "进销存明细报表");
  assert.equal(findNode(visible, "inventory-detail"), null);
  assert.match(page, />进销存明细报表<\/h1>/);

  const tree = buildRolePermissionTree([
    {
      id: 3,
      permission_code: "sales.inventory_movement.view",
      permission_name: "查看进销存明细报表",
      module_code: "sales",
      action_code: "inventory_movement_view",
    },
  ]);
  assert.deepEqual(
    findNode(tree, "inventory-movement-detail").permissions.map((item) => item.id),
    [3],
  );
});

test("keeps only occurrence dates and the five real-time inventory filters", async () => {
  const page = await readFile(
    new URL("../pages/sales-reports/inventory-movement-detail.tsx", import.meta.url),
    "utf8",
  );

  for (const field of ["supplier", "group", "goods_code", "goods_name", "barcode"]) {
    assert.match(page, new RegExp(`key: ["']${field}["']`));
  }
  assert.match(page, />发生开始日期<\/Label>/);
  assert.match(page, />发生结束日期<\/Label>/);
  assert.doesNotMatch(page, />记账开始日期<\/Label>/);
  assert.doesNotMatch(page, />记账结束日期<\/Label>/);
  assert.doesNotMatch(page, />门店<\/Label>/);
  assert.doesNotMatch(page, />商品规格<\/Label>/);
  assert.doesNotMatch(page, /movement-subinventory/);
  assert.match(page, /InventoryFilterAutocomplete/);
  assert.match(page, /optionsEndpoint=\{`\$\{REPORT_ENDPOINT\}\/options`\}/);
  assert.match(page, /dates=\{\{ start_date: draft\.start_date, end_date: draft\.end_date \}\}/);
});

test("uses the real-time inventory name for the tab and page title", async () => {
  const [dashboard, page] = await Promise.all([
    readFile(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../pages/sales-reports/inventory-detail.tsx", import.meta.url), "utf8"),
  ]);

  assert.match(dashboard, /["']inventory-detail["']:\s*["']实时库存查询["']/);
  assert.match(page, />实时库存查询<\/h1>/);
});

test("keeps existing inventory permission access under the new parent", () => {
  const visible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.inventory.view"],
  });

  assert.ok(findNode(visible, "inventory-management"));
  assert.equal(findNode(visible, "inventory-detail").name, "实时库存查询");
  assert.equal(findNode(visible, "sales-reports"), null);
});

test("moves the existing inventory permission into inventory management", () => {
  const tree = buildRolePermissionTree([
    {
      id: 1,
      permission_code: "sales.inventory.view",
      permission_name: "查看实时库存查询",
      module_code: "sales",
      action_code: "inventory_view",
    },
  ]);

  const inventoryManagement = findNode(tree, "inventory-management");
  assert.ok(inventoryManagement);
  assert.equal(findNode(tree, "inventory-detail").name, "实时库存查询");
  assert.deepEqual(inventoryManagement.children[0].permissions.map((item) => item.id), [1]);
  assert.equal(findNode(tree, "sales-management"), null);
});

test("shows the historical inventory report only with its own permission", () => {
  const visible = filterAccessibleModuleTree(navigationItems, {
    permission_codes: ["sales.inventory_history.view"],
  });

  assert.ok(findNode(visible, "inventory-management"));
  assert.equal(findNode(visible, "historical-inventory-detail").name, "历史库存明细报表");
  assert.equal(findNode(visible, "inventory-detail"), null);

  const tree = buildRolePermissionTree([
    {
      id: 2,
      permission_code: "sales.inventory_history.view",
      permission_name: "查看历史库存明细报表",
      module_code: "sales",
      action_code: "inventory_history_view",
    },
  ]);
  assert.deepEqual(
    findNode(tree, "historical-inventory-detail").permissions.map((item) => item.id),
    [2],
  );
});

 test("turnover navigation requires its own permission", () => {
  const visible = filterAccessibleModuleTree(navigationItems, {permission_codes: ["sales.inventory_turnover.view"]});
  assert.ok(findNode(visible, "inventory-turnover"));
  assert.equal(findNode(visible, "inventory-detail"), null);
  const denied = filterAccessibleModuleTree(navigationItems, {permission_codes: ["sales.inventory.view"]});
  assert.equal(findNode(denied, "inventory-turnover"), null);
});
