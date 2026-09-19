import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  buildProductTicketParams,
  getReceiptProductDisplay,
  getDepartmentDrilldownTab,
  getGroupDrilldownTab,
  isCosmeticsRetailPriceScope,
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

test("retail price scope matches Shopping Center and New Century cosmetics", () => {
  assert.equal(
    isCosmeticsRetailPriceScope(
      { store_id: "1", store_name: "常州购物中心" },
      { department_code: "6010101", department_name: "中心一部(化妆)" },
    ),
    true,
  );
  assert.equal(
    isCosmeticsRetailPriceScope(
      { store_id: 601, store_name: "常州购物中心" },
      { department_code: "", department_name: "中心一部（化妆）" },
    ),
    true,
  );
  assert.equal(
    isCosmeticsRetailPriceScope(
      { store_id: "3", store_name: "常州新世纪" },
      { department_code: "6030101", department_name: "新世纪一部(化妆)" },
    ),
    true,
  );
  assert.equal(
    isCosmeticsRetailPriceScope(
      { store_id: "603", store_name: "常州新世纪商城" },
      { department_code: "", department_name: "新世纪一部（化妆）" },
    ),
    true,
  );
  assert.equal(
    isCosmeticsRetailPriceScope(
      { store_id: "1", store_name: "常州购物中心" },
      { department_code: "6010102", department_name: "中心四部(男装)" },
    ),
    false,
  );
});

test("retail price scope requires both store and department", () => {
  assert.equal(isCosmeticsRetailPriceScope(null, { department_code: "6010101" }), false);
  assert.equal(isCosmeticsRetailPriceScope({ store_id: "1" }, null), false);
});

