import assert from "node:assert/strict";
import { buildSync } from "esbuild";
import { pathToFileURL } from "node:url";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const workdir = mkdtempSync(join(tmpdir(), "sales-browse-journey-"));
const outfile = join(workdir, "sales-browse-journey.mjs");

try {
  buildSync({
    entryPoints: [new URL("./sales-browse-journey.ts", import.meta.url).pathname],
    outfile,
    bundle: true,
    platform: "node",
    format: "esm",
  });
  const { buildSalesBrowseJourneys } = await import(pathToFileURL(outfile));

  const log = (id, created_at, query_conditions) => ({
    id,
    user_id: 7,
    username: "chen",
    real_name: "陈晓楠",
    action_code: "query",
    resource_code: "mobile-sales-dashboard",
    detail: { query_conditions: { query_type: "sales", ...query_conditions } },
    created_at,
  });

  const journeys = buildSalesBrowseJourneys([
    log(6, "2026-08-01T12:06:00", { query_level: "tickets", group_code: "G02", group_name: "欧舒丹厅" }),
    log(5, "2026-08-01T12:05:50", { query_level: "departments", navigation_action: "back", to_level: "departments", store_name: "常州购物中心" }),
    log(4, "2026-08-01T12:05:40", { query_level: "detail", ticket_no: "P2608010001" }),
    log(3, "2026-08-01T12:05:30", { query_level: "tickets", group_code: "G01", group_name: "雅诗兰黛厅" }),
    log(2, "2026-08-01T12:05:20", { query_level: "groups", department_code: "D01", department_name: "化妆品部" }),
    log(1, "2026-08-01T12:05:10", { query_level: "departments", store_id: "01", store_name: "常州购物中心" }),
  ]);

  assert.equal(journeys.length, 1);
  assert.equal(journeys[0].userName, "陈晓楠");
  assert.deepEqual(
    journeys[0].steps.map(({ kind, label, value }) => ({ kind, label, value })),
    [
      { kind: "store", label: "门店", value: "常州购物中心" },
      { kind: "department", label: "部门", value: "化妆品部" },
      { kind: "group", label: "柜组", value: "雅诗兰黛厅" },
      { kind: "ticket", label: "小票", value: "P2608010001" },
      { kind: "return", label: "返回部门列表", value: "常州购物中心" },
      { kind: "group", label: "柜组", value: "欧舒丹厅" },
    ],
  );

  const mobileSalesSource = readFileSync(new URL("../pages/mobile-sales-dashboard.tsx", import.meta.url), "utf8");
  assert.match(mobileSalesSource, /navigation_action:\s*"back"/);
  assert.match(mobileSalesSource, /to_level:\s*"departments"/);
  assert.match(mobileSalesSource, /ticket_no:\s*`\$\{row\.invoice_no \|\| row\.billno\}`/);
  assert.match(mobileSalesSource, /department_name:\s*selectedDepartment\?\.department_name/);
  assert.match(mobileSalesSource, /group_name:\s*selectedGroup\?\.group_name/);
} finally {
  rmSync(workdir, { recursive: true, force: true });
}
