import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const page = readFileSync(resolve("client/src/pages/activity-analysis/confirmed-revenue-daily.tsx"), "utf8");
const dashboard = readFileSync(resolve("client/src/pages/main-dashboard.tsx"), "utf8");

assert.match(page, /确认收入占比/);
assert.match(page, /coupon-confirmed-revenue-daily/);
assert.match(page, /couponType/);
assert.match(page, /setCouponType/);
assert.match(page, /coupon_type/);
assert.match(page, /卡券/);
assert.match(page, /couponOptions/);
assert.match(page, /<Select value=\{couponType\} onValueChange=\{setCouponType\}>/);
assert.doesNotMatch(page, /id="confirmed-revenue-coupon-type"[\s\S]*?<Input/);
assert.match(page, /confirmed_revenue_amount/);
assert.match(page, /missing_rate_count/);
assert.doesNotMatch(page, /刷新每日变动/);
assert.doesNotMatch(page, /确认月结/);
assert.match(dashboard, /ConfirmedRevenueDailyPage/);
assert.match(dashboard, /case "confirmed-revenue-daily"/);

console.log("confirmed revenue daily page checks passed");
