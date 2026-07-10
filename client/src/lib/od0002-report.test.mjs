import assert from "node:assert/strict";
import { execFile } from "node:child_process";
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
  await promisify(execFile)("./node_modules/.bin/tsc", [
    "--noEmit", "--strict", "--target", "ES2020", "--module", "ESNext",
    "--moduleResolution", "bundler", "--allowImportingTsExtensions", "--skipLibCheck",
    new URL("./od0002-report.contract.ts", import.meta.url).pathname,
  ]);
});
