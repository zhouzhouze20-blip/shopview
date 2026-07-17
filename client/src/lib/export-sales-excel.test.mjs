import assert from "node:assert/strict";
import test from "node:test";

import { buildGroupExportTable, buildTicketExportTable } from "./export-sales-excel.ts";

const groupRows = [{
  group_code: "6010101035",
  group_name: "测试柜组",
  department_name: "中心一部(化妆)",
  ticket_count: 1,
  quantity: 2,
  priced_sales_amount: 1200,
  effective_sales: 900,
  net_profit: 90,
  ticket_margin: 0.1,
  net_margin: 0.1,
  same_period_ticket_count: 1,
  same_period_effective_sales: 800,
  same_period_net_profit: 80,
  same_period_margin: 0.1,
}];

const ticketRows = [{
  billno: "13000001",
  sale_date: "2026-07-10",
  sale_datetime: "2026-07-10T10:00:00.123456",
  cash_register_no: "1007",
  invoice_no: "1001",
  quantity: 2,
  priced_sales_amount: 1200,
  effective_sales: 900,
  net_profit: 90,
  ticket_margin: 0.1,
  authorized_discount: 10,
  mzk: 0,
  lq: 0,
  consumption_point: 9,
  birthday_month_member_point: 0,
  transaction_type: "销售",
}];

test("group export inserts retail price only when requested", () => {
  const withRetail = buildGroupExportTable(groupRows, true);
  assert.equal(withRetail[0][2], "零售价");
  assert.equal(withRetail[1][2], 1200);
  assert.equal(withRetail.at(-1)[2], 1200);

  const withoutRetail = buildGroupExportTable(groupRows, false);
  assert.equal(withoutRetail[0].includes("零售价"), false);
  assert.equal(withoutRetail[0][2], "本期销售收入");
});

test("ticket export replaces cashier with cash register before invoice and inserts retail price before sales revenue", () => {
  const withRetail = buildTicketExportTable(ticketRows, true);
  assert.equal(withRetail[0].includes("商品数"), false);
  assert.equal(withRetail[0].includes("收银员"), false);
  assert.equal(withRetail[0][3], "收银机号");
  assert.equal(withRetail[0][4], "小票号");
  assert.equal(withRetail[1][3], "1007");
  assert.equal(withRetail[1][4], "1001");
  assert.equal(withRetail[1][1], "2026-07-10 10:00:00");
  assert.equal(withRetail[0][5], "零售价");
  assert.equal(withRetail[0][6], "销售收入");
  assert.equal(withRetail[1][5], 1200);
  assert.equal(withRetail.at(-1)[5], 1200);

  const withoutRetail = buildTicketExportTable(ticketRows, false);
  assert.equal(withoutRetail[0].includes("商品数"), false);
  assert.equal(withoutRetail[0].includes("零售价"), false);
  assert.equal(withoutRetail[0][5], "销售收入");
});
