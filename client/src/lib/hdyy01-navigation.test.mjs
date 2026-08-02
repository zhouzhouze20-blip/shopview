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

test("new-century reports use the approved report order", () => {
  const reports = findNode(navigationItems, "sales-reports");
  const newCenturyReports = findNode(navigationItems, "new-century-reports");
  assert.ok(reports);
  assert.ok(newCenturyReports);

  const reportIds = newCenturyReports.subItems.map((item) => item.id);
  const dailyFollowupIndex = reportIds.indexOf("daily-sales-followup");
  assert.notEqual(dailyFollowupIndex, -1);
  assert.deepEqual(reportIds.slice(dailyFollowupIndex, dailyFollowupIndex + 5), [
    "daily-sales-followup",
    OD0002_ID,
    "od0004-monthly-followup",
    "od0005-micro-mall-brand-sales",
    HDYY01_ID,
  ]);

  const hdyy01 = newCenturyReports.subItems[dailyFollowupIndex + 4];
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
