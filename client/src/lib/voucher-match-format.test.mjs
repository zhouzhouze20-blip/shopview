import assert from "node:assert/strict";
import test from "node:test";

import { formatVoucherMatchMoney } from "./voucher-match-format.ts";

test("voucher match money always keeps two decimal places", () => {
  assert.equal(formatVoucherMatchMoney(400), "¥400.00");
  assert.equal(formatVoucherMatchMoney(1069.99), "¥1,069.99");
  assert.equal(formatVoucherMatchMoney(0), "¥0.00");
});
