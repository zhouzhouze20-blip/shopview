import assert from "node:assert/strict";
import test from "node:test";

import { isMobileClient, isWeComClient, shouldUseMobileHome, shouldUseMobileLogin } from "./mobile-entry.ts";

test("detects phones from either the user agent or compact viewport", () => {
  assert.equal(isMobileClient({ userAgent: "Mozilla/5.0 (iPhone)", viewportWidth: 1024 }), true);
  assert.equal(isMobileClient({ userAgent: "Mozilla/5.0 (Macintosh)", viewportWidth: 390 }), true);
  assert.equal(isMobileClient({ userAgent: "Mozilla/5.0 (Macintosh)", viewportWidth: 1440 }), false);
});

test("detects the Enterprise WeChat embedded browser", () => {
  assert.equal(isWeComClient("Mozilla/5.0 wxwork/4.1.30 MicroMessenger"), true);
  assert.equal(isWeComClient("Mozilla/5.0 MicroMessenger"), false);
});

test("routes compact home entries to the mobile workbench without hijacking desktop pages", () => {
  assert.equal(shouldUseMobileHome("/", { viewportWidth: 390 }), true);
  assert.equal(shouldUseMobileHome("/dashboard", { viewportWidth: 390 }), true);
  assert.equal(shouldUseMobileHome("/stores", { viewportWidth: 390 }), false);
  assert.equal(shouldUseMobileHome("/", { viewportWidth: 1440 }), false);
  assert.equal(shouldUseMobileHome("/mobile", { viewportWidth: 1440 }), true);
});

test("keeps the explicit mobile entry on the mobile login experience", () => {
  assert.equal(shouldUseMobileLogin("/mobile", { userAgent: "Desktop", viewportWidth: 1440 }), true);
  assert.equal(shouldUseMobileLogin("/mobile/contracts", { userAgent: "Desktop", viewportWidth: 1440 }), true);
  assert.equal(shouldUseMobileLogin("/", { userAgent: "Desktop", viewportWidth: 390 }), true);
  assert.equal(shouldUseMobileLogin("/", { userAgent: "Desktop", viewportWidth: 1440 }), false);
});

test("preserves explicit dashboard views in compact and mobile browsers", () => {
  const desktop = { userAgent: "Mozilla/5.0 (Macintosh)", viewportWidth: 640 };
  const phone = { userAgent: "Mozilla/5.0 (iPhone)", viewportWidth: 390 };
  for (const signals of [desktop, phone]) {
    assert.equal(shouldUseMobileHome("/dashboard", signals, "?view=coupon-campaigns"), false);
    assert.equal(shouldUseMobileHome("/", signals, "?storeId=2&view=coupon-campaigns"), false);
    assert.equal(shouldUseMobileHome("/dashboard", signals, "?storeId=2"), true);
    assert.equal(shouldUseMobileHome("/dashboard", signals, "?view="), true);
    assert.equal(shouldUseMobileHome("/mobile", signals, "?view=coupon-campaigns"), true);
  }
});

test("uses the current URL search when the dashboard caller omits it", (t) => {
  const previousWindow = globalThis.window;
  t.after(() => {
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  });
  globalThis.window = { location: { search: "?view=coupon-campaigns" } };
  assert.equal(shouldUseMobileHome("/dashboard", { userAgent: "Desktop", viewportWidth: 640 }), false);
});
