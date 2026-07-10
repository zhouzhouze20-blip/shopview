import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (relativePath) => readFile(new URL(relativePath, import.meta.url), "utf8");

test("OD0002 is a sales report sibling with its own sales permission", async () => {
  const sidebar = await read("../components/navigation-sidebar.tsx");
  const navigation = sidebar.includes('from "@/lib/navigation-items"')
    ? await read("./navigation-items.ts")
    : sidebar;
  const permissions = await read("./module-permissions.ts");

  assert.match(
    navigation,
    /id:\s*["']sales-reports["'][\s\S]*subItems:\s*\[[\s\S]*id:\s*["']commodity-sales-detail["'][\s\S]*id:\s*["']od0002-sales-gross-profit["'][\s\S]*name:\s*["']OD0002 门店销售毛利汇总表["'][\s\S]*icon:\s*FileSpreadsheet/,
  );
  assert.match(permissions, /["']od0002-sales-gross-profit["']:\s*\[["']sales\.view["']\]/);
  assert.doesNotMatch(permissions, /["']sales-reports["']\s*:/);
});

test("main dashboard labels and renders the OD0002 page", async () => {
  const dashboard = await read("../pages/main-dashboard.tsx");

  assert.match(dashboard, /import\s+Od0002SalesGrossProfitPage\s+from\s+["']\.\/sales-reports\/od0002-sales-gross-profit["']/);
  assert.match(dashboard, /["']od0002-sales-gross-profit["']:\s*["']OD0002 门店销售毛利汇总表["']/);
  assert.match(dashboard, /case\s+["']od0002-sales-gross-profit["']:\s*return\s+<Od0002SalesGrossProfitPage\s*\/>/);
});
