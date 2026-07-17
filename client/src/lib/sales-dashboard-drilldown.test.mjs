import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  buildProductTicketParams,
  getReceiptProductDisplay,
  getDepartmentDrilldownTab,
  getGroupDrilldownTab,
  isCenterCosmeticsRetailPriceScope,
  isSupermarketDepartment,
} from "./sales-dashboard-drilldown.ts";

test("supermarket and fresh departments are detected by name or code", () => {
  assert.equal(isSupermarketDepartment({ department_code: "6010104", department_name: "中心BF部(超市)" }), true);
  assert.equal(isSupermarketDepartment({ department_code: "6010106", department_name: "新世纪生鲜部" }), true);
  assert.equal(isSupermarketDepartment({ department_code: "6010102", department_name: "中心四部(男装)" }), false);
});

test("department drilldown keeps supermarket departments on the group step", () => {
  assert.equal(getDepartmentDrilldownTab({ department_code: "6010104", department_name: "中心BF部(超市)" }), "groups");
  assert.equal(getDepartmentDrilldownTab({ department_code: "6010102", department_name: "中心四部(男装)" }), "groups");
});

test("group drilldown sends supermarket groups to group goods and normal groups to tickets", () => {
  assert.equal(getGroupDrilldownTab({ department_code: "6010104", department_name: "中心BF部(超市)" }), "department-products");
  assert.equal(getGroupDrilldownTab({ department_code: "6010102", department_name: "中心四部(男装)" }), "tickets");
});

test("selected product becomes ticket query params", () => {
  assert.deepEqual(
    buildProductTicketParams({
      goods_code: "2034366",
      barcode: "2000020343666",
      supplier_code: "10609",
    }),
    {
      goods_code: "2034366",
      barcode: "2000020343666",
      supplier_code: "10609",
    },
  );
  assert.deepEqual(buildProductTicketParams(null), {});
});

test("receipt product display keeps goods code and barcode visible", () => {
  assert.deepEqual(
    getReceiptProductDisplay({
      name: "牛丼饭 单人定食",
      code: "2054406",
      barcode: "2000020544063",
    }),
    {
      name: "牛丼饭 单人定食",
      identifiers: ["商品编码：2054406", "条码：2000020544063"],
    },
  );
});

test("retail price scope matches only Changzhou Shopping Center cosmetics", () => {
  assert.equal(
    isCenterCosmeticsRetailPriceScope(
      { store_id: "1", store_name: "常州购物中心" },
      { department_code: "6010101", department_name: "中心一部(化妆)" },
    ),
    true,
  );
  assert.equal(
    isCenterCosmeticsRetailPriceScope(
      { store_id: 601, store_name: "常州购物中心" },
      { department_code: "", department_name: "中心一部（化妆）" },
    ),
    true,
  );
  assert.equal(
    isCenterCosmeticsRetailPriceScope(
      { store_id: "3", store_name: "常州新世纪" },
      { department_code: "6030101", department_name: "新世纪一部(化妆)" },
    ),
    false,
  );
  assert.equal(
    isCenterCosmeticsRetailPriceScope(
      { store_id: "1", store_name: "常州购物中心" },
      { department_code: "6010102", department_name: "中心四部(男装)" },
    ),
    false,
  );
});

test("retail price scope requires both store and department", () => {
  assert.equal(isCenterCosmeticsRetailPriceScope(null, { department_code: "6010101" }), false);
  assert.equal(isCenterCosmeticsRetailPriceScope({ store_id: "1" }, null), false);
});

test("sales dashboard wires the conditional retail price column through page and exports", () => {
  const pageSource = readFileSync(new URL("../pages/sales-dashboard.tsx", import.meta.url), "utf8");
  assert.match(pageSource, /isCenterCosmeticsRetailPriceScope/);
  assert.match(pageSource, /priced_sales_amount/);
  assert.match(pageSource, />零售价</);
  assert.match(pageSource, /includePricedSalesAmount/);

  const ticketTabStart = pageSource.indexOf('<TabsContent value="tickets">');
  const ticketTabEnd = pageSource.indexOf("</TabsContent>", ticketTabStart);
  const ticketTabSource = pageSource.slice(ticketTabStart, ticketTabEnd);
  assert.ok(ticketTabStart >= 0 && ticketTabEnd > ticketTabStart);
  assert.doesNotMatch(ticketTabSource, />商品数</);
  assert.doesNotMatch(ticketTabSource, />收银员</);
  assert.match(ticketTabSource, />收银机号<\/TableHead>[\s\S]*>小票号<\/TableHead>/);
  assert.match(ticketTabSource, /row\.cash_register_no/);
  assert.doesNotMatch(ticketTabSource, /ticketsTableTotals\.quantity/);
  assert.match(ticketTabSource, /showPricedSalesAmount \? 14 : 13/);
});
