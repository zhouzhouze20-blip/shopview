import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { build } from "esbuild";

const source = path.resolve("client/src/lib/merchant-planning-map.ts");
const outDir = await mkdtemp(path.join(tmpdir(), "merchant-planning-map-"));
const outfile = path.join(outDir, "merchant-planning-map.mjs");

await build({
  entryPoints: [source],
  outfile,
  bundle: true,
  platform: "node",
  format: "esm",
  logLevel: "silent",
});

const { candidateMapStyle, candidateTypeText } = await import(pathToFileURL(outfile).href);

assert.equal(candidateTypeText("VACANT"), "空置");
assert.equal(candidateTypeText("LOW_EFFICIENCY"), "低效");
assert.equal(candidateTypeText("EXPIRING"), "到期");
assert.equal(candidateTypeText("NORMAL"), "普通");

assert.equal(candidateMapStyle("VACANT").fill, "rgba(14,165,233,0.58)");
assert.equal(candidateMapStyle("LOW_EFFICIENCY").stroke, "rgba(190,18,60,0.94)");
assert.equal(candidateMapStyle("EXPIRING").fill, "rgba(245,158,11,0.58)");
assert.equal(candidateMapStyle("NORMAL").stroke, "rgba(100,116,139,0.65)");
assert.equal(candidateMapStyle("VACANT", true).stroke, "rgba(37,99,235,1)");

await writeFile(path.join(outDir, "ok"), "ok");
console.log("merchant planning map helper ok");