test("sales dashboard wires the conditional retail price column through page and exports", () => {
  const pageSource = readFileSync(new URL("../pages/sales-dashboard.tsx", import.meta.url), "utf8");
  assert.match(pageSource, /isCosmeticsRetailPriceScope/);
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

test("desktop sales dashboard sends rental and back-office exclusion switches through every drilldown", () => {
  const pageSource = readFileSync(new URL("../pages/sales-dashboard.tsx", import.meta.url), "utf8");

  assert.match(pageSource, /排除租赁销售/);
  assert.match(pageSource, /排除后台部门销售/);
  assert.match(pageSource, /aria-pressed=\{excludeRental\}/);
  assert.match(pageSource, /aria-pressed=\{excludeBackofficeDepartments\}/);
  assert.match(pageSource, /exclude_rental: excludeRental/);
  assert.match(pageSource, /exclude_backoffice_departments: excludeBackofficeDepartments/);

  const commonParamsStart = pageSource.indexOf("const commonParams = useMemo");
  const storesQueryStart = pageSource.indexOf("const storesQuery", commonParamsStart);
  const commonParamsSource = pageSource.slice(commonParamsStart, storesQueryStart);
  assert.match(commonParamsSource, /exclude_rental: excludeRental/);
  assert.match(commonParamsSource, /exclude_backoffice_departments: excludeBackofficeDepartments/);

  const ticketsQueryStart = pageSource.indexOf("const ticketsQuery");
  const ticketsQueryEnd = pageSource.indexOf("const ticketDetailQuery", ticketsQueryStart);
  const ticketsQuerySource = pageSource.slice(ticketsQueryStart, ticketsQueryEnd);
  assert.match(ticketsQuerySource, /exclude_rental: excludeRental/);
  assert.match(ticketsQuerySource, /exclude_backoffice_departments: excludeBackofficeDepartments/);

  const analysisStart = pageSource.indexOf("const handleAnalyzeGroups");
  const analysisEnd = pageSource.indexOf("const handleExportTickets", analysisStart);
  const analysisSource = pageSource.slice(analysisStart, analysisEnd);
  assert.match(analysisSource, /exclude_rental: excludeRental/);
  assert.match(analysisSource, /exclude_backoffice_departments: excludeBackofficeDepartments/);
});

test("ticket table paginates by 100 while totals and export cover every filtered ticket", () => {
  const pageSource = readFileSync(new URL("../pages/sales-dashboard.tsx", import.meta.url), "utf8");
  const ticketsQueryStart = pageSource.indexOf("const ticketsQuery");
  const ticketsQueryEnd = pageSource.indexOf("const ticketDetailQuery", ticketsQueryStart);
  const ticketsQuerySource = pageSource.slice(ticketsQueryStart, ticketsQueryEnd);
  const exportStart = pageSource.indexOf("const handleExportTickets");
  const exportEnd = pageSource.indexOf("return (", exportStart);
  const exportSource = pageSource.slice(exportStart, exportEnd);

  assert.ok(exportStart >= 0 && exportEnd > exportStart);
  assert.match(ticketsQuerySource, /limit: TICKET_PAGE_SIZE/);
  assert.match(ticketsQuerySource, /offset: \(ticketPage - 1\) \* TICKET_PAGE_SIZE/);
  assert.match(ticketsQuerySource, /tickets\/summary/);
  assert.match(pageSource, /每页 \{TICKET_PAGE_SIZE\} 张/);
  assert.match(pageSource, /上一页/);
  assert.match(pageSource, /下一页/);
  assert.match(pageSource, /本页合计/);
  assert.match(exportSource, /apiGet<TicketSummaryTotals>/);
  assert.match(exportSource, /apiGet<TicketSummary\[\]>/);
  assert.match(exportSource, /offset < summary\.ticket_count/);
  assert.match(exportSource, /limit: TICKET_EXPORT_BATCH_SIZE/);
  assert.match(exportSource, /offset,/);
  assert.match(exportSource, /\.\.\.selectedProductTicketParams/);
  assert.match(exportSource, /exclude_rental: excludeRental/);
  assert.match(exportSource, /exclude_backoffice_departments: excludeBackofficeDepartments/);
  assert.doesNotMatch(exportSource, /TICKET_EXPORT_MAX_ROWS/);
  assert.doesNotMatch(exportSource, /const rows = ticketsQuery\.data/);
});

test("desktop ticket detail distinguishes loading and failure from real zero values", () => {
  const pageSource = readFileSync(new URL("../pages/sales-dashboard.tsx", import.meta.url), "utf8");
  const dialogStart = pageSource.indexOf('<Dialog open={Boolean(selectedBillno)}');
  const dialogEnd = pageSource.indexOf("</Dialog>", dialogStart);
  const dialogSource = pageSource.slice(dialogStart, dialogEnd);

  assert.ok(dialogStart >= 0 && dialogEnd > dialogStart);
  assert.match(dialogSource, /ticketDetailQuery\.isLoading/);
  assert.match(dialogSource, /ticketDetailQuery\.isError/);
  assert.match(dialogSource, /小票详情加载中/);
  assert.match(dialogSource, /小票详情加载失败/);
});

test("mobile sales dashboard shows current retail price without a prior-period retail field", () => {
  const pageSource = readFileSync(new URL("../pages/mobile-sales-dashboard.tsx", import.meta.url), "utf8");

  assert.match(pageSource, /isCosmeticsRetailPriceScope/);
  assert.match(pageSource, /row\.priced_sales_amount/);
  assert.match(pageSource, />本期零售价</);
  assert.doesNotMatch(pageSource, /同期零售价/);
});

test("mobile sales dashboard excludes rental and back-office sales by default and exposes one add button", () => {
  const pageSource = readFileSync(new URL("../pages/mobile-sales-dashboard.tsx", import.meta.url), "utf8");

  assert.match(pageSource, /useState\(false\).*includeRentalAndBackofficeSales|includeRentalAndBackofficeSales.*useState\(false\)/s);
  assert.match(pageSource, /exclude_rental: !includeRentalAndBackofficeSales/);
  assert.match(pageSource, /exclude_backoffice_departments: !includeRentalAndBackofficeSales/);
  assert.match(pageSource, /level === "stores"[\s\S]*添加租赁\/后台销售/);
  assert.match(pageSource, /aria-pressed=\{includeRentalAndBackofficeSales\}/);

  const ticketsQueryStart = pageSource.indexOf("const ticketsQuery");
  const ticketsQueryEnd = pageSource.indexOf("const ticketDetailQuery", ticketsQueryStart);
  const ticketsQuerySource = pageSource.slice(ticketsQueryStart, ticketsQueryEnd);
  assert.match(ticketsQuerySource, /exclude_rental: !includeRentalAndBackofficeSales/);
  assert.match(ticketsQuerySource, /exclude_backoffice_departments: !includeRentalAndBackofficeSales/);
});
