import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  assertSupplierPptTemplateImageResponse,
  buildSupplierPptNarrative,
  buildSupplierPresentation,
  resolveSupplierPptTemplateImageUrl,
  supplierPptTemplateBaseUrl,
  supplierPptTemplateDirectory,
  supplierPptTemplateVariant,
} from "./export-brand-member-ppt.ts";

const level = (levelCode, levelLabel, buyerCount, salesRevenue, frequency) => ({
  level_code: levelCode,
  level_label: levelLabel,
  buyer_count: buyerCount,
  sales_revenue: salesRevenue,
  ticket_count: buyerCount,
  buyer_share: buyerCount / 82,
  sales_share: salesRevenue / 51823,
  spend_per_buyer: buyerCount ? salesRevenue / buyerCount : 0,
  purchase_frequency: frequency,
  average_ticket_value: buyerCount ? salesRevenue / buyerCount : 0,
});

const current = {
  period: { start_date: "2026-06-01", end_date: "2026-06-30" },
  summary: {
    sales_revenue: 51823,
    positive_revenue: 51823,
    refund_revenue: 0,
    ticket_count: 86,
    member_buyer_count: 82,
    member_sales_revenue: 51583,
    member_ticket_count: 86,
    nonmember_sales_revenue: 240,
    refund_only_member_sales_revenue: 0,
    spend_per_buyer: 629,
    purchase_frequency: 1.05,
    member_sales_quantity: 112,
    items_per_ticket: 1.3,
    average_item_price: 460.56,
    department_rank: 15,
    department_group_count: 21,
    old_customer_repurchase_rate: 0.039948,
  },
  segments: [
    { code: "brand_returning", label: "品牌老客", buyer_count: 62, sales_revenue: 40046, ticket_count: 64, buyer_share: 62 / 82, sales_share: 40046 / 51583 },
    { code: "same_department_inflow", label: "同部门流入", buyer_count: 3, sales_revenue: 1817, ticket_count: 3, buyer_share: 3 / 82, sales_share: 1817 / 51583 },
    { code: "cross_department_inflow", label: "跨部门流入", buyer_count: 4, sales_revenue: 2045, ticket_count: 4, buyer_share: 4 / 82, sales_share: 2045 / 51583 },
    { code: "external_new", label: "外部招新", buyer_count: 13, sales_revenue: 7675, ticket_count: 15, buyer_share: 13 / 82, sales_share: 7675 / 51583 },
  ],
  member_level_consumption: [
    level("01", "银星会员", 72, 43820, 1.03),
    level("02", "金星会员", 6, 5702, 1.33),
    level("03", "黑金会员", 3, 1921, 1),
    level("04", "黑钻会员", 1, 140, 1),
  ],
  purchase_frequency_analysis: [
    { code: "single_purchase", label: "一次客", buyer_count: 78, buyer_share: 78 / 82, sales_revenue: 46800, sales_share: 46800 / 51583, ticket_count: 78, sales_quantity: 98, spend_per_buyer: 600, purchase_frequency: 1, average_ticket_value: 600, items_per_ticket: 1.26, average_item_price: 477.55 },
    { code: "repeat_purchase", label: "多次客", buyer_count: 4, buyer_share: 4 / 82, sales_revenue: 4783, sales_share: 4783 / 51583, ticket_count: 8, sales_quantity: 14, spend_per_buyer: 1195.75, purchase_frequency: 2, average_ticket_value: 597.88, items_per_ticket: 1.75, average_item_price: 341.64 },
  ],
  old_customer_funnel: {
    historical_target_member_count: 1552,
    store_visit_count: 205,
    department_visit_count: 92,
    target_repurchase_count: 62,
  },
  inflow_sources: [],
};

const prior = {
  ...current,
  period: { start_date: "2025-06-01", end_date: "2025-06-30" },
  summary: { ...current.summary, sales_revenue: 101886, member_buyer_count: 133, spend_per_buyer: 711, department_rank: 11, department_group_count: 22 },
  segments: current.segments.map((row) => ({
    ...row,
    buyer_count: row.code === "brand_returning" ? 45 : row.code === "external_new" ? 66 : row.buyer_count,
  })),
  old_customer_funnel: { historical_target_member_count: 738, store_visit_count: 113, department_visit_count: 57, target_repurchase_count: 45 },
};

