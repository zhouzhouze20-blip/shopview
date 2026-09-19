import assert from "node:assert/strict";
import test from "node:test";

import { supplierActualReceivableAmount } from "./rental-receivable-amounts.ts";

test("supplier actual receivable subtracts sales refunds in currency cents", () => {
  assert.equal(supplierActualReceivableAmount(93426.45, 18105), 75321.45);
  assert.equal(supplierActualReceivableAmount(1376.2, 42196.24), -40820.04);
  assert.equal(supplierActualReceivableAmount(0.3, 0.1), 0.2);
});

test("supplier actual receivable treats missing summary values as zero", () => {
  assert.equal(supplierActualReceivableAmount(undefined, undefined), 0);
  assert.equal(supplierActualReceivableAmount(125.5, null), 125.5);
});
