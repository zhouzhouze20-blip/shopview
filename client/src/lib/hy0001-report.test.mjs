import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";


async function loadModule() {
  const url = new URL("./hy0001-report.ts", import.meta.url);
  const source = await readFile(url, "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
}


test("HY0001 defaults to the previous full calendar month as a date range", async () => {
  const module = await loadModule();
  assert.deepEqual(module.defaultHy0001DateRange(new Date(2026, 7, 2)), {
    start: "2026-07-01",
    end: "2026-07-31",
  });
  assert.deepEqual(module.defaultHy0001DateRange(new Date(2026, 0, 15)), {
    start: "2025-12-01",
    end: "2025-12-31",
  });
});


test("HY0001 query keeps the exact date, store, and optional department tuple", async () => {
  const module = await loadModule();
  assert.equal(
    module.buildHy0001Params("2026-03-03", "2026-03-18", "001", "00101").toString(),
    "start_date=2026-03-03&end_date=2026-03-18&store_id=001&department_id=00101",
  );
  assert.equal(
    module.buildHy0001Params("2026-03-03", "2026-03-18", "001", module.HY0001_ALL_DEPARTMENTS).toString(),
    "start_date=2026-03-03&end_date=2026-03-18&store_id=001",
  );
});


test("HY0001 uses Chinese financial yoy colors and does not invent zero-base growth", async () => {
  const module = await loadModule();
  assert.equal(module.hy0001YoyClass(0.1), "text-red-600");
  assert.equal(module.hy0001YoyClass(-0.1), "text-emerald-600");
  assert.equal(module.formatHy0001Yoy(null), "—");
});


test("HY0001 is registered in the center report folder with its own permission", async () => {
  const navigationSource = await readFile(new URL("./navigation-items.ts", import.meta.url), "utf8");
  const permissionsSource = await readFile(new URL("./module-permissions.ts", import.meta.url), "utf8");
  const dashboardSource = await readFile(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8");
  const pageSource = await readFile(new URL("../pages/sales-reports/hy0001-key-brand-member.tsx", import.meta.url), "utf8");

  const centerFolder = navigationSource.slice(
    navigationSource.indexOf('id: "center-reports"'),
    navigationSource.indexOf('id: "building-reports"'),
  );
  assert.match(centerFolder, /HY0001 重点品牌会员消费情况/);
  assert.match(permissionsSource, /"hy0001-key-brand-member": \["sales\.hy0001\.view"\]/);
  assert.match(dashboardSource, /Hy0001KeyBrandMemberPage/);
  assert.match(pageSource, />品类主管</);
  assert.match(pageSource, />开始日期</);
  assert.match(pageSource, />结束日期</);
  assert.match(pageSource, />本期人数</);
  assert.match(pageSource, />同期人数</);
  assert.match(pageSource, />人数同比</);
  assert.match(pageSource, /\/api\/sales\/reports\/hy0001\/export/);
});
