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
