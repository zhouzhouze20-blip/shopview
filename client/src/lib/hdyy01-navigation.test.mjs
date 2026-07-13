import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { FileSpreadsheet } from "lucide-react";
import { navigationItems } from "./navigation-items.ts";
import {
  MODULE_PERMISSION_REQUIREMENTS,
  canAccessModule,
  filterAccessibleModuleTree,
} from "./module-permissions.ts";

const HDYY01_ID = "hdyy01-group-operation-analysis";
const OD0002_ID = "od0002-sales-gross-profit";

function findNode(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findNode(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("HDYY01 menu follows OD0002 in the sales reports folder", () => {
  const reports = findNode(navigationItems, "sales-reports");
  assert.ok(reports);

  const reportIds = reports.subItems.map((item) => item.id);
  const od0002Index = reportIds.indexOf(OD0002_ID);
  assert.notEqual(od0002Index, -1);
  assert.equal(reportIds[od0002Index + 1], HDYY01_ID);

  const hdyy01 = reports.subItems[od0002Index + 1];
  assert.equal(hdyy01.name, "HDYY01柜组经营分析表");
  assert.equal(hdyy01.icon, FileSpreadsheet);
});

test("HDYY01 has one exact module permission and no broad sales reports permission", () => {
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS[HDYY01_ID], ["sales.hdyy01.view"]);
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS[OD0002_ID], ["sales.od0002.view"]);
  assert.equal(Object.hasOwn(MODULE_PERMISSION_REQUIREMENTS, "sales-reports"), false);
});

test("OD0002-only access neither exposes nor grants HDYY01", () => {
  const user = { permission_codes: ["sales.od0002.view"] };
  const visible = filterAccessibleModuleTree(navigationItems, user);

  assert.ok(findNode(visible, OD0002_ID));
  assert.equal(findNode(visible, HDYY01_ID), null);
  assert.equal(canAccessModule(user, OD0002_ID), true);
  assert.equal(canAccessModule(user, HDYY01_ID), false);
});

test("HDYY01-only access neither exposes nor grants OD0002", () => {
  const user = { permission_codes: ["sales.hdyy01.view"] };
  const visible = filterAccessibleModuleTree(navigationItems, user);

  assert.ok(findNode(visible, HDYY01_ID));
  assert.equal(findNode(visible, OD0002_ID), null);
  assert.equal(canAccessModule(user, HDYY01_ID), true);
  assert.equal(canAccessModule(user, OD0002_ID), false);
});

test("main dashboard labels and renders the HDYY01 page", async () => {
  const dashboard = await readFile(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8");

  assert.match(
    dashboard,
    /import\s+Hdyy01GroupOperationAnalysisPage\s+from\s+["']\.\/sales-reports\/hdyy01-group-operation-analysis["']/,
  );
  assert.match(dashboard, /["']hdyy01-group-operation-analysis["']:\s*["']HDYY01柜组经营分析表["']/);
  assert.match(
    dashboard,
    /case\s+["']hdyy01-group-operation-analysis["']:\s*return\s+<Hdyy01GroupOperationAnalysisPage\s*\/>/,
  );
});
