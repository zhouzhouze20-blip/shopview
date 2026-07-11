import assert from "node:assert/strict";
import test from "node:test";

import { buildHomeSalesFinancialMeta } from "./financialMonth.ts";

test("home sales financial period is capped by the latest available sales date", () => {
  const meta = buildHomeSalesFinancialMeta("2026-07-08", "2026-07-07");

  assert.equal(meta.periodStart, "2026-06-29");
  assert.equal(meta.periodEnd, "2026-07-07");
  assert.equal(meta.priorPeriodStart, "2025-06-29");
  assert.equal(meta.priorPeriodEnd, "2025-07-07");
});
