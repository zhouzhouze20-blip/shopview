import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("./mobile-revenue-dashboard.tsx", import.meta.url), "utf8");

test("mobile revenue keeps the desktop metric definitions and hierarchy", () => {
  assert.match(page, /销售毛利/);
  assert.match(page, /费用收益/);
  assert.match(page, /其他收益/);
  assert.match(page, /总收益（不含税口径）/);
  assert.match(page, /type DrillLevel = "stores" \| "departments" \| "groups"/);
  assert.match(page, /setLevel\("departments"\)/);
  assert.match(page, /setLevel\("groups"\)/);
});

test("mobile revenue uses the same permission-scoped dashboard APIs", () => {
  assert.match(page, /\/api\/revenue-map\/dashboard\?start_date=/);
  assert.match(page, /\/api\/revenue-map\/dashboard\/groups\//);
  assert.match(page, /detail_type/);
  assert.match(page, /enabled: hasAccess/);
  assert.match(page, /数据范围与电脑端收益看板一致/);
});

test("mobile revenue exposes gross-profit and fee evidence at cabinet level", () => {
  assert.match(page, /mode: "gross-profit"/);
  assert.match(page, /mode: "fees"/);
  assert.match(page, /每日明细合计/);
  assert.match(page, /付款单号/);
  assert.match(page, /结算单号/);
  assert.match(page, /不含税/);
});

test("mobile revenue defaults to financial month and exposes the requested period presets", () => {
  assert.match(page, /buildMobileRevenueDatePresets\(today\)/);
  assert.match(page, /const defaultPreset = datePresets\[0\]/);
  assert.match(page, /activeDateLabel/);
  assert.match(page, /datePresets\.map/);
  assert.match(page, /结束日期不能早于开始日期/);
});
