import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const page = readFileSync(resolve("client/src/pages/joint-payment-confirmation.tsx"), "utf8");
const hook = readFileSync(resolve("client/src/hooks/useJointPaymentConfirmation.ts"), "utf8");
const dashboard = readFileSync(resolve("client/src/pages/main-dashboard.tsx"), "utf8");
const navigation = readFileSync(resolve("client/src/lib/navigation-items.ts"), "utf8");
const permissions = readFileSync(resolve("client/src/lib/module-permissions.ts"), "utf8");

assert.match(page, /联营付款单确认/);
assert.match(page, /生成待确认/);
assert.match(page, /已审核/);
assert.match(page, /财务收入已确认/);
assert.match(page, /本财务月审核金额/);
assert.match(page, /current_financial_month_audited_amount/);
assert.match(page, /current_financial_month_start/);
assert.match(page, /current_financial_month_end/);
assert.match(page, /最新状态业务日期/);
assert.match(page, /付款单明细/);
assert.match(page, /结算单号/);
assert.match(page, /全部有权部门/);
assert.match(page, /departmentCode/);
assert.match(page, /useJointPaymentDepartmentOptions/);
assert.match(page, /部门\/柜组/);
assert.match(page, /状态日期：生成单取录入日期，已审核单取审核日期/);
assert.match(hook, /joint-payment-confirmation\/options/);
assert.match(hook, /department_code/);
assert.match(dashboard, /JointPaymentConfirmationPage/);
assert.match(dashboard, /case "joint-payment-confirmation"/);
assert.match(navigation, /id: "joint-payment-confirmation", name: "联营付款单确认"/);
assert.match(permissions, /"joint-payment-confirmation": \["settlement\.joint_payment_confirmation\.view"\]/);

console.log("joint payment confirmation page checks passed");
