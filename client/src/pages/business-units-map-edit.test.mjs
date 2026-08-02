import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = readFileSync(new URL("./business-units.tsx", import.meta.url), "utf8");

test("map editing shows all business-unit geometries by default", () => {
  assert.match(
    pageSource,
    /const \[showPendingOnly, setShowPendingOnly\] = useState\(false\);/,
    "review-only filtering must be opt-in so existing business units remain clickable",
  );
});
