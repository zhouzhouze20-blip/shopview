import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("../pages/mobile-inventory.tsx", import.meta.url), "utf8");
const panel = readFileSync(new URL("../components/mobile-inventory-department.tsx", import.meta.url), "utf8");

test("department is a fourth mobile inventory tab and preserves selection on return", () => {
  assert.match(page, /grid-cols-4/);
  assert.match(page, /<TabsTrigger value="department"[^>]*>部门查询/);
  assert.match(page, /<TabsContent value="department" forceMount className="data-\[state=inactive\]:hidden"/);
  assert.match(page, /返回部门库存列表/);
  assert.match(page, /key=\{menuUser\?\.user_id\}/);
});

test("department queries are scoped by account and render server-side totals", () => {
  assert.match(panel, /inventory-departments", userId/);
  assert.match(panel, /inventory-department-summary", userId, department\?\.value/);
  assert.match(panel, /department_code: department\?\.value/);
  assert.match(panel, /enabled: active && Boolean\(department\)/);
  assert.match(panel, /summary\?\.retail_amount/);
  assert.match(panel, /row\.retail_amount/);
  assert.match(panel, /零售价金额（元）/);
  assert.doesNotMatch(panel, /inventory_purchase_amount_tax_included|含税进价|selling_price/);
  assert.match(panel, /row\.supplier_display/);
  assert.match(panel, /row\.group_display/);
  assert.match(panel, /row\.inventory_quantity/);
});

test("drilldown submits exact group automatically and can refresh the same group", () => {
  const drilldown = page.slice(page.indexOf("const openDepartmentGroup"), page.indexOf("const groupSupplierGroups"));
  assert.match(drilldown, /value: row\.group_code/);
  assert.match(drilldown, /setSelectedGroup\(option\)/);
  assert.match(drilldown, /setGroupInput\(option\.label\)/);
  assert.match(drilldown, /setActiveTab\("group"\)/);
  assert.match(drilldown, /groupQuery\.refetch\(\)/);
  assert.match(drilldown, /setSubmittedGroup\(option\)/);
  assert.match(page, /exact_group: submittedGroup\?\.value/);
});

test("department paging handles empty last page and retry without hiding loaded rows", () => {
  assert.match(panel, /lastPage\.rows\.length > 0 && nextOffset < lastPage\.summary\.total_count/);
  assert.match(panel, /inventoryQuery\.isError && !inventoryQuery\.data/);
  assert.match(panel, /inventoryQuery\.isFetchNextPageError/);
  assert.match(panel, /inventoryQuery\.fetchNextPage\(\)/);
  assert.match(panel, /inventoryQuery\.refetch\(\)/);
});
