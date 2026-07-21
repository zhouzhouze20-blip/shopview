import pptxgen from "pptxgenjs";

import type {
  BrandMemberLevelConsumption,
  BrandMemberPurchaseFrequencyAnalysis,
  BrandMemberReport,
  BrandMemberSegment,
} from "./brand-member-analysis";

export interface SupplierPptTemplateImages {
  overview: string;
  segments: string;
  loyalty: string;
  actions: string;
  frequency: string;
}

export type SupplierPptTemplateVariant = "default" | "womenswear" | "menswear" | "luxury";

export interface SupplierPptNarrative {
  overviewTitle: string;
  overviewSummary: string;
  segmentTitle: string;
  segmentSummary: string;
  frequencyTitle: string;
  frequencySummary: string;
  actionItems: Array<{ title: string; copy: string }>;
}

const C = {
  emerald: "082D28",
  emeraldDeep: "061F1C",
  gold: "D8B878",
  goldLight: "F1DEBA",
  ivory: "F8F2E8",
  white: "FFFFFF",
  muted: "D8D4CA",
  blush: "D8AFA8",
  line: "8CA69E",
};

const WIDE = { width: 13.333, height: 7.5 };
const FONT = "Microsoft YaHei";

function compactNumber(value: number, digits = 0) {
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value || 0));
}

function money(value: number) {
  return `¥${compactNumber(value)}`;
}