const report = {
  scope: { store_code: "603", target_group_code: "6030101033", competitor_group_codes: [] },
  target: {
    group_code: "6030101033",
    group_name: "Aupres欧珀莱厅",
    department_code: "6030101",
    department_name: "新世纪一部(化妆)",
    current,
    prior,
  },
  comparison: {
    sales_revenue: { current: 51823, prior: 101886, change: -50063, change_rate: -0.49136 },
    member_buyer_count: { current: 82, prior: 133, change: -51, change_rate: -0.38346 },
    spend_per_buyer: { current: 629, prior: 711, change: -82, change_rate: -0.11475 },
    purchase_frequency: { current: 1.05, prior: 1.1, change: -0.05, change_rate: -0.0446 },
    old_customer_repurchase_rate: { current: 0.039948, prior: 0.060976, change: -0.021028, change_rate: -0.34485 },
  },
  competitors: [],
  definitions: {},
};

const imageData = async (fileName, templateDirectory = "brand-member-ppt") => {
  const bytes = await readFile(new URL(`../../public/${templateDirectory}/${fileName}`, import.meta.url));
  return `data:image/png;base64,${bytes.toString("base64")}`;
};

test("PPT narrative follows the report metrics without fixed Aupres copy", () => {
  const narrative = buildSupplierPptNarrative(report);
  assert.match(narrative.overviewTitle, /销售承压/);
  assert.match(narrative.overviewSummary, /下降49\.1%/);
  assert.match(narrative.segmentSummary, /品牌老客62人/);
  assert.match(narrative.segmentSummary, /一次客78人、多次客4人/);
  assert.match(narrative.segmentSummary, /会员客件数1\.30件/);
  assert.match(narrative.frequencySummary, /一次客78人/);
  assert.match(narrative.frequencySummary, /多次客4人/);
  assert.equal(narrative.actionItems[0].title, "盘活1,552名历史品牌会员");
  assert.match(narrative.actionItems[1].title, /金星会员/);
});

test("supplier PPT builds five widescreen slides with embedded template images", async () => {
  const images = {
    overview: await imageData("01-overview.png"),
    segments: await imageData("02-segments.png"),
    loyalty: await imageData("03-loyalty.png"),
    actions: await imageData("04-actions.png"),
    frequency: await imageData("05-frequency-basket.png"),
  };
  const presentation = buildSupplierPresentation(report, "常州新世纪商城", images, "销售与会员规模承压，建议优先恢复会员到店与购买转化。");
  assert.equal(presentation._slides.length, 5);
  const output = await presentation.write({ outputType: "uint8array", compression: true });
  assert.ok(output instanceof Uint8Array);
  assert.ok(output.byteLength > 1_000_000);
});

test("PPT template images use the deployed static base path and reject HTML fallbacks", () => {
  assert.equal(supplierPptTemplateBaseUrl(true), "/static/");
  assert.equal(supplierPptTemplateBaseUrl(false), "/");
  assert.equal(
    resolveSupplierPptTemplateImageUrl(
      "01-overview.png",
      "https://shopview.example",
      supplierPptTemplateBaseUrl(true),
    ).href,
    "https://shopview.example/static/brand-member-ppt/01-overview.png",
  );
  assert.equal(supplierPptTemplateDirectory("womenswear"), "brand-member-ppt-womenswear");
  assert.equal(supplierPptTemplateDirectory("menswear"), "brand-member-ppt-menswear");
  assert.equal(supplierPptTemplateDirectory("luxury"), "brand-member-ppt-luxury");
  assert.equal(
    resolveSupplierPptTemplateImageUrl(
      "01-overview.png",
      "https://shopview.example",
      supplierPptTemplateBaseUrl(true),
      "womenswear",
    ).href,
    "https://shopview.example/static/brand-member-ppt-womenswear/01-overview.png",
  );
  assert.doesNotThrow(() => assertSupplierPptTemplateImageResponse(
    new Response("png", { headers: { "content-type": "image/png" } }),
    "01-overview.png",
  ));
  assert.throws(
    () => assertSupplierPptTemplateImageResponse(
      new Response("<!DOCTYPE html>", { headers: { "content-type": "text/html; charset=utf-8" } }),
      "01-overview.png",
    ),
    /PPT模板图片格式错误：01-overview\.png/,
  );
});

