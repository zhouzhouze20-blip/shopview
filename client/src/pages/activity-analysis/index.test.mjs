import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";


const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(__dirname, "index.tsx"), "utf8");


test("general activity analysis removes activity search and schedule selection", () => {
  assert.equal(source.includes("活动搜索"), false);
  assert.equal(source.includes("<Label>活动档期</Label>"), false);
  assert.equal(source.includes("/api/activity-analysis/activities"), false);
  assert.equal(/activity_id\s*:/.test(source), false);
  assert.equal(source.includes("const [keyword"), false);
  assert.equal(source.includes("const [activityId"), false);
});

test("general activity analysis renders an authorized store selector", () => {
  assert.match(source, /type StoreOption = \{/);
  assert.match(source, /\/api\/activity-analysis\/store-options/);
  assert.match(source, /const \[selectedStoreCode, setSelectedStoreCode\] = useState\("all"\)/);
  assert.match(source, /const selectedStoreParam = selectedStoreCode === "all" \? "" : selectedStoreCode/);
  assert.match(source, /<Label>门店<\/Label>/);
  assert.match(source, /<SelectItem value="all">全部有权限门店<\/SelectItem>/);
});

test("all summary and drill-down requests use the same store filter", () => {
  const storeParamCount = (source.match(/store_code: selectedStoreParam/g) || []).length;
  assert.ok(storeParamCount >= 8, `expected at least 8 store parameters, found ${storeParamCount}`);

  const storeKeyCount = (source.match(/selectedStoreCode/g) || []).length;
  assert.ok(storeKeyCount >= 10, `expected selected store in query keys and state, found ${storeKeyCount}`);
});

test("range card describes scope store and date without a selected activity", () => {
  assert.match(source, /当前范围：\{analysisScopeLabel\}/);
  assert.match(source, /门店：\{selectedStoreLabel\}/);
  assert.match(source, /日期：\{startDate \|\| "不限"\} 至 \{endDate \|\| "不限"\}/);
  assert.equal(source.includes("selectedActivity"), false);
});

test("switching store clears stale drill-down state", () => {
  assert.match(source, /\[analysisScope, selectedStoreCode, startDate, endDate\]/);
});