function percent(value: number | null | undefined, absolute = false) {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${compactNumber((absolute ? Math.abs(value) : value) * 100, 1)}%`;
}

function signedChange(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value) || value === 0) return "持平";
  return `${value > 0 ? "+" : ""}${percent(value)}`;
}

function trendText(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value) || value === 0) return "持平";
  return `${value > 0 ? "增长" : "下降"}${percent(value, true)}`;
}

function segment(report: BrandMemberReport, code: BrandMemberSegment["code"]) {
  return report.target.current.segments.find((item) => item.code === code);
}

function priorSegment(report: BrandMemberReport, code: BrandMemberSegment["code"]) {
  return report.target.prior.segments.find((item) => item.code === code);
}

function frequencySegment(report: BrandMemberReport, code: BrandMemberPurchaseFrequencyAnalysis["code"]) {
  return report.target.current.purchase_frequency_analysis.find((item) => item.code === code);
}

function topMemberLevel(levels: BrandMemberLevelConsumption[]) {
  return levels
    .filter((row) => row.level_code !== "UNIDENTIFIED" && row.buyer_count > 0)
    .sort((left, right) => right.spend_per_buyer - left.spend_per_buyer)[0];
}

function safeFilename(value: string) {
  return value.replace(/[\\/:*?"<>|]/g, "_").replace(/\s+/g, " ").trim();
}

function truncate(value: string | undefined, length: number) {
  const normalized = (value || "").replace(/\s+/g, " ").trim();
  if (normalized.length <= length) return normalized;
  return `${normalized.slice(0, length - 1)}…`;
}

export function buildSupplierPptNarrative(report: BrandMemberReport): SupplierPptNarrative {
  const salesRate = report.comparison.sales_revenue?.change_rate ?? 0;
  const buyerRate = report.comparison.member_buyer_count?.change_rate ?? 0;
  const spendRate = report.comparison.spend_per_buyer?.change_rate ?? 0;
  const old = segment(report, "brand_returning");
  const oldPrior = priorSegment(report, "brand_returning");
  const external = segment(report, "external_new");
  const externalPrior = priorSegment(report, "external_new");
  const funnel = report.target.current.old_customer_funnel;
  const level = topMemberLevel(report.target.current.member_level_consumption);
  const singlePurchase = frequencySegment(report, "single_purchase");
  const repeatPurchase = frequencySegment(report, "repeat_purchase");

  let overviewTitle = "销售表现整体平稳，\n会员运营决定下一步增量";
  if (salesRate < -0.01) {
    overviewTitle = buyerRate <= spendRate
      ? "销售承压，优先恢复\n购买会员规模"
      : "销售承压，优先修复\n会员消费深度";
  } else if (salesRate > 0.01) {
    overviewTitle = buyerRate >= spendRate
      ? "销售保持增长，购买会员扩张\n是主要支撑"
      : "销售保持增长，会员消费深度\n是主要支撑";
  }

  const overviewSummary = `销售收入较同期${trendText(salesRate)}，购买会员数${trendText(buyerRate)}，会员人均消费${trendText(spendRate)}。`;
  const externalChange = (external?.buyer_count ?? 0) - (externalPrior?.buyer_count ?? 0);
  const oldChange = (old?.buyer_count ?? 0) - (oldPrior?.buyer_count ?? 0);
  const segmentTitle = (old?.buyer_share ?? 0) >= 0.6
    ? "品牌老客贡献占据主导，会员池激活仍是重点"
    : "客群来源更加分散，需要同时经营老客与新客";
  const segmentSummary = `品牌老客${compactNumber(old?.buyer_count ?? 0)}人，占购买会员${percent(old?.buyer_share)}；一次客${compactNumber(singlePurchase?.buyer_count ?? 0)}人、多次客${compactNumber(repeatPurchase?.buyer_count ?? 0)}人，会员客件数${compactNumber(report.target.current.summary.items_per_ticket, 2)}件。`;
  const frequencyTitle = "一次客与多次客分层，\n看清复购质量与连带深度";
  const frequencySummary = `本期一次客${compactNumber(singlePurchase?.buyer_count ?? 0)}人，占购买会员${percent(singlePurchase?.buyer_share)}；多次客${compactNumber(repeatPurchase?.buyer_count ?? 0)}人，占${percent(repeatPurchase?.buyer_share)}。`;

  const actionItems = [
    {
      title: `盘活${compactNumber(funnel.historical_target_member_count)}名历史品牌会员`,
      copy: `已有${compactNumber(funnel.store_visit_count)}人到店、${compactNumber(funnel.target_repurchase_count)}人回购目标柜组，优先复盘到店但未回购品牌的人群承接。`,
    },
    {
      title: level ? `深挖${level.level_label}消费潜力` : "深挖高等级会员消费潜力",
      copy: level
        ? `本期${compactNumber(level.buyer_count)}人购买，会员人均消费${money(level.spend_per_buyer)}、消费频次${compactNumber(level.purchase_frequency, 2)}次。`
        : "结合会员等级、人均消费和消费频次，安排专属护理与新品邀约。",
    },
    {
      title: externalChange < 0 ? "用体验活动补回外部新客" : "延续外部新客增长势头",
      copy: `外部招新${compactNumber(external?.buyer_count ?? 0)}人，较同期${externalChange >= 0 ? "增加" : "减少"}${compactNumber(Math.abs(externalChange))}人；可联合开展护肤课堂、体验日与柜外引流。`,
    },
  ];

  return { overviewTitle, overviewSummary, segmentTitle, segmentSummary, frequencyTitle, frequencySummary, actionItems };
}

function addFullBleed(slide: pptxgen.Slide, image: string) {
  slide.addImage({ data: image, x: 0, y: 0, w: WIDE.width, h: WIDE.height });
}

function addOverlay(slide: pptxgen.Slide, x: number, y: number, w: number, h: number, transparency = 8) {
  slide.addShape("rect", {
    x, y, w, h,
    fill: { color: C.emeraldDeep, transparency },
    line: { color: C.emeraldDeep, transparency: 100 },
  });
}

function addText(slide: pptxgen.Slide, text: string, options: pptxgen.TextPropsOptions) {
  slide.addText(text, {
    fontFace: FONT,
    color: C.white,
    margin: 0,
    breakLine: false,
    fit: "shrink",
    valign: "middle",
    ...options,
  });
}

function addEyebrow(slide: pptxgen.Slide, text: string, x = 0.75, y = 0.48) {
  slide.addShape("rect", { x, y: y + 0.04, w: 0.3, h: 0.02, fill: { color: C.gold }, line: { color: C.gold } });
  addText(slide, text, { x: x + 0.42, y: y - 0.05, w: 3.9, h: 0.25, fontSize: 11, bold: true, color: C.gold, charSpacing: 1.1 });
}

function addFooter(slide: pptxgen.Slide, storeName: string, groupName: string, period: string, page: number) {
  slide.addShape("rect", { x: 0.75, y: 7.06, w: 11.83, h: 0.01, fill: { color: C.line, transparency: 45 }, line: { color: C.line, transparency: 100 } });
  addText(slide, `${groupName}｜${storeName}｜${period}`, { x: 0.75, y: 7.1, w: 7.2, h: 0.18, fontSize: 8.5, color: C.muted });
  addText(slide, String(page).padStart(2, "0"), { x: 12.05, y: 7.1, w: 0.45, h: 0.18, fontSize: 8.5, color: C.gold, align: "right" });
}

function addMetric(slide: pptxgen.Slide, x: number, value: string, label: string, note: string) {
  addText(slide, value, { x, y: 5.72, w: 2.25, h: 0.47, fontSize: 26, bold: true });
  addText(slide, label, { x, y: 6.18, w: 2.25, h: 0.26, fontSize: 12, bold: true, color: C.goldLight });
  addText(slide, note, { x, y: 6.45, w: 2.25, h: 0.23, fontSize: 9.5, color: C.muted });
}

export function buildSupplierPresentation(
  report: BrandMemberReport,
  storeName: string,
  images: SupplierPptTemplateImages,
  aiConclusion?: string,
) {
  const pptx = new pptxgen();
  pptx.defineLayout({ name: "SHOPVIEW_WIDE", width: WIDE.width, height: WIDE.height });
  pptx.layout = "SHOPVIEW_WIDE";
  pptx.author = "ShopView";
  pptx.company = storeName;
  pptx.subject = "品牌会员经营分析供应商沟通版";
  pptx.title = `${report.target.group_name} 品牌会员经营分析`;
  pptx.theme = {
    headFontFace: FONT,
    bodyFontFace: FONT,
  };

  const narrative = buildSupplierPptNarrative(report);
  const current = report.target.current;
  const prior = report.target.prior;
  const old = segment(report, "brand_returning");
  const external = segment(report, "external_new");
  const oldPrior = priorSegment(report, "brand_returning");
  const externalPrior = priorSegment(report, "external_new");
  const funnel = current.old_customer_funnel;
  const period = `${current.period.start_date} 至 ${current.period.end_date}`;

  // 01 经营总览
  {
    const slide = pptx.addSlide();
    addFullBleed(slide, images.overview);
    addOverlay(slide, 0, 0, 7.55, 7.5, 5);
    addOverlay(slide, 0, 5.39, 13.333, 2.11, 8);
    addEyebrow(slide, "供应商经营复盘");
    addText(slide, narrative.overviewTitle, { x: 0.75, y: 1.08, w: 5.9, h: 1.08, fontSize: 31, bold: true, breakLine: true, valign: "top" });
    addText(slide, narrative.overviewSummary, { x: 0.75, y: 2.48, w: 5.45, h: 0.65, fontSize: 15, color: C.ivory, breakLine: true, valign: "top", lineSpacingMultiple: 1.05 });
    if (aiConclusion) {
      addText(slide, truncate(aiConclusion, 92), { x: 0.75, y: 3.32, w: 5.4, h: 0.65, fontSize: 11.5, color: C.muted, italic: true, breakLine: true, valign: "top" });
    }
    slide.addShape("rect", { x: 0.75, y: 4.17, w: 0.92, h: 0.025, fill: { color: C.gold }, line: { color: C.gold } });
    addText(slide, "本期销售收入", { x: 0.75, y: 4.32, w: 1.6, h: 0.24, fontSize: 10.5, color: C.muted });
    addText(slide, money(current.summary.sales_revenue), { x: 0.75, y: 4.52, w: 2.7, h: 0.52, fontSize: 31, bold: true, color: C.goldLight });
    addMetric(slide, 0.75, signedChange(report.comparison.sales_revenue?.change_rate), "销售收入较同期", `同期 ${money(prior.summary.sales_revenue)}`);
    addMetric(slide, 3.66, `${compactNumber(current.summary.member_buyer_count)}人`, "购买会员数", `较同期 ${signedChange(report.comparison.member_buyer_count?.change_rate)}`);
    addMetric(slide, 6.58, money(current.summary.spend_per_buyer), "会员人均消费", `较同期 ${signedChange(report.comparison.spend_per_buyer?.change_rate)}`);
    const rank = current.summary.department_rank == null ? "—" : `第${current.summary.department_rank}位`;
    const rankNote = prior.summary.department_rank == null || current.summary.department_rank == null
      ? `共${compactNumber(current.summary.department_group_count)}个柜组`
      : `${current.summary.department_rank < prior.summary.department_rank ? "提升" : current.summary.department_rank > prior.summary.department_rank ? "下降" : "持平"}${Math.abs(current.summary.department_rank - prior.summary.department_rank)}位`;
    addMetric(slide, 9.5, rank, "部门销售排名", rankNote);
    addFooter(slide, storeName, report.target.group_name, period, 1);
    slide.addNotes(`数据来源：ShopView汇总数据。比较期间：${prior.period.start_date} 至 ${prior.period.end_date}。`);
  }

  // 02 会员结构
  {
    const slide = pptx.addSlide();
    addFullBleed(slide, images.segments);
    addOverlay(slide, 0, 0, 13.333, 7.5, 12);
    addEyebrow(slide, "会员结构｜价值核心");
    addText(slide, narrative.segmentTitle, { x: 0.75, y: 1.02, w: 5.6, h: 0.95, fontSize: 29, bold: true, breakLine: true, valign: "top" });
    addText(slide, narrative.segmentSummary, { x: 0.75, y: 2.26, w: 5.5, h: 0.58, fontSize: 14, color: C.ivory, breakLine: true, valign: "top" });
    addText(slide, percent(old?.buyer_share), { x: 0.75, y: 3.37, w: 2.35, h: 0.66, fontSize: 38, bold: true, color: C.goldLight });
    addText(slide, "购买会员为品牌老客", { x: 0.75, y: 4.04, w: 2.4, h: 0.25, fontSize: 12.5, bold: true });
    addText(slide, `${compactNumber(old?.buyer_count ?? 0)} / ${compactNumber(current.summary.member_buyer_count)}人`, { x: 0.75, y: 4.36, w: 2.2, h: 0.2, fontSize: 10.5, color: C.muted });
    addText(slide, percent(old?.sales_share), { x: 3.48, y: 3.37, w: 2.35, h: 0.66, fontSize: 38, bold: true, color: C.goldLight });
    addText(slide, "销售收入来自品牌老客", { x: 3.48, y: 4.04, w: 2.55, h: 0.25, fontSize: 12.5, bold: true });
    addText(slide, money(old?.sales_revenue ?? 0), { x: 3.48, y: 4.36, w: 2.2, h: 0.2, fontSize: 10.5, color: C.muted });

    addText(slide, "购买会员构成", { x: 7.0, y: 3.52, w: 2.5, h: 0.25, fontSize: 13, bold: true });
    const barX = 7.0;
    const barY = 4.04;
    const barW = 4.72;
    const colors: Record<BrandMemberSegment["code"], string> = {
      brand_returning: C.goldLight,
      same_department_inflow: "88AFA3",
      cross_department_inflow: "6D9287",
      external_new: C.blush,
    };
    let offset = 0;
    current.segments.forEach((row) => {
      const width = Math.max(0, barW * Math.max(0, row.buyer_share ?? 0));
      if (width > 0) {
        slide.addShape("rect", { x: barX + offset, y: barY, w: width, h: 0.24, fill: { color: colors[row.code] }, line: { color: colors[row.code] } });
      }
      offset += width;
    });
    addText(slide, `品牌老客 ${percent(old?.buyer_share)}`, { x: 7.0, y: 4.51, w: 1.7, h: 0.22, fontSize: 9.5, bold: true, color: C.goldLight });
    const internalShare = (segment(report, "same_department_inflow")?.buyer_share ?? 0) + (segment(report, "cross_department_inflow")?.buyer_share ?? 0);
    addText(slide, `内部流入 ${percent(internalShare)}`, { x: 8.85, y: 4.51, w: 1.55, h: 0.22, fontSize: 9.5, color: C.muted, align: "center" });
    addText(slide, `外部招新 ${percent(external?.buyer_share)}`, { x: 10.42, y: 4.51, w: 1.55, h: 0.22, fontSize: 9.5, bold: true, color: C.blush, align: "right" });
    slide.addShape("rect", { x: 7.0, y: 5.18, w: 4.72, h: 0.01, fill: { color: C.line, transparency: 45 }, line: { color: C.line, transparency: 100 } });
    const externalChange = (external?.buyer_count ?? 0) - (externalPrior?.buyer_count ?? 0);
    const oldChange = (old?.buyer_count ?? 0) - (oldPrior?.buyer_count ?? 0);
    addText(slide, `外部招新：${compactNumber(external?.buyer_count ?? 0)}人`, { x: 7.0, y: 5.42, w: 2.2, h: 0.3, fontSize: 17, bold: true });
    addText(slide, `较同期${externalChange >= 0 ? "增加" : "减少"}${compactNumber(Math.abs(externalChange))}人`, { x: 7.0, y: 5.78, w: 2.2, h: 0.24, fontSize: 11, color: externalChange >= 0 ? C.goldLight : C.blush });
    addText(slide, `品牌老客：${compactNumber(old?.buyer_count ?? 0)}人`, { x: 9.68, y: 5.42, w: 2.2, h: 0.3, fontSize: 17, bold: true });
    addText(slide, `较同期${oldChange >= 0 ? "增加" : "减少"}${compactNumber(Math.abs(oldChange))}人`, { x: 9.68, y: 5.78, w: 2.2, h: 0.24, fontSize: 11, color: oldChange >= 0 ? C.goldLight : C.blush });
    addFooter(slide, storeName, report.target.group_name, period, 2);
  }

  // 03 老客经营
  {
    const slide = pptx.addSlide();
    addFullBleed(slide, images.loyalty);
    addOverlay(slide, 6.18, 0, 7.16, 7.5, 3);
    addEyebrow(slide, "老客经营｜激活漏斗", 6.76, 0.48);
    addText(slide, `${compactNumber(funnel.historical_target_member_count)}名历史品牌会员，\n仅${compactNumber(funnel.target_repurchase_count)}人完成本期回购`, { x: 6.76, y: 1.04, w: 5.55, h: 1.03, fontSize: 29, bold: true, breakLine: true, valign: "top" });
    addText(slide, "品牌老客贡献高，但会员池从到店到回购的转化链路仍有提升空间。", { x: 6.76, y: 2.35, w: 5.0, h: 0.48, fontSize: 13.5, color: C.ivory, breakLine: true, valign: "top" });
    const levels = [
      ["历史品牌会员", funnel.historical_target_member_count],
      ["本期到店", funnel.store_visit_count],
      ["到目标部门", funnel.department_visit_count],
      ["回购目标柜组", funnel.target_repurchase_count],
    ] as const;
    slide.addShape("rect", { x: 6.92, y: 3.58, w: 0.015, h: 2.15, fill: { color: C.gold, transparency: 40 }, line: { color: C.gold, transparency: 100 } });
    levels.forEach(([label, value], index) => {
      const y = 3.28 + index * 0.72;
      const rate = funnel.historical_target_member_count > 0 ? value / funnel.historical_target_member_count : 0;
      slide.addShape("ellipse", { x: 6.81, y: y + 0.18, w: 0.23, h: 0.23, fill: { color: [C.goldLight, C.gold, "B59A6E", "8E7656"][index] }, line: { color: C.emerald, width: 1.5 } });
      addText(slide, label, { x: 7.36, y, w: 1.85, h: 0.52, fontSize: 13.5, bold: true });
      addText(slide, `${compactNumber(value)}人`, { x: 9.45, y, w: 1.4, h: 0.52, fontSize: 20, bold: true, color: C.goldLight, align: "right" });
      addText(slide, percent(rate), { x: 11.2, y, w: 0.75, h: 0.52, fontSize: 12.5, bold: true, color: [C.goldLight, C.gold, "B59A6E", "8E7656"][index], align: "right" });
      if (index < levels.length - 1) slide.addShape("rect", { x: 7.36, y: y + 0.62, w: 4.6, h: 0.01, fill: { color: C.line, transparency: 55 }, line: { color: C.line, transparency: 100 } });
    });
    addText(slide, "优先复盘：已到店但未回购品牌的人群承接", { x: 7.2, y: 6.35, w: 4.75, h: 0.32, fontSize: 13, bold: true, color: C.goldLight, align: "center" });
    addOverlay(slide, 0, 6.94, 6.18, 0.56, 42);
    addFooter(slide, storeName, report.target.group_name, period, 3);
  }

  // 04 联合行动
  {
    const slide = pptx.addSlide();
    addFullBleed(slide, images.actions);
    addOverlay(slide, 0, 0, 8.05, 7.5, 5);
    addEyebrow(slide, "联合行动｜品牌 × 商场");
    addText(slide, "把存量价值与新客增量\n放进同一套经营动作", { x: 0.75, y: 1.0, w: 5.95, h: 0.98, fontSize: 29, bold: true, breakLine: true, valign: "top" });
    addText(slide, "建议围绕三件事共同推进，并持续跟踪触达、到店、购买和回购", { x: 0.75, y: 2.28, w: 5.8, h: 0.4, fontSize: 13.5, color: C.ivory, breakLine: true, valign: "top" });
    narrative.actionItems.forEach((item, index) => {
      const y = 3.16 + index * 0.98;
      const accent = [C.goldLight, C.gold, C.blush][index];
      addText(slide, String(index + 1).padStart(2, "0"), { x: 0.75, y, w: 0.5, h: 0.3, fontSize: 15, bold: true, color: accent });
      slide.addShape("rect", { x: 1.37, y: y + 0.01, w: 0.025, h: 0.72, fill: { color: accent }, line: { color: accent } });
      addText(slide, item.title, { x: 1.58, y: y - 0.03, w: 4.85, h: 0.32, fontSize: 17, bold: true });
      addText(slide, item.copy, { x: 1.58, y: y + 0.34, w: 4.9, h: 0.42, fontSize: 11.2, color: C.muted, breakLine: true, valign: "top" });
    });
    addFooter(slide, storeName, report.target.group_name, period, 4);
  }

  // 05 购买频次与客件
  {
    const slide = pptx.addSlide();
    const singlePurchase = frequencySegment(report, "single_purchase");
    const repeatPurchase = frequencySegment(report, "repeat_purchase");
    addFullBleed(slide, images.frequency);
    addOverlay(slide, 0, 0, 7.55, 7.5, 7);
    addEyebrow(slide, "购买频次｜客件表现");
    addText(slide, narrative.frequencyTitle, { x: 0.75, y: 1.02, w: 5.8, h: 0.96, fontSize: 29, bold: true, breakLine: true, valign: "top" });
    addText(slide, narrative.frequencySummary, { x: 0.75, y: 2.27, w: 5.65, h: 0.52, fontSize: 13.5, color: C.ivory, breakLine: true, valign: "top" });

    const singleShare = Math.max(0, Math.min(1, singlePurchase?.buyer_share ?? 0));
    const repeatShare = Math.max(0, Math.min(1, repeatPurchase?.buyer_share ?? 0));
    const barX = 0.75;
    const barY = 3.25;
    const barW = 5.75;
    slide.addShape("rect", { x: barX, y: barY, w: barW, h: 0.22, fill: { color: C.line, transparency: 65 }, line: { color: C.line, transparency: 100 } });
    if (singleShare > 0) slide.addShape("rect", { x: barX, y: barY, w: barW * singleShare, h: 0.22, fill: { color: "88AFA3" }, line: { color: "88AFA3" } });
    if (repeatShare > 0) slide.addShape("rect", { x: barX + barW * singleShare, y: barY, w: barW * repeatShare, h: 0.22, fill: { color: C.goldLight }, line: { color: C.goldLight } });
    addText(slide, `一次客 ${compactNumber(singlePurchase?.buyer_count ?? 0)}人｜${percent(singlePurchase?.buyer_share)}`, { x: barX, y: 3.59, w: 2.7, h: 0.24, fontSize: 11, color: C.muted });
    addText(slide, `多次客 ${compactNumber(repeatPurchase?.buyer_count ?? 0)}人｜${percent(repeatPurchase?.buyer_share)}`, { x: 3.55, y: 3.59, w: 2.95, h: 0.24, fontSize: 11, bold: true, color: C.goldLight, align: "right" });

    const basketMetrics = [
      [compactNumber(singlePurchase?.items_per_ticket ?? 0, 2), "一次客客件数", `客单 ${money(singlePurchase?.average_ticket_value ?? 0)}`],
      [compactNumber(repeatPurchase?.items_per_ticket ?? 0, 2), "多次客客件数", `客单 ${money(repeatPurchase?.average_ticket_value ?? 0)}`],
      [compactNumber(current.summary.items_per_ticket, 2), "整体会员客件数", `同期 ${compactNumber(prior.summary.items_per_ticket, 2)}`],
    ] as const;
    basketMetrics.forEach(([value, label, note], index) => {
      const x = 0.75 + index * 2.02;
      addText(slide, `${value}件`, { x, y: 4.55, w: 1.72, h: 0.46, fontSize: 25, bold: true, color: index === 1 ? C.goldLight : C.white });
      addText(slide, label, { x, y: 5.05, w: 1.72, h: 0.25, fontSize: 11.5, bold: true, color: C.goldLight });
      addText(slide, note, { x, y: 5.36, w: 1.72, h: 0.22, fontSize: 9.5, color: C.muted });
    });
    addText(slide, "客件数＝会员净销售件数÷正向购买小票数｜退货小票不计客次，退货数量按负数冲减", { x: 0.75, y: 6.18, w: 5.8, h: 0.26, fontSize: 9.5, color: C.muted });
    addFooter(slide, storeName, report.target.group_name, period, 5);
    slide.addNotes("一次客为期间内1张正向购买小票，多次客为期间内2张及以上正向购买小票，退货小票不计客次。客件数按会员净销售件数除以正向购买小票数计算，退货数量按负数冲减。");
  }

  return pptx;
}

function blobToDataUrl(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error || new Error("PPT模板图片读取失败"));
    reader.readAsDataURL(blob);
  });
}

const templateImagesPromises = new Map<SupplierPptTemplateVariant, Promise<SupplierPptTemplateImages>>();

export function supplierPptTemplateVariant(report: BrandMemberReport, storeName: string): SupplierPptTemplateVariant {
  const normalizedStoreName = storeName.replace(/\s+/g, "");
  const normalizedDepartmentName = (report.target.department_name || "").replace(/\s+/g, "");
  const isShoppingCenterLuxury = normalizedStoreName.includes("购物中心")
    && /一部/.test(normalizedDepartmentName);
  const isNewCenturyLuxury = normalizedStoreName.includes("新世纪")
    && /一部/.test(normalizedDepartmentName);
  if (isShoppingCenterLuxury || isNewCenturyLuxury) return "luxury";

  const isShoppingCenterWomenswear = normalizedStoreName.includes("购物中心")
    && /[二三]部/.test(normalizedDepartmentName);
  const isNewCenturyWomenswear = normalizedStoreName.includes("新世纪")
    && /[二三四]部/.test(normalizedDepartmentName);
  if (isShoppingCenterWomenswear || isNewCenturyWomenswear) return "womenswear";

  const isShoppingCenterMenswear = normalizedStoreName.includes("购物中心")
    && /四部/.test(normalizedDepartmentName);
  const isNewCenturyMenswear = normalizedStoreName.includes("新世纪")
    && /六部/.test(normalizedDepartmentName);
  if (isShoppingCenterMenswear || isNewCenturyMenswear) return "menswear";

  return "default";
}

export function supplierPptTemplateDirectory(variant: SupplierPptTemplateVariant) {
  if (variant === "womenswear") return "brand-member-ppt-womenswear";
  if (variant === "menswear") return "brand-member-ppt-menswear";
  if (variant === "luxury") return "brand-member-ppt-luxury";
  return "brand-member-ppt";
}

export function resolveSupplierPptTemplateImageUrl(
  fileName: string,
  origin: string,
  baseUrl: string,
  variant: SupplierPptTemplateVariant = "default",
) {
  const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  return new URL(`${normalizedBaseUrl}${supplierPptTemplateDirectory(variant)}/${fileName}`, origin);
}

export function supplierPptTemplateBaseUrl(isProduction: boolean) {
  return isProduction ? "/static/" : "/";
}

export function assertSupplierPptTemplateImageResponse(response: Response, fileName: string) {
  if (!response.ok) throw new Error(`PPT模板图片加载失败：${fileName}`);
  const contentType = response.headers.get("content-type")?.toLowerCase() || "";
  if (!contentType.startsWith("image/")) {
    throw new Error(`PPT模板图片格式错误：${fileName}`);
  }
}

export function loadSupplierPptTemplateImages(variant: SupplierPptTemplateVariant = "default") {
  const cachedPromise = templateImagesPromises.get(variant);
  if (cachedPromise) return cachedPromise;
  const names = {
    overview: "01-overview.png",
    segments: "02-segments.png",
    loyalty: "03-loyalty.png",
    actions: "04-actions.png",
    frequency: "05-frequency-basket.png",
  } as const;
  const templateImagesPromise = Promise.all(
    Object.entries(names).map(async ([key, fileName]) => {
      const url = resolveSupplierPptTemplateImageUrl(
        fileName,
        window.location.origin,
        supplierPptTemplateBaseUrl(import.meta.env.PROD),
        variant,
      );
      const response = await fetch(url);
      assertSupplierPptTemplateImageResponse(response, fileName);
      return [key, await blobToDataUrl(await response.blob())] as const;
    }),
  )
    .then((entries) => Object.fromEntries(entries) as unknown as SupplierPptTemplateImages)
    .catch((error) => {
      templateImagesPromises.delete(variant);
      throw error;
    });
  templateImagesPromises.set(variant, templateImagesPromise);
  return templateImagesPromise;
}

export async function exportSupplierPresentation(
  report: BrandMemberReport,
  storeName: string,
  aiConclusion?: string,
) {
  const images = await loadSupplierPptTemplateImages(supplierPptTemplateVariant(report, storeName));
  const pptx = buildSupplierPresentation(report, storeName, images, aiConclusion);
  const filename = safeFilename(
    `品牌会员经营分析_${storeName}_${report.target.group_name}_${report.target.current.period.start_date}_${report.target.current.period.end_date}.pptx`,
  );
  await pptx.writeFile({ fileName: filename, compression: true });
  return filename;
}
