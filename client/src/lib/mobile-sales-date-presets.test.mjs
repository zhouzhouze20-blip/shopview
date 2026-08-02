import assert from "node:assert/strict";
import test from "node:test";
import { buildMobileSalesDatePresets } from "./mobile-sales-date-presets.ts";

test("mobile sales shortcuts include today and keep cumulative ranges at the completed-data cutoff", () => {
  assert.deepEqual(buildMobileSalesDatePresets("2026-07-22"), [
    { label: "本日", start: "2026-07-22", end: "2026-07-22" },
    { label: "昨天", start: "2026-07-21", end: "2026-07-21" },
    { label: "本财务月", start: "2026-06-29", end: "2026-07-21" },
    { label: "本年", start: "2026-01-01", end: "2026-07-21" },
  ]);
});

test("financial-month shortcut follows the existing leap-year boundary", () => {
  assert.deepEqual(buildMobileSalesDatePresets("2024-03-01")[2], {
    label: "本财务月",
    start: "2024-02-29",
    end: "2024-02-29",
  });
});
