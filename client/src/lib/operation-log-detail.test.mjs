import assert from "node:assert/strict";
import { buildSync } from "esbuild";
import { pathToFileURL } from "node:url";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const workdir = mkdtempSync(join(tmpdir(), "operation-log-detail-"));
const outfile = join(workdir, "operation-log-detail.mjs");

try {
  buildSync({
    entryPoints: [new URL("./operation-log-detail.ts", import.meta.url).pathname],
    outfile,
    bundle: true,
    platform: "node",
    format: "esm",
  });
  const { formatOperationQueryConditions } = await import(pathToFileURL(outfile));

  assert.equal(formatOperationQueryConditions(null), "-");
  assert.equal(
    formatOperationQueryConditions({
      query_conditions: {
        start_date: "2026-08-01",
        end_date: "2026-08-01",
        query_level: "stores",
        store_name: "半山店",
      },
    }),
    "开始日期：2026-08-01；结束日期：2026-08-01；查询层级：门店汇总；门店：半山店",
  );
} finally {
  rmSync(workdir, { recursive: true, force: true });
}
