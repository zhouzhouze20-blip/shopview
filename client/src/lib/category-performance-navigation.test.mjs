import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { navigationItems } from "./navigation-items.ts";
import { MODULE_PERMISSION_REQUIREMENTS } from "./module-permissions.ts";

const currentDir = dirname(fileURLToPath(import.meta.url));

test("category performance is available under sales management", () => {
  const sales = navigationItems.find((item) => item.id === "sales-management");
  const module = sales?.subItems?.find((item) => item.id === "category-performance");

  assert.ok(module);
  assert.equal(module.name, "品类主管绩效");
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["category-performance"], [
    "sales.category_performance.view",
  ]);
});

test("main dashboard renders the category performance page", () => {
  const source = readFileSync(resolve(currentDir, "../pages/main-dashboard.tsx"), "utf8");

  assert.match(source, /import CategoryPerformancePage from "\.\/category-performance"/);
  assert.match(source, /case "category-performance":\s+return <CategoryPerformancePage \/>/);
});

test("brand assignment maintenance exposes the key-brand marker", () => {
  const source = readFileSync(resolve(currentDir, "../pages/category-performance.tsx"), "utf8");

  assert.match(source, /<Label>重点属性<\/Label>/);
  assert.match(source, /is_key_brand: brandIsKey === "true"/);
  assert.match(source, /其中重点品牌 \{keyBrandAssignmentCount\}/);
});

test("defaults to the latest maintained performance period for each store", () => {
  const source = readFileSync(resolve(currentDir, "../pages/category-performance.tsx"), "utf8");

  assert.match(source, /latest_period\?: string \| null/);
  assert.match(source, /setPeriod\(optionsQuery\.data\.latest_period \?\? currentPeriod\(\)\)/);
});
