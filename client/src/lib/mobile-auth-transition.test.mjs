import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const libDir = dirname(fileURLToPath(import.meta.url));
const authSource = readFileSync(join(libDir, "../contexts/AuthContext.tsx"), "utf8");
const appSource = readFileSync(join(libDir, "../App.tsx"), "utf8");
const loginSource = readFileSync(join(libDir, "../pages/login.tsx"), "utf8");

test("logout waits for the server before exposing the signed-out state", () => {
  const logoutBody = authSource.match(/const logout = async \(\) => \{([\s\S]*?)\n  \};/)?.[1] ?? "";
  const requestIndex = logoutBody.indexOf('await apiPost("/api/auth/logout", {})');
  const clearUserIndex = logoutBody.indexOf("setUser(null)");

  assert.ok(requestIndex >= 0, "logout request should exist");
  assert.ok(clearUserIndex > requestIndex, "the user must stay present until the logout request completes");
  assert.match(logoutBody, /setLoading\(true\)/);
  assert.match(logoutBody, /setLoading\(false\)/);
});

test("initial auth, logout, and silent mobile login share one loading screen", () => {
  assert.match(appSource, /<AuthLoadingScreen \/>/);
  assert.match(loginSource, /return <AuthLoadingScreen \/>/);
  assert.doesNotMatch(appSource, /正在加载登录状态/);
});

test("a rejected mobile WeCom login cannot immediately restart after the error query is consumed", () => {
  assert.match(
    loginSource,
    /const \[mobileAutoLoginBlocked\] = useState\([\s\S]*?URLSearchParams\(window\.location\.search\)\.has\("auth_error"\)/,
  );
  assert.match(
    loginSource,
    /if \(!mobileClient \|\| !isWeComClient\(\) \|\| mobileAutoLoginBlocked\) return;/,
  );
  assert.match(
    loginSource,
    /mobileClient && isWeComClient\(\) && !mobileAutoLoginBlocked && !mobileAutoLoginFailed/,
  );
});