test("configured shopping center and new century departments use the womenswear PPT template", () => {
  const departmentReport = (departmentName) => ({
    ...report,
    target: { ...report.target, department_name: departmentName },
  });

  assert.equal(supplierPptTemplateVariant(departmentReport("购物中心二部"), "常州购物中心"), "womenswear");
  assert.equal(supplierPptTemplateVariant(departmentReport("购物中心三部（女装）"), "常州购物中心"), "womenswear");
  assert.equal(supplierPptTemplateVariant(departmentReport("新世纪二部"), "常州新世纪商城"), "womenswear");
  assert.equal(supplierPptTemplateVariant(departmentReport("新世纪三部"), "常州新世纪商城"), "womenswear");
  assert.equal(supplierPptTemplateVariant(departmentReport("新世纪四部（女装）"), "常州新世纪商城"), "womenswear");
});

test("shopping center department four and new century department six use the menswear PPT template", () => {
  const departmentReport = (departmentName) => ({
    ...report,
    target: { ...report.target, department_name: departmentName },
  });

  assert.equal(supplierPptTemplateVariant(departmentReport("购物中心四部"), "常州购物中心"), "menswear");
  assert.equal(supplierPptTemplateVariant(departmentReport("新世纪六部（男装）"), "常州新世纪商城"), "menswear");
  assert.equal(supplierPptTemplateVariant(departmentReport("购物中心六部"), "常州购物中心"), "default");
  assert.equal(supplierPptTemplateVariant(departmentReport("新世纪五部"), "常州新世纪商城"), "default");
});

test("shopping center and new century department one use the luxury PPT template", () => {
  const departmentReport = (departmentName) => ({
    ...report,
    target: { ...report.target, department_name: departmentName },
  });

  assert.equal(supplierPptTemplateVariant(departmentReport("购物中心一部（名品）"), "常州购物中心"), "luxury");
  assert.equal(supplierPptTemplateVariant(departmentReport("新世纪一部名品"), "常州新世纪商城"), "luxury");
  assert.equal(supplierPptTemplateVariant(departmentReport("其他商场一部"), "其他商场"), "default");
});

test("womenswear template images build a complete five-slide PPT", async () => {
  const templateDirectory = "brand-member-ppt-womenswear";
  const images = {
    overview: await imageData("01-overview.png", templateDirectory),
    segments: await imageData("02-segments.png", templateDirectory),
    loyalty: await imageData("03-loyalty.png", templateDirectory),
    actions: await imageData("04-actions.png", templateDirectory),
    frequency: await imageData("05-frequency-basket.png", templateDirectory),
  };
  const presentation = buildSupplierPresentation(report, "常州购物中心", images);
  const output = await presentation.write({ outputType: "uint8array", compression: true });
  assert.equal(presentation._slides.length, 5);
  assert.ok(output.byteLength > 1_000_000);
});

test("menswear template images build a complete five-slide PPT", async () => {
  const templateDirectory = "brand-member-ppt-menswear";
  const images = {
    overview: await imageData("01-overview.png", templateDirectory),
    segments: await imageData("02-segments.png", templateDirectory),
    loyalty: await imageData("03-loyalty.png", templateDirectory),
    actions: await imageData("04-actions.png", templateDirectory),
    frequency: await imageData("05-frequency-basket.png", templateDirectory),
  };
  const presentation = buildSupplierPresentation(report, "常州购物中心", images);
  const output = await presentation.write({ outputType: "uint8array", compression: true });
  assert.equal(presentation._slides.length, 5);
  assert.ok(output.byteLength > 1_000_000);
});

test("luxury template images build a complete five-slide PPT", async () => {
  const templateDirectory = "brand-member-ppt-luxury";
  const images = {
    overview: await imageData("01-overview.png", templateDirectory),
    segments: await imageData("02-segments.png", templateDirectory),
    loyalty: await imageData("03-loyalty.png", templateDirectory),
    actions: await imageData("04-actions.png", templateDirectory),
    frequency: await imageData("05-frequency-basket.png", templateDirectory),
  };
  const presentation = buildSupplierPresentation(report, "常州购物中心", images);
  const output = await presentation.write({ outputType: "uint8array", compression: true });
  assert.equal(presentation._slides.length, 5);
  assert.ok(output.byteLength > 1_000_000);
});

test("brand member page exposes separate Excel and PPT export actions", async () => {
  const source = await readFile(new URL("../pages/member-analysis/brand-member-analysis.tsx", import.meta.url), "utf8");
  assert.match(source, /导出 Excel 沟通版/);
  assert.match(source, /导出 PPT 沟通版/);
  assert.match(source, /exportSupplierPresentation/);
  assert.match(source, /购买频次与客件分析/);
  assert.match(source, /一次客＝期间内1张正向购买小票/);
  assert.match(source, /退货小票不计客次/);
  assert.match(source, /同期客件数/);
});
