import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


test("joint renewal revenue draft is wired into navigation and dashboard", async () => {
  const [navigation, permissions, dashboard, roleTree] = await Promise.all([
    readFile(new URL("./navigation-items.ts", import.meta.url), "utf8"),
    readFile(new URL("./module-permissions.ts", import.meta.url), "utf8"),
    readFile(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("./role-permission-tree.ts", import.meta.url), "utf8"),
  ]);

  assert.match(navigation, /id:\s*["']joint-renewal-revenue["']/);
  assert.match(permissions, /["']joint-renewal-revenue["']:\s*\[["']revenue\.view["']\]/);
  assert.match(roleTree, /id:\s*["']joint-renewal-revenue["'][\s\S]*permissionCodes:\s*\[["']revenue\.view["']\]/);
  assert.match(dashboard, /import\s+JointRenewalRevenueReportPage\s+from\s+["']\.\/joint-renewal-revenue-report["']/);
  assert.match(dashboard, /case\s+["']joint-renewal-revenue["']:[\s\S]*<JointRenewalRevenueReportPage\s*\/>/);
});
