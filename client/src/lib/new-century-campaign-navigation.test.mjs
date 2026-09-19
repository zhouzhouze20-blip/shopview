import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { navigationItems } from "./navigation-items.ts";
import { MODULE_PERMISSION_REQUIREMENTS } from "./module-permissions.ts";

const read = (relativePath) => readFile(new URL(relativePath, import.meta.url), "utf8");

test("new century campaign analysis is an independent activity module", () => {
  const sales = navigationItems.find((item) => item.id === "sales-management");
  const activities = sales?.subItems?.find((item) => item.id === "activity-analysis-group");
  const module = activities?.subItems?.find((item) => item.id === "new-century-campaign-analysis");

  assert.equal(module?.name, "新世纪活动分析");
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["new-century-campaign-analysis"], [
    "activity_analysis.new_century_campaign.view",
  ]);
});

test("main dashboard renders the new century campaign page", async () => {
  const dashboard = await read("../pages/main-dashboard.tsx");
  assert.match(dashboard, /import NewCenturyCampaignPage from "\.\/activity-analysis\/new-century-campaign"/);
  assert.match(dashboard, /"new-century-campaign-analysis": "新世纪活动分析"/);
  assert.match(dashboard, /case "new-century-campaign-analysis":\s+return <NewCenturyCampaignPage \/>/);
});

test("dashboard page exposes both required detail tabs and the quality warning", async () => {
  const page = await read("../pages/activity-analysis/new-century-campaign.tsx");
  assert.match(page, /<TabsTrigger value="recharge"/);
  assert.match(page, /<TabsTrigger value="gift"/);
  assert.match(page, /卡券数据质量/);
  assert.match(page, /exportNewCenturyCampaign/);
});

test("dashboard uses red for increases and green for decreases", async () => {
  const page = await read("../pages/activity-analysis/new-century-campaign.tsx");

  assert.match(page, /positive \? "text-rose-600" : "text-emerald-600"/);
  assert.doesNotMatch(page, /positive \? "text-emerald-600" : "text-rose-600"/);
});

test("dashboard exposes a gift filter and whole-campaign Excel export", async () => {
  const page = await read("../pages/activity-analysis/new-century-campaign.tsx");

  assert.match(page, /id="gift-template-filter"/);
  assert.match(page, /全部礼品券/);
  assert.match(page, /filteredGiftDetails/);
  assert.match(page, /导出整体活动 Excel/);
});
