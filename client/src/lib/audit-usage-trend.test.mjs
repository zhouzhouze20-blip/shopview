import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildAuditUsageTrendUrl } from "./audit-usage-trend.ts";

const systemConfigSource = readFileSync(new URL("../pages/system-config.tsx", import.meta.url), "utf8");

test("audit usage trend URL contains exactly one query delimiter", () => {
  assert.equal(
    buildAuditUsageTrendUrl("year", "2026"),
    "/api/system/audit-statistics/trend?granularity=year&period=2026",
  );
  assert.equal(
    buildAuditUsageTrendUrl("month", "2026-08"),
    "/api/system/audit-statistics/trend?granularity=month&period=2026-08",
  );
});

test("audit usage chart displays operation and user values", () => {
  assert.match(systemConfigSource, /<LabelList\s+dataKey="operation_count"/);
  assert.match(systemConfigSource, /<LabelList\s+dataKey="usage_users"/);
});

test("person and module statistics preserve month and year filters", () => {
  for (const dimension of ["person", "module"]) {
    for (const [granularity, period] of [["month", "2026-09"], ["year", "2026"]]) {
      const url = new URL(buildAuditUsageTrendUrl(granularity, period, dimension), "http://localhost");
      assert.equal(url.searchParams.get("dimension"), dimension);
      assert.equal(url.searchParams.get("granularity"), granularity);
      assert.equal(url.searchParams.get("period"), period);
    }
  }
});
