import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const pagesDir = dirname(fileURLToPath(import.meta.url));
const appSource = readFileSync(join(pagesDir, "../App.tsx"), "utf8");
const homeSource = readFileSync(join(pagesDir, "mobile-home.tsx"), "utf8");
const contractsSource = readFileSync(join(pagesDir, "mobile-contracts.tsx"), "utf8");
const salesSource = readFileSync(join(pagesDir, "mobile-sales-dashboard.tsx"), "utf8");
const inventorySource = readFileSync(join(pagesDir, "mobile-inventory.tsx"), "utf8");
const revenueSource = readFileSync(join(pagesDir, "mobile-revenue-dashboard.tsx"), "utf8");
const receivablesSource = readFileSync(join(pagesDir, "mobile-rental-receivables.tsx"), "utf8");
const couponFollowupsSource = readFileSync(join(pagesDir, "mobile-coupon-followups.tsx"), "utf8");
const supplierPaymentsSource = readFileSync(join(pagesDir, "mobile-supplier-payments.tsx"), "utf8");

test("mobile workbench routes home, sales, contracts, and inventory separately", () => {
  assert.match(appSource, /path="\/mobile\/sales" component=\{MobileSalesDashboardPage\}/);
  assert.match(appSource, /path="\/mobile\/contracts" component=\{MobileContractsPage\}/);
  assert.match(appSource, /path="\/mobile\/inventory" component=\{MobileInventoryPage\}/);
  assert.match(appSource, /path="\/mobile\/revenue" component=\{MobileRevenueDashboardPage\}/);
  assert.match(appSource, /path="\/mobile\/rental-receivables" component=\{MobileRentalReceivablesPage\}/);
  assert.match(appSource, /path="\/mobile\/supplier-payments" component=\{MobileSupplierPaymentsPage\}/);
  assert.match(appSource, /path="\/mobile" component=\{MobileHomePage\}/);
});

test("mobile workbench exposes permission-scoped rental receivables drilldown", () => {
  assert.match(homeSource, /id: "mobile-rental-receivables"/);
  assert.match(homeSource, /path: "\/mobile\/rental-receivables"/);
  assert.match(homeSource, /title: "租赁应收未收"/);
  assert.match(receivablesSource, /canAccessModule\(menuUser, "mobile-rental-receivables"\)/);
  assert.match(receivablesSource, /门店/);
  assert.match(receivablesSource, /部门/);
  assert.match(receivablesSource, /柜组/);
  assert.match(receivablesSource, /金额明细/);
  assert.match(receivablesSource, /\/api\/rental-receivables\/mobile\/drilldown/);
  assert.match(receivablesSource, /\/api\/rental-receivables\/mobile\/bills/);
});

test("mobile receivables keeps headline amounts fully visible on narrow phones", () => {
  const amountLabelIndex = receivablesSource.indexOf(">应收未收</div>");
  const summaryStart = receivablesSource.lastIndexOf('className="mt-3 grid', amountLabelIndex);
  const summaryEnd = receivablesSource.indexOf("已按账号权限过滤", summaryStart);
  const summarySource = receivablesSource.slice(summaryStart, summaryEnd);

  assert.match(summarySource, /grid-cols-2/);
  assert.match(summarySource, /col-span-2/);
  assert.doesNotMatch(summarySource, /truncate text-sm font-bold tabular-nums/);
});

test("mobile receivables shows supplier actual receivable in summary and bill detail", () => {
  assert.match(receivablesSource, /supplierActualReceivableAmount\(summary\?\.receivable_amount, summary\?\.sales_refund_amount\)/);
  assert.match(receivablesSource, /supplierActualReceivableAmount\(detailQuery\.data\.totals\.receivable_amount, detailQuery\.data\.totals\.sales_refund_amount\)/);
  assert.equal((receivablesSource.match(/供应商实际应收金额/g) || []).length, 2);
});

test("mobile receivables uses compact two-line hierarchy cards", () => {
  const hierarchyStart = receivablesSource.indexOf("drillQuery.data.items.map");
  const hierarchyEnd = receivablesSource.indexOf("billsQuery.data.items.map", hierarchyStart);
  const hierarchySource = receivablesSource.slice(hierarchyStart, hierarchyEnd);

  assert.match(receivablesSource, /<div className="space-y-1">/);
  assert.match(hierarchySource, /rounded-2xl bg-white px-3 py-2/);
  assert.match(hierarchySource, /\{item\.bill_count\} 张/);
  assert.doesNotMatch(hierarchySource, /w-full rounded-3xl bg-white p-4 text-left/);
});

