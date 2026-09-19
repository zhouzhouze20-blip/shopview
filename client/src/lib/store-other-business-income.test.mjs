import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import ts from "typescript";

async function loadModule() {
  const sourcePath = new URL("./store-other-business-income.ts", import.meta.url);
  const source = await readFile(sourcePath, "utf8");
  const transpiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(transpiled).toString("base64")}`);
}

test("report params retain year and ending period while all stores stays unfiltered", async () => {
  const module = await loadModule();
  assert.equal(
    module.buildStoreOtherIncomeParams({ financialYear: 2026, endPeriod: 7, storeId: "all" }).toString(),
    "financial_year=2026&end_period=7",
  );
  assert.equal(
    module.buildStoreOtherIncomeParams({ financialYear: 2026, endPeriod: 7, storeId: "603" }).toString(),
    "financial_year=2026&end_period=7&store_id=603",
  );
});

test("amounts are displayed in ten-thousand yuan and rates keep two decimals", async () => {
  const module = await loadModule();
  assert.equal(module.formatIncomeWan(21185617.31), "2,118.56");
  assert.equal(module.formatIncomeRate(-0.09085393), "-9.09%");
  assert.equal(module.formatIncomeRate(null), "—");
});

test("page and navigation use the exact report name", async () => {
  const page = await readFile(new URL("../pages/sales-reports/store-other-business-income.tsx", import.meta.url), "utf8");
  const navigation = await readFile(new URL("./navigation-items.ts", import.meta.url), "utf8");
  const dashboard = await readFile(new URL("../pages/main-dashboard.tsx", import.meta.url), "utf8");
  assert.match(page, /门店其他业务收入/);
  assert.match(page, /门店口径/);
  assert.match(page, /部门口径/);
  assert.match(page, /<Label>截止会计期间<\/Label>/);
  assert.match(page, /length: 12/);
  assert.match(page, /endPeriod: Number\(value\)/);
  assert.doesNotMatch(page, /report\.summary\.current/);
  assert.match(navigation, /store-other-business-income/);
  assert.match(navigation, /门店其他业务收入/);
  assert.match(dashboard, /StoreOtherBusinessIncomePage/);
});
