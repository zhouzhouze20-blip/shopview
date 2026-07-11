import assert from "node:assert/strict";
import test from "node:test";
import { APP_BRAND } from "./app-branding.ts";

test("uses the department store retail system as the visible product brand", () => {
  assert.equal(APP_BRAND.zhName, "百货零售系统");
  assert.equal(APP_BRAND.enName, "Fuji Retail System");
});
