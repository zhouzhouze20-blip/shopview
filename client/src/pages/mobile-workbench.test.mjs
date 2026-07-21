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

test("mobile workbench routes home, sales, contracts, and inventory separately", () => {
  assert.match(appSource, /path="\/mobile\/sales" component=\{MobileSalesDashboardPage\}/);
  assert.match(appSource, /path="\/mobile\/contracts" component=\{MobileContractsPage\}/);
  assert.match(appSource, /path="\/mobile\/inventory" component=\{MobileInventoryPage\}/);
  assert.match(appSource, /path="\/mobile" component=\{MobileHomePage\}/);
});

test("mobile workbench lists sales first and contracts second with desktop permission ids", () => {
  const salesIndex = homeSource.indexOf('id: "sales-dashboard"');
  const contractsIndex = homeSource.indexOf('id: "contracts"');
  assert.ok(salesIndex >= 0);
  assert.ok(contractsIndex > salesIndex);
  assert.match(homeSource, /canAccessModule\(menuUser, module\.id\)/);
  assert.match(homeSource, /path: "\/mobile\/sales"/);
  assert.match(homeSource, /path: "\/mobile\/contracts"/);
});

test("mobile workbench exposes inventory only through the existing inventory permission", () => {
  assert.match(homeSource, /id: "inventory-detail"/);
  assert.match(homeSource, /path: "\/mobile\/inventory"/);
  assert.match(homeSource, /title: "库存查询"/);
  assert.match(inventorySource, /canAccessModule\(menuUser, "inventory-detail"\)/);
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

test("mobile contract queries remain disabled without contract permission", () => {
  assert.match(contractsSource, /canAccessModule\(menuUser, "contracts"\)/);
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

test("mobile ticket detail renders POS receipt field names", () => {
  assert.match(salesSource, /getReceiptProductDisplay/);
  assert.match(salesSource, /item\.sl\s*\?\?\s*item\.quantity/);
  assert.match(salesSource, /item\.hjje\s*\?\?\s*item\.effective_sales/);
  assert.match(salesSource, /payment\.payname\s*\|\|\s*payment\.paycode/);
  assert.match(salesSource, /payment\.je/);
});
