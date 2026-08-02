import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { FileSpreadsheet } from "lucide-react";

import { navigationItems } from "./navigation-items.ts";

const read = (relativePath) => readFile(new URL(relativePath, import.meta.url), "utf8");

function findNode(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findNode(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("OD0002 is available in every requested store folder with its own sales permission", async () => {
  const permissions = await read("./module-permissions.ts");

  for (const folderId of ["new-century-reports", "center-reports", "building-reports"]) {
    const folder = findNode(navigationItems, folderId);
    const od0002 = folder?.subItems?.find((item) => item.id === "od0002-sales-gross-profit");
    assert.equal(od0002?.name, "OD0002 门店销售毛利汇总表");
    assert.equal(od0002?.icon, FileSpreadsheet);
  }
  assert.match(permissions, /["']od0002-sales-gross-profit["']:\s*\[["']sales\.od0002\.view["']\]/);
  assert.doesNotMatch(permissions, /["']sales-reports["']\s*:/);
});

test("main dashboard labels and renders the OD0002 page", async () => {
  const dashboard = await read("../pages/main-dashboard.tsx");

  assert.match(dashboard, /import\s+Od0002SalesGrossProfitPage\s+from\s+["']\.\/sales-reports\/od0002-sales-gross-profit["']/);
  assert.match(dashboard, /["']od0002-sales-gross-profit["']:\s*["']OD0002 门店销售毛利汇总表["']/);
  assert.match(dashboard, /case\s+["']od0002-sales-gross-profit["']:\s*return\s+<Od0002SalesGrossProfitPage\s*\/>/);
});

test("nested report names stay on one line in the expanded sidebar", async () => {
  const sidebar = await read("../components/navigation-sidebar.tsx");

  assert.match(sidebar, /className=\{cn\(["']w-72 bg-slate-900/);
  assert.match(sidebar, /<span className=["']whitespace-nowrap text-\[13px\]["']>\{leaf\.name\}<\/span>/);
  assert.match(sidebar, /pl-\[4\.75rem\]/);
  assert.doesNotMatch(sidebar, /<report\.icon/);
});
