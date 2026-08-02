import assert from "node:assert/strict";
import test from "node:test";
import { buildMobileRevenueDatePresets } from "./mobile-revenue-date-presets.ts";

test("mobile revenue defaults to the current financial month and exposes the requested periods", () => {
  assert.deepEqual(buildMobileRevenueDatePresets("2026-07-28"), [
    { label: "本财务月", start: "2026-06-29", end: "2026-07-28" },
    { label: "上个财务月", start: "2026-05-29", end: "2026-06-28" },
    { label: "本年", start: "2026-01-01", end: "2026-07-28" },
  ]);
});

test("previous financial month crosses the year boundary correctly", () => {
  assert.deepEqual(buildMobileRevenueDatePresets("2026-01-10"), [
    { label: "本财务月", start: "2026-01-01", end: "2026-01-10" },
    { label: "上个财务月", start: "2025-11-29", end: "2025-12-31" },
    { label: "本年", start: "2026-01-01", end: "2026-01-10" },
  ]);
});
