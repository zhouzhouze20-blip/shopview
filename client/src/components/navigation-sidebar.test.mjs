import assert from "node:assert/strict";
import test from "node:test";
import { navigationItems } from "../lib/navigation-items.ts";

function findItem(items, id) {
  for (const item of items) {
    if (item.id === id) return item;
    const child = findItem(item.subItems ?? [], id);
    if (child) return child;
  }
  return null;
}

test("groups voucher matching and coupon monthly balance under financial activity settlement", () => {
  const salesManagement = findItem(navigationItems, "sales-management");
  const activityAnalysisGroup = findItem(navigationItems, "activity-analysis-group");
  const financialManagement = findItem(navigationItems, "financial-management");
  const activitySettlement = findItem(navigationItems, "activity-settlement");

  assert.ok(salesManagement);
  assert.ok(activityAnalysisGroup);
  assert.deepEqual(
    (activityAnalysisGroup.subItems ?? []).map((item) => item.id),
    ["activity-analysis", "points-activity-analysis", "star-diamond-analysis"],
  );

  assert.ok(financialManagement);
  assert.ok(activitySettlement);
  assert.equal(activitySettlement.name, "活动结算");
  assert.deepEqual(
    (activitySettlement.subItems ?? []).map((item) => item.id),
    ["voucher-match", "confirmed-revenue-daily", "coupon-monthly-balance"],
  );
});

test("shows the mid-year celebration name for the existing points activity module", () => {
  const pointsActivity = findItem(navigationItems, "points-activity-analysis");

  assert.ok(pointsActivity);
  assert.equal(pointsActivity.name, "中心年中庆活动");
});
