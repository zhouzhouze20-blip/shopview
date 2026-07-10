import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  buildOd0002Params,
  OD0002_TABS,
  previousYearDate,
} from "./od0002-report.ts";

test("previousYearDate returns the same calendar day in the previous year", () => {
  assert.equal(previousYearDate("2026-07-10"), "2025-07-10");
});

test("previousYearDate clamps leap day to February 28", () => {
  assert.equal(previousYearDate("2024-02-29"), "2023-02-28");
});

test("previousYearDate rejects invalid ISO dates with a clear error", () => {
  assert.throws(
    () => previousYearDate("2026-02-30"),
    /Invalid ISO date: 2026-02-30/,
  );
  assert.throws(
    () => previousYearDate("not-a-date"),
    /Invalid ISO date: not-a-date/,
  );
});

test("buildOd0002Params omits the all-store sentinel", () => {
  assert.equal(
    buildOd0002Params("2026-05-29", "2026-06-28", "all").toString(),
    "start_date=2026-05-29&end_date=2026-06-28",
  );
});

test("buildOd0002Params omits an empty store", () => {
  assert.equal(
    buildOd0002Params("2026-05-29", "2026-06-28", "   ").toString(),
    "start_date=2026-05-29&end_date=2026-06-28",
  );
});

test("buildOd0002Params trims a selected store", () => {
  assert.equal(
    buildOd0002Params("2026-05-29", "2026-06-28", " 601 ").toString(),
    "start_date=2026-05-29&end_date=2026-06-28&store_id=601",
  );
});

test("OD0002 exposes the six approved tabs in order", () => {
  assert.deepEqual(
    OD0002_TABS.map((tab) => tab.label),
    ["分店", "部门", "区域", "品类", "柜组", "楼层"],
  );
});

test("frontend model declares every backend response key", async () => {
  const source = await readFile(new URL("./od0002-report.ts", import.meta.url), "utf8");
  const requiredKeys = [
    "sales_current", "sales_prior", "sales_yoy",
    "profit_current", "profit_prior", "profit_yoy",
    "margin_current", "margin_prior", "margin_change",
    "store_code", "store_name", "dimension_code", "dimension_name", "metrics",
    "unmatched_area_category_group_count", "unmatched_floor_group_count",
    "unmatched_area_category_sales_current", "unmatched_floor_sales_current",
    "dates", "selected_store", "dimensions", "totals", "quality", "generated_at",
  ];

  for (const key of requiredKeys) {
    assert.match(source, new RegExp(`\\b${key}\\b`), `missing backend key: ${key}`);
  }
});
