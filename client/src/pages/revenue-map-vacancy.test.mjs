import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const revenueMapSource = readFileSync(new URL("./revenue-map.tsx", import.meta.url), "utf8");

test("vacant halls use a dedicated color before revenue bands", () => {
  assert.match(revenueMapSource, /vacant:\s*\{[\s\S]*fill: "rgba\(207, 192, 232, 0\.84\)"/);
  assert.match(revenueMapSource, /isVacant\s*\? REVENUE_MAP_PALETTE\.vacant\s*:\s*revenueFill/);
  assert.match(revenueMapSource, /geo\.unit_status \|\| businessUnitById\.get\(geo\.unit_id\)\?\.status/);
});

test("vacant halls are separate from no-data in the legend and counts", () => {
  assert.match(revenueMapSource, /REVENUE_MAP_PALETTE\.vacant\.fill[^\n]*空置/);
  assert.match(revenueMapSource, /浅紫色为空置，浅灰色为无数据/);
  assert.match(revenueMapSource, /高\/中\/低\/空置\/无/);
  assert.match(revenueMapSource, /acc\.vacant \+= 1/);
});
