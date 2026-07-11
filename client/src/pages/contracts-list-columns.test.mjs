import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(__dirname, "contracts.tsx"), "utf8");

function contractListHeaderSource() {
  const titleIndex = source.indexOf('<CardTitle className="text-lg">合同列表</CardTitle>');
  assert.notEqual(titleIndex, -1, "contract list title should exist");
  const headerStart = source.indexOf("<TableHeader>", titleIndex);
  const headerEnd = source.indexOf("</TableHeader>", headerStart);
  assert.notEqual(headerStart, -1, "contract list table header should exist");
  assert.notEqual(headerEnd, -1, "contract list table header should close");
  return source.slice(headerStart, headerEnd);
}

function tableHeadLabels(headerSource) {
  return Array.from(headerSource.matchAll(/<TableHead[^>]*>([^<]+)<\/TableHead>/g), (match) => match[1].trim());
}

test("contract list table starts with department contract number date range and counter number", () => {
  const labels = tableHeadLabels(contractListHeaderSource());

  assert.deepEqual(labels.slice(0, 9), [
    "部门",
    "合同编号",
    "开始日期",
    "结束日期",
    "供应商",
    "经营方式",
    "柜位号",
    "柜组",
    "月目标销售额",
  ]);
  assert.equal(labels.includes("状态"), false);
  assert.equal(labels.includes("合同类型"), false);
  assert.equal(labels.includes("品牌"), false);
  assert.equal(labels.includes("主题"), false);
});

test("contract list dates stay on one line and expired contracts are red", () => {
  assert.match(
    source,
    /<TableRow key=\{item\.cmcontno\} className=\{[^}]*isPastDate\(item\.cmlapdate\)[^}]*text-red-600/s,
  );
  assert.match(source, /<TableCell className="whitespace-nowrap">\{fmtDate\(item\.cmeffdate\)\}<\/TableCell>/);
  assert.match(source, /<TableCell className="whitespace-nowrap">\{fmtDate\(item\.cmlapdate\)\}<\/TableCell>/);
});

test("contract detail dialog omits the main contract info card", () => {
  assert.equal(source.includes("<CardTitle>主合同信息</CardTitle>"), false);
});

test("contract detail dialog keeps a fixed size and compact single-line detail rows", () => {
  assert.match(source, /<DialogContent className="[^"]*h-\[92vh\][^"]*w-\[94vw\][^"]*max-w-\[94vw\]/);
  assert.match(source, /<TableHead key=\{column\.header\} className=\{cn\("px-3 py-2 whitespace-nowrap"/);
  assert.match(source, /<TableCell key=\{column\.header\} className=\{cn\("px-3 py-2 align-middle whitespace-nowrap"/);
  assert.match(source, /function renderInlineInfo\(code\?: string \| null, name\?: string \| null\)/);
  assert.match(source, /\{ header: "柜组", render: \(row\) => renderInlineInfo\(row\.cmfmfid, row\.group_name\) \}/);
});

test("contbd detail table places bottom amount before profit and completed amount after profit", () => {
  const contbdIndex = source.indexOf('<TabsContent value="contbd">');
  assert.notEqual(contbdIndex, -1, "contbd tab should exist");
  const contbdEnd = source.indexOf("</TabsContent>", contbdIndex);
  const contbdSource = source.slice(contbdIndex, contbdEnd);
  const bottomAmountIndex = contbdSource.indexOf('{ header: "保底金额"');
  const bottomProfitIndex = contbdSource.indexOf('{ header: "保底毛利"');
  const completedAmountIndex = contbdSource.indexOf('{ header: "完成金额"');

  assert.notEqual(bottomAmountIndex, -1, "bottom amount column should exist");
  assert.notEqual(bottomProfitIndex, -1, "bottom profit column should exist");
  assert.notEqual(completedAmountIndex, -1, "completed amount column should exist");
  assert.ok(bottomAmountIndex < bottomProfitIndex, "bottom amount should be before bottom profit");
  assert.ok(completedAmountIndex > bottomProfitIndex, "completed amount should be after bottom profit");
});

test("contcyclist detail table shows charge item name after item number", () => {
  const contcyclistIndex = source.indexOf('<TabsContent value="contcyclist">');
  assert.notEqual(contcyclistIndex, -1, "contcyclist tab should exist");
  const contcyclistEnd = source.indexOf("</TabsContent>", contcyclistIndex);
  const contcyclistSource = source.slice(contcyclistIndex, contcyclistEnd);
  const itemNumberIndex = contcyclistSource.indexOf('{ header: "项目编号"');
  const itemNameIndex = contcyclistSource.indexOf('{ header: "收费项目名称"');
  const groupIndex = contcyclistSource.indexOf('{ header: "柜组"');

  assert.notEqual(itemNumberIndex, -1, "item number column should exist");
  assert.notEqual(itemNameIndex, -1, "charge item name column should exist");
  assert.notEqual(groupIndex, -1, "group column should exist");
  assert.ok(itemNumberIndex < itemNameIndex, "charge item name should be after item number");
  assert.ok(itemNameIndex < groupIndex, "charge item name should be before group");
  assert.match(contcyclistSource, /row\.cclitemname/);
});

test("supplier charge detail maps settlement method codes and formats small indicators as percentages", () => {
  assert.match(source, /if \(normalized === "0"\) return "一次";/);
  assert.match(source, /if \(normalized === "1"\) return "每次";/);
  assert.match(source, /function fmtChargeIndicator\(value\?: number \| null\)/);
  assert.match(source, /\{ header: "指标", render: \(row\) => fmtChargeIndicator\(row\.cscvalue\), className: "whitespace-nowrap" \}/);
});

test("contract filters use department selector instead of group code text input", () => {
  assert.equal(source.includes("<Label className=\"text-xs\">柜组编码</Label>"), false);
  assert.match(source, /<Label className="text-xs">部门<\/Label>/);
  assert.match(source, /setListDepartmentCode/);
  assert.match(source, /departmentCode: listDepartmentCode/);
});
