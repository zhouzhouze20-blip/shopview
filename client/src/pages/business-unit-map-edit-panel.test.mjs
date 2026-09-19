import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(here, "business-units.tsx"), "utf8");

assert.match(source, /role="dialog"/);
assert.match(source, /aria-modal="false"/);
assert.match(source, /mapEditPosition/);
assert.match(source, /startMapEditDrag/);
assert.match(source, /onPointerMove=\{moveMapEditPanel\}/);
assert.match(source, /拖动此处移动/);
assert.doesNotMatch(source, /<Dialog open=\{mapEditOpen\}/);

console.log("business unit map edit panel tests passed");
