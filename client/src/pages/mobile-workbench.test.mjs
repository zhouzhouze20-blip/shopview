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

test("mobile workbench routes home, sales, contracts, and inventory separately", () => {
  assert.match(appSource, /path="\/mobile\/sales" component=\{MobileSalesDashboardPage\}/);
  assert.match(appSource, /path="\/mobile\/contracts" component=\{MobileContractsPage\}/);
  assert.match(appSource, /path="\/mobile\/inventory" component=\{MobileInventoryPage\}/);
  assert.match(appSource, /path="\/mobile\/revenue" component=\{MobileRevenueDashboardPage\}/);
  assert.match(appSource, /path="\/mobile" component=\{MobileHomePage\}/);
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
  assert.match(salesSource, /同期销售 <span/);
  assert.match(salesSource, /同期毛利 <span/);
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

test("compact sales cards place current and prior amounts side by side in ten-thousands", () => {
  const rowStart = salesSource.indexOf("function SummaryRow");
  const rowEnd = salesSource.indexOf("function ProductRow", rowStart);
  const rowSource = salesSource.slice(rowStart, rowEnd);

  assert.match(salesSource, /const tenThousands =/);
  assert.match(rowSource, /grid grid-cols-2 gap-2[\s\S]*?本期[\s\S]*?tenThousands\(sales\)[\s\S]*?同期[\s\S]*?tenThousands\(priorSales\)/);
  assert.match(rowSource, /grid grid-cols-2 gap-2[\s\S]*?本期[\s\S]*?tenThousands\(profit\)[\s\S]*?同期[\s\S]*?tenThousands\(priorProfit\)/);
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