test("mobile receivable detail rows only show name, period, and balance amount", () => {
  const detailsStart = receivablesSource.indexOf("visibleDetails.map");
  const detailsEnd = receivablesSource.indexOf("</SheetContent>", detailsStart);
  const detailsSource = receivablesSource.slice(detailsStart, detailsEnd);

  assert.match(detailsSource, /item\.item_name/);
  assert.match(detailsSource, /shortDate\(item\.period_from\)/);
  assert.match(detailsSource, /shortDate\(item\.period_to\)/);
  assert.match(detailsSource, /money\(item\.balance_amount\)/);
  assert.doesNotMatch(detailsSource, /项目金额|已收款|抵扣|明细余额/);
  assert.doesNotMatch(detailsSource, /item\.item_code|item\.finance_month/);
});

test("mobile receivable detail sheet has an opaque fixed header and its own scroll area", () => {
  const sheetStart = receivablesSource.indexOf('<Sheet open={Boolean(selectedBill)}');
  const sheetEnd = receivablesSource.indexOf("</Sheet>", sheetStart);
  const sheetSource = receivablesSource.slice(sheetStart, sheetEnd);

  assert.match(sheetSource, /SheetContent[^>]+bg-white[^>]+overflow-hidden/);
  assert.match(sheetSource, /SheetHeader className="border-b/);
  assert.match(sheetSource, /h-\[calc\(92dvh-5\.5rem\)\] overflow-y-auto/);
});

test("mobile workbench exposes the revenue dashboard as the fourth app", () => {
  const inventoryIndex = homeSource.indexOf('id: "mobile-inventory"');
  const revenueIndex = homeSource.indexOf('id: "mobile-revenue-dashboard"');
  assert.ok(inventoryIndex >= 0);
  assert.ok(revenueIndex > inventoryIndex);
  assert.match(homeSource, /path: "\/mobile\/revenue"/);
  assert.match(homeSource, /title: "收益"/);
  assert.match(revenueSource, /canAccessModule\(menuUser, "mobile-revenue-dashboard"\)/);
});

test("mobile workbench lists sales first and contracts second with mobile permission ids", () => {
  const salesIndex = homeSource.indexOf('id: "mobile-sales-dashboard"');
  const contractsIndex = homeSource.indexOf('id: "mobile-contracts"');
  assert.ok(salesIndex >= 0);
  assert.ok(contractsIndex > salesIndex);
  assert.match(homeSource, /canAccessModule\(menuUser, module\.id\)/);
  assert.match(homeSource, /path: "\/mobile\/sales"/);
  assert.match(homeSource, /path: "\/mobile\/contracts"/);
  assert.match(salesSource, /canAccessModule\(menuUser, "mobile-sales-dashboard"\)/);
  assert.match(contractsSource, /canAccessModule\(menuUser, "mobile-contracts"\)/);
});

test("mobile workbench exposes inventory through its mobile module permission", () => {
  assert.match(homeSource, /id: "mobile-inventory"/);
  assert.match(homeSource, /path: "\/mobile\/inventory"/);
  assert.match(homeSource, /title: "库存查询"/);
  assert.match(inventorySource, /canAccessModule\(menuUser, "mobile-inventory"\)/);
});

test("mobile workbench exposes the C coupon follow-up module", () => {
  assert.match(homeSource, /id: "mobile-coupon-followups"/);
  assert.match(homeSource, /path: "\/mobile\/coupon-followups"/);
  assert.match(appSource, /MobileCouponFollowupsPage/);
  assert.match(appSource, /path="\/mobile\/coupon-followups"/);
  assert.match(couponFollowupsSource, /canAccessModule\(menuUser, "mobile-coupon-followups"\)/);
});

test("mobile workbench exposes query-business-scope supplier payments", () => {
  assert.match(homeSource, /id: "mobile-supplier-payments"/);
  assert.match(homeSource, /path: "\/mobile\/supplier-payments"/);
  assert.match(homeSource, /title: "供应商付款单"/);
  assert.match(supplierPaymentsSource, /canAccessModule\(menuUser, "mobile-supplier-payments"\)/);
  assert.match(supplierPaymentsSource, /\/api\/erp-settlements\/mobile\/supplier-payments/);
  assert.match(supplierPaymentsSource, /按查询业务范围显示/);
  assert.match(supplierPaymentsSource, /跨范围单据仅计可见部分/);
  assert.doesNotMatch(supplierPaymentsSource, /品类主管绩效/);
  assert.match(supplierPaymentsSource, /实际应付（当前可见）/);
});

test("mobile supplier payment search separates exact supplier code from fuzzy name", () => {
  assert.match(supplierPaymentsSource, /supplier_code/);
  assert.match(supplierPaymentsSource, /supplier_name/);
  assert.match(supplierPaymentsSource, /\/\^\\d\+\$\//);
  assert.match(supplierPaymentsSource, /供应商号（精确）或名称（模糊）/);
});

test("mobile supplier payment headline amounts stay fully visible", () => {
  const summaryStart = supplierPaymentsSource.indexOf("function PaymentStageCard(");
  const summaryEnd = supplierPaymentsSource.indexOf("function PaymentDetail(", summaryStart);
  const summarySource = supplierPaymentsSource.slice(summaryStart, summaryEnd);

  assert.match(summarySource, /w-full/);
  assert.match(summarySource, /flex-wrap/);
  assert.match(summarySource, /whitespace-nowrap font-mono/);
  assert.match(summarySource, /text-lg/);
  assert.doesNotMatch(summarySource, /truncate font-mono/);
});

test("mobile supplier payment detail shows income, invoice, payable, and expense evidence", () => {
  assert.match(supplierPaymentsSource, /实际应付（当前可见）/);
  assert.match(supplierPaymentsSource, /销售收入/);
  assert.match(supplierPaymentsSource, /应开票金额/);
  assert.match(supplierPaymentsSource, /票减/);
  assert.match(supplierPaymentsSource, /费用/);
  assert.match(supplierPaymentsSource, /收入构成/);
  assert.match(supplierPaymentsSource, /票减明细/);
  assert.match(supplierPaymentsSource, /费用明细/);
  assert.match(supplierPaymentsSource, /charge\.expense_name_display/);
  assert.match(supplierPaymentsSource, /charge\.sscmoney/);
  assert.match(supplierPaymentsSource, /付款汇总存在历史差异/);
  assert.match(supplierPaymentsSource, /页面以付款汇总金额为准/);
  assert.match(supplierPaymentsSource, /仅显示当前账号查询业务范围/);
});

test("mobile workbench uses a four-column phone app grid", () => {
  assert.match(homeSource, /grid grid-cols-4/);
  assert.match(homeSource, /accessibleModules\.map/);
  assert.match(homeSource, /aria-label=\{`\$\{module\.title\}：\$\{module\.description\}`\}/);
  assert.doesNotMatch(homeSource, /ChevronRight/);
});

test("mobile inventory supports manual entry and camera scanning", () => {
  assert.match(inventorySource, /placeholder="请输入或扫描商品条码"/);
  assert.match(inventorySource, /手工输入商品条码/);
  assert.match(inventorySource, /开始扫码/);
  assert.match(inventorySource, /BrowserMultiFormatReader/);
  assert.match(inventorySource, /tryWeComBarcodeScan/);
  assert.match(inventorySource, /exact_code/);
});

test("mobile inventory separates product, supplier, and group lookup into three tabs", () => {
  assert.match(inventorySource, /<TabsTrigger value="product"[^>]*>单品查询<\/TabsTrigger>/);
  assert.match(inventorySource, /<TabsTrigger value="supplier"[^>]*>供应商查询<\/TabsTrigger>/);
  assert.match(inventorySource, /<TabsTrigger value="group"[^>]*>柜组查询<\/TabsTrigger>/);
  assert.match(inventorySource, /placeholder="请输入供应商名称或编码"/);
  assert.match(inventorySource, /supplier: submittedSupplier/);
  assert.match(inventorySource, /\/api\/sales\/reports\/inventory-detail/);
});

test("supplier inventory groups rows and can load every result page", () => {
  assert.match(inventorySource, /new Map<string, \{ supplier: string; rows: InventoryRow\[\]; quantity: number \}>/);
  assert.match(inventorySource, /supplierQuery\.fetchNextPage\(\)/);
  assert.match(inventorySource, /已显示全部库存明细/);
  assert.match(inventorySource, /已显示 \{supplierRows\.length\} \/ \{Number\(supplierSummary\?\.total_count/);
});

test("group inventory searches scoped options before exact group lookup", () => {
  assert.match(inventorySource, /field: "group"/);
  assert.match(inventorySource, /\/api\/sales\/reports\/inventory-detail\/options/);
  assert.match(inventorySource, /setSelectedGroup\(option\)/);
  assert.match(inventorySource, /请先从匹配结果中选择一个柜组/);
  assert.match(inventorySource, /exact_group: submittedGroup\?\.value/);
  assert.match(inventorySource, /柜组候选和库存结果均受当前账号数据范围控制/);
});

test("group inventory can load every result page", () => {
  assert.match(inventorySource, /groupQuery\.fetchNextPage\(\)/);
  assert.match(inventorySource, /已显示 \{groupRows\.length\} \/ \{Number\(groupSummary\?\.total_count/);
});

test("group inventory shows total retail value and uses compact detail rows", () => {
  const groupResultsStart = inventorySource.indexOf("groupSummary?.inventory_quantity");
  const groupResultsEnd = inventorySource.indexOf("groupQuery.hasNextPage", groupResultsStart);
  const groupResults = inventorySource.slice(groupResultsStart, groupResultsEnd);

  assert.match(groupResults, /总库存金额/);
  assert.match(groupResults, /按零售价合计/);
  assert.match(groupResults, /groupSummary\?\.retail_amount/);
  assert.match(groupResults, /space-y-1 border-b bg-teal-50 px-4 py-3/);
  assert.match(groupResults, /className="px-3 py-2\.5"/);
  assert.doesNotMatch(groupResults, /className="space-y-3 p-4"/);
});

test("group inventory groups products by supplier without repeating location hierarchy", () => {
  assert.match(inventorySource, /const groupSupplierGroups = useMemo/);
  assert.match(inventorySource, /groupSupplierGroups\.map\(\(supplierGroup\)/);
  assert.match(inventorySource, /售价：\{formatSellingCalculation\(row\)\}/);
  assert.match(inventorySource, /unitPrice \* quantity/);

  const groupResultsStart = inventorySource.indexOf("groupSupplierGroups.map");
  const groupResultsEnd = inventorySource.indexOf("groupQuery.hasNextPage", groupResultsStart);
  const groupResults = inventorySource.slice(groupResultsStart, groupResultsEnd);
  assert.doesNotMatch(groupResults, /row\.store_display/);
  assert.doesNotMatch(groupResults, /row\.floor_display/);
  assert.doesNotMatch(groupResults, /row\.area_display/);
  assert.doesNotMatch(groupResults, /row\.group_display/);
  assert.doesNotMatch(groupResults, /供应商：\{row\.supplier_display/);
});

test("mobile contract queries remain disabled without mobile contract access", () => {
  assert.match(contractsSource, /canAccessModule\(menuUser, "mobile-contracts"\)/);
  assert.match(contractsSource, /enabled: hasAccess/);
  assert.match(contractsSource, /useContractFilterOptions\(hasAccess\)/);
  assert.match(contractsSource, /useContractDetail\(selectedContractNo, hasAccess\)/);
});

test("mobile contracts replace the status filter with a store filter", () => {
  assert.match(contractsSource, /<Label[^>]*>门店<\/Label>/);
  assert.match(contractsSource, /value=\{storeCode\}/);
  assert.match(contractsSource, /setStoreCode\(value\)/);
  assert.match(contractsSource, /<SelectItem value="ALL">全部门店<\/SelectItem>/);
  assert.match(contractsSource, /storeCode,/);
});

test("mobile contract detail shows contract deduction rates", () => {
  assert.match(contractsSource, /合同扣点/);
  for (let index = 1; index <= 5; index += 1) {
    assert.match(contractsSource, new RegExp(`row\\.cmfnum${index}`));
  }
});

test("mobile contracts prefer the withdrawal date when displaying the contract end date", () => {
  assert.match(contractsSource, /getContractDisplayEndDate\(item\)/);
  assert.match(
    contractsSource,
    /getContractDisplayEndDate\(contractDetailQuery\.data\.contmain\)/,
  );
});

test("mobile fee terms appear before bottom terms and show once or each-time settlement", () => {
  const feeIndex = contractsSource.indexOf('title="收费条款"');
  const bottomIndex = contractsSource.indexOf('title="保底条款"');
  assert.ok(feeIndex >= 0, "fee section should exist");
  assert.ok(bottomIndex > feeIndex, "fee section should be above bottom section");
  assert.match(contractsSource, /formatSettlementMethod\(row\.cscismcjs\)/);
  assert.match(contractsSource, /if \(normalized === "0"\) return "一次";/);
  assert.match(contractsSource, /if \(normalized === "1"\) return "每次";/);
});

test("sales and contracts both provide a route back to the mobile workbench", () => {
  assert.match(salesSource, /setLocation\("\/mobile"\)/);
  assert.match(contractsSource, /setLocation\("\/mobile"\)/);
});

test("mobile sales compares current sales and profit with the same period", () => {
  assert.match(salesSource, /same_period_effective_sales\?: number/);
  assert.match(salesSource, /same_period_net_profit\?: number/);
  assert.match(salesSource, /priorLabel="同期销售"/);
  assert.match(salesSource, /priorLabel="同期毛利"/);
  assert.match(salesSource, /tenThousands\(priorSales\) : currency\(priorSales\)/);
  assert.match(salesSource, /tenThousands\(priorProfit\) : currency\(priorProfit\)/);
  assert.match(salesSource, /priorProfit=\{row\.same_period_net_profit\}/);
});

test("mobile sales overview keeps yoy metrics inside the amount cards", () => {
  const overviewStart = salesSource.indexOf('<div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-sm">');
  const overviewEnd = salesSource.indexOf("<section>", overviewStart);
  const overviewSource = salesSource.slice(overviewStart, overviewEnd);

  assert.match(overviewSource, /yoyLabel="销售同比"/);
  assert.match(overviewSource, /yoyLabel="毛利同比"/);
  assert.match(overviewSource, /prior=\{totals\.priorSales\}/);
  assert.match(overviewSource, /prior=\{totals\.priorProfit\}/);
  assert.doesNotMatch(overviewSource, /小票数|柜组数/);
  assert.doesNotMatch(overviewSource, /border-t border-slate-100 bg-slate-50\/70/);
});

test("mobile sales overview gives the full amount its own row", () => {
  const metricStart = salesSource.indexOf("function OverviewMetric");
  const metricEnd = salesSource.indexOf("function EmptyState", metricStart);
  const metricSource = salesSource.slice(metricStart, metricEnd);

  assert.match(metricSource, /whitespace-nowrap text-lg/);
  assert.doesNotMatch(metricSource, /truncate text-lg/);
  assert.match(metricSource, /grid grid-cols-2 gap-2/);
});

test("mobile sales store cards use the compact row layout", () => {
  const storesStart = salesSource.indexOf('(storesQuery.data ?? []).map');
  const storesEnd = salesSource.indexOf('(departmentsQuery.data ?? []).map', storesStart);
  const storesSource = salesSource.slice(storesStart, storesEnd);

  assert.match(storesSource, /<SummaryRow[\s\S]*?dense[\s\S]*?onClick=/);
});

test("mobile sales keeps the duplicate date row collapsed until requested", () => {
  assert.match(salesSource, /\{dateFiltersOpen \? <Card className="rounded-2xl border-0 shadow-sm">/);
  assert.doesNotMatch(salesSource, /level !== "departments" \|\| dateFiltersOpen/);
});

test("mobile sales cards show three amount panels with current and prior values stacked", () => {
  const rowStart = salesSource.indexOf("function SummaryRow");
  const rowEnd = salesSource.indexOf("function ProductRow", rowStart);
  const rowSource = salesSource.slice(rowStart, rowEnd);

  assert.match(salesSource, /const tenThousands =/);
  assert.match(rowSource, /grid grid-cols-3 gap-1\.5/);
  assert.match(rowSource, /销售收入[\s\S]*?本期[\s\S]*?tenThousands\(sales\)[\s\S]*?同期[\s\S]*?tenThousands\(priorSales\)/);
  assert.match(rowSource, /净毛利[\s\S]*?本期[\s\S]*?tenThousands\(profit\)[\s\S]*?同期[\s\S]*?tenThousands\(priorProfit\)/);
  assert.match(rowSource, /本财务月销售额[\s\S]*?本期[\s\S]*?financialMonthSales\?\.effective_sales[\s\S]*?同期[\s\S]*?financialMonthSales\?\.same_period_effective_sales/);
  assert.match(rowSource, /if \(value == null\) return "—"/);
  assert.match(rowSource, /text-\[11px\] font-semibold[\s\S]*?tenThousands\(sales\)/);
  assert.match(rowSource, /dense \? "text-\[10px\]" : "text-\[9px\]"/);
  assert.match(rowSource, /销售收入[\s\S]*?currency\(sales\)/);
  assert.match(rowSource, /净毛利[\s\S]*?currency\(profit\)/);
});

test("mobile ticket detail renders POS receipt field names", () => {
  assert.match(salesSource, /getReceiptProductDisplay/);
  assert.match(salesSource, /item\.sl\s*\?\?\s*item\.quantity/);
  assert.match(salesSource, /item\.hjje\s*\?\?\s*item\.effective_sales/);
  assert.match(salesSource, /payment\.payname\s*\|\|\s*payment\.paycode/);
  assert.match(salesSource, /payment\.je/);
});
