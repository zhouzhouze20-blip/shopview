import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { writeFile, unlink } from "node:fs/promises";
import test from "node:test";
import { promisify } from "node:util";

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

test("previousYearDate rejects dates without a representable previous year", () => {
  assert.throws(
    () => previousYearDate("0001-01-01"),
    /Invalid ISO date: 0001-01-01/,
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

test("frontend model accepts the complete backend response contract", async () => {
  const fixtureUrl = new URL("./od0002-report.type-fixture.ts", import.meta.url);
  const metric = `{
    sales_current: 120000, sales_prior: 100000, sales_yoy: 0.2,
    profit_current: 24000, profit_prior: 15000, profit_yoy: 0.6,
    margin_current: 0.2, margin_prior: 0.15, margin_change: 0.05,
  }`;
  const row = `{
    store_code: "601", store_name: "一店",
    dimension_code: "601", dimension_name: "一店",
    metrics: metric, total: metric,
  }`;
  const fixture = `
    import type { Od0002DimensionKey, Od0002Response } from "./od0002-report.ts";
    const metric = ${metric};
    const row = ${row};
    const keys: Od0002DimensionKey[] = ["stores", "departments", "areas", "categories", "groups", "floors"];
    const dimensions = Object.fromEntries(keys.map((key) => [key, [row]])) as Record<Od0002DimensionKey, typeof row[]>;
    const totals = Object.fromEntries(keys.map((key) => [key, metric])) as Record<Od0002DimensionKey, typeof metric>;
    export const response = {
      dates: {
        start_date: "2026-01-01", end_date: "2026-01-31",
        prior_start_date: "2025-01-01", prior_end_date: "2025-01-31",
      },
      selected_store: null,
      dimensions,
      totals,
      quality: {
        unmatched_area_category_group_count: 0,
        unmatched_floor_group_count: 0,
        unmatched_area_category_sales_current: 0,
        unmatched_floor_sales_current: 0,
      },
      generated_at: "2026-07-10T00:00:00+00:00",
    } satisfies Od0002Response;
  `;

  await writeFile(fixtureUrl, fixture);
  try {
    await promisify(execFile)("./node_modules/.bin/tsc", [
      "--noEmit", "--strict", "--target", "ES2020", "--module", "ESNext",
      "--moduleResolution", "bundler", "--allowImportingTsExtensions", "--skipLibCheck",
      fixtureUrl.pathname,
    ]);
  } finally {
    await unlink(fixtureUrl);
  }
});
