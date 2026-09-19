import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = readFileSync(new URL("./business-units.tsx", import.meta.url), "utf8");
const hookSource = readFileSync(new URL("../hooks/useBusinessUnits.ts", import.meta.url), "utf8");

test("经营单元删除前说明历史财务数据会保留", () => {
  assert.match(pageSource, /历史收益和月结金额会保留/);
  assert.match(pageSource, /只解除与该\$\{deleteConfirmPrefix\}的关联/);
});

test("删除成功提示保留的月结明细数量", () => {
  assert.match(hookSource, /detached_month_close_adjustments\?: number/);
  assert.match(pageSource, /result\.detached_month_close_adjustments/);
  assert.match(pageSource, /已保留 \$\{preservedMonthCloseRows\} 条历史月结明细和金额/);
});
