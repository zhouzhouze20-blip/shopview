import XLSX from "xlsx-js-style";

import type { BrandMemberReport } from "@/lib/brand-member-analysis";


const COLORS = {
  ink: "0F172A",
  slate: "475569",
  muted: "64748B",
  line: "CBD5E1",
  softLine: "E2E8F0",
  teal: "0F766E",
  tealDark: "115E59",
  tealSoft: "CCFBF1",
  tealPale: "F0FDFA",
  white: "FFFFFF",
  warm: "FFF7ED",
  amber: "B45309",
  red: "B91C1C",
  redSoft: "FEF2F2",
  green: "047857",
  greenSoft: "ECFDF5",
  graySoft: "F8FAFC",
};

const FONT_NAME = "Microsoft YaHei";
const MONEY_FORMAT = '#,##0;[Red]-#,##0';
const COUNT_FORMAT = "#,##0";
const PERCENT_FORMAT = "0.0%";

type Worksheet = XLSX.WorkSheet;
type CellStyle = Record<string, unknown>;

const thinBottom = { bottom: { style: "thin", color: { rgb: COLORS.softLine } } };

const baseCellStyle: CellStyle = {
  fill: { fgColor: { rgb: COLORS.white } },
  font: { name: FONT_NAME, sz: 10, color: { rgb: COLORS.ink } },
  alignment: { vertical: "center" },
};

const titleStyle: CellStyle = {
  fill: { fgColor: { rgb: COLORS.tealDark } },
  font: { name: FONT_NAME, sz: 22, bold: true, color: { rgb: COLORS.white } },
  alignment: { horizontal: "left", vertical: "center" },
};

const subtitleStyle: CellStyle = {
  fill: { fgColor: { rgb: COLORS.tealDark } },
  font: { name: FONT_NAME, sz: 10, color: { rgb: "D1FAE5" } },
  alignment: { horizontal: "left", vertical: "center" },
};

const sectionStyle: CellStyle = {
  fill: { fgColor: { rgb: COLORS.tealSoft } },
  font: { name: FONT_NAME, sz: 12, bold: true, color: { rgb: COLORS.tealDark } },
  alignment: { horizontal: "left", vertical: "center" },
  border: { bottom: { style: "medium", color: { rgb: COLORS.teal } } },
};

const tableHeaderStyle: CellStyle = {
  fill: { fgColor: { rgb: COLORS.teal } },
  font: { name: FONT_NAME, sz: 10, bold: true, color: { rgb: COLORS.white } },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
  border: thinBottom,
};

function cleanFilePart(value: string) {
  return value.replace(/[\\/:*?"<>|]/g, "_").slice(0, 50);
}

function mergeStyles(...styles: CellStyle[]) {
  const result: Record<string, unknown> = {};
  for (const style of styles) {
    for (const [key, value] of Object.entries(style)) {
      if (value && typeof value === "object" && !Array.isArray(value)) {
        result[key] = { ...((result[key] as Record<string, unknown>) || {}), ...(value as Record<string, unknown>) };
      } else {
        result[key] = value;
      }
    }
  }
  return result;
}

function ensureCell(sheet: Worksheet, row: number, column: number) {
  const address = XLSX.utils.encode_cell({ r: row, c: column });
  if (!sheet[address]) sheet[address] = { t: "s", v: "" };
  return sheet[address]!;
}

function styleRange(sheet: Worksheet, range: string, style: CellStyle) {
  const decoded = XLSX.utils.decode_range(range);
  for (let row = decoded.s.r; row <= decoded.e.r; row += 1) {
    for (let column = decoded.s.c; column <= decoded.e.c; column += 1) {
      const cell = ensureCell(sheet, row, column);
      cell.s = mergeStyles((cell.s as CellStyle) || {}, style);
    }
  }
}

function setNumberFormat(sheet: Worksheet, range: string, numFmt: string) {
  const decoded = XLSX.utils.decode_range(range);
  for (let row = decoded.s.r; row <= decoded.e.r; row += 1) {
    for (let column = decoded.s.c; column <= decoded.e.c; column += 1) {
      const cell = ensureCell(sheet, row, column);
      cell.z = numFmt;
      cell.s = mergeStyles((cell.s as CellStyle) || {}, { numFmt });
    }
  }
}

function merge(sheet: Worksheet, range: string) {
  sheet["!merges"] ||= [];
  sheet["!merges"]!.push(XLSX.utils.decode_range(range));
}

function applyBase(sheet: Worksheet, usedRange: string) {
  styleRange(sheet, usedRange, baseCellStyle);
  sheet["!margins"] = { left: 0.35, right: 0.35, top: 0.5, bottom: 0.5, header: 0.2, footer: 0.2 };
  sheet["!pageSetup"] = { orientation: "landscape", fitToWidth: 1, fitToHeight: 0, paperSize: 9 };
  (sheet as Worksheet & { "!sheetViews"?: Array<Record<string, unknown>> })["!sheetViews"] = [{ showGridLines: false }];
}

function applyTitle(sheet: Worksheet, lastColumn: string, title: string, subtitle: string) {
  merge(sheet, `A1:${lastColumn}2`);
  merge(sheet, `A3:${lastColumn}3`);
  sheet.A1 = { t: "s", v: title };
  sheet.A3 = { t: "s", v: subtitle };
  styleRange(sheet, `A1:${lastColumn}2`, titleStyle);
  styleRange(sheet, `A3:${lastColumn}3`, subtitleStyle);
  sheet["!rows"] ||= [];
  sheet["!rows"]![0] = { hpt: 30 };
  sheet["!rows"]![1] = { hpt: 16 };
  sheet["!rows"]![2] = { hpt: 22 };
}

function applyTable(sheet: Worksheet, headerRow: number, endRow: number, lastColumn: string) {
  styleRange(sheet, `A${headerRow}:${lastColumn}${headerRow}`, tableHeaderStyle);
  for (let row = headerRow + 1; row <= endRow; row += 1) {
    styleRange(sheet, `A${row}:${lastColumn}${row}`, {
      fill: { fgColor: { rgb: row % 2 === 0 ? COLORS.white : COLORS.graySoft } },
      border: thinBottom,
      alignment: { vertical: "center", wrapText: true },
    });
  }
  sheet["!autofilter"] = { ref: `A${headerRow}:${lastColumn}${endRow}` };
}

function signedRateText(rate: number | null | undefined) {
  if (rate == null || !Number.isFinite(rate)) return "同期无可比基数";
  if (Math.abs(rate) < 0.005) return "与同期基本持平";
  return `较同期${rate > 0 ? "增长" : "下降"}${Math.abs(rate * 100).toFixed(1)}%`;
}

function rankText(rank: number | null, total: number) {
  if (!rank) return "暂无排名";
  return `第${rank}位 / ${total}个柜组`;
}

function rankChangeText(currentRank: number | null, priorRank: number | null) {
  if (!currentRank || !priorRank) return "暂无可比排名";
  const movement = priorRank - currentRank;
  if (movement === 0) return "持平";
  return `${movement > 0 ? "提升" : "下降"}${Math.abs(movement)}位`;
}

function roundMoney(value: number) {
  return Math.round(value);
}

function roundDecimal(value: number, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function roundNullableDecimal(value: number | null, digits = 2) {
  if (value == null || !Number.isFinite(value)) return null;
  return roundDecimal(value, digits);
}

function metricHint(label: string, rate: number | null | undefined) {
  if (label === "销售收入") return rate != null && rate < 0 ? "销售承压，建议先对齐客流与客群结构变化" : "保持增长动能，复盘主要贡献客群";
  if (label === "购买会员数") return rate != null && rate < 0 ? "优先关注会员到店与购买转化" : "关注新增会员的后续复购";
  if (label === "会员人均消费") return rate != null && Math.abs(rate) < 0.03 ? "消费深度相对稳定" : "结合品类与客群变化进一步复盘";
  if (label === "会员消费频次") return rate != null && Math.abs(rate) < 0.03 ? "购买频次相对稳定" : "关注老客回访节奏";
  if (label === "品牌老客回购率") return rate != null && rate < 0 ? "建议聚焦到店未回购老客" : "老客经营表现改善";
  return "用于部门内经营位置沟通";
}

function supplierSuggestions(report: BrandMemberReport) {
  const current = report.target.current;
  const largestSegment = [...current.segments].sort((a, b) => b.buyer_count - a.buyer_count)[0];
  const storeVisit = current.old_customer_funnel.store_visit_count;
  const repurchase = current.old_customer_funnel.target_repurchase_count;
  const pending = Math.max(storeVisit - repurchase, 0);
  const suggestions = [
    "先对齐销售收入与购买会员规模变化，再结合会员人均消费判断变化主要来自客流还是消费深度。",
  ];
  if (largestSegment) {
    suggestions.push(`本期主要购买客群为${largestSegment.label}（${largestSegment.buyer_count}人，占购买会员${((largestSegment.buyer_share || 0) * 100).toFixed(1)}%），建议围绕该客群安排重点沟通。`);
  }
  if (pending > 0) suggestions.push(`历史品牌会员中，本期已有${storeVisit}人到店、${repurchase}人回购目标柜组，可优先复盘到店未回购人群的承接机会。`);
  return suggestions.slice(0, 3);
}

function createOverviewSheet(report: BrandMemberReport, storeName: string, conclusion?: string) {
  const current = report.target.current;
  const prior = report.target.prior;
  const metrics = [
    ["销售收入", roundMoney(current.summary.sales_revenue), roundMoney(prior.summary.sales_revenue), roundNullableDecimal(report.comparison.sales_revenue?.change ?? null, 0), report.comparison.sales_revenue?.change_rate ?? null],
    ["购买会员数", current.summary.member_buyer_count, prior.summary.member_buyer_count, report.comparison.member_buyer_count?.change ?? null, report.comparison.member_buyer_count?.change_rate ?? null],
    ["会员人均消费", roundMoney(current.summary.spend_per_buyer), roundMoney(prior.summary.spend_per_buyer), roundNullableDecimal(report.comparison.spend_per_buyer?.change ?? null, 0), report.comparison.spend_per_buyer?.change_rate ?? null],
    ["会员消费频次", roundDecimal(current.summary.purchase_frequency), roundDecimal(prior.summary.purchase_frequency), roundNullableDecimal(report.comparison.purchase_frequency?.change ?? null), report.comparison.purchase_frequency?.change_rate ?? null],
    ["品牌老客回购率", current.summary.old_customer_repurchase_rate, prior.summary.old_customer_repurchase_rate, report.comparison.old_customer_repurchase_rate?.change ?? null, report.comparison.old_customer_repurchase_rate?.change_rate ?? null],
  ] as Array<[string, number, number, number | null, number | null]>;
  const suggestions = supplierSuggestions(report);
  const rows: unknown[][] = [
    ["品牌会员经营沟通简报"],
    [],
    ["供应商沟通材料｜仅供经营复盘使用"],
    [],
    ["品牌 / 柜组", `${report.target.group_name}（${report.target.group_code}）`, "", "门店", storeName, ""],
    ["所属部门", report.target.department_name || "—", "", "分析期间", `${current.period.start_date} 至 ${current.period.end_date}`, ""],
    ["对比期间", `${prior.period.start_date} 至 ${prior.period.end_date}`, "", "生成口径", "ShopView 汇总数据", ""],
    [],
    ["经营结论"],
    [conclusion?.trim() || metrics.slice(0, 2).map(([label, , , , rate]) => `${label}${signedRateText(rate)}`).join("；") + "。"],
    [],
    ["核心经营指标（金额单位：人民币元）"],
    ["指标", "本期", "同期", "变化", "变化率", "沟通提示"],
    ...metrics.map(([label, currentValue, priorValue, change, rate]) => [label, currentValue, priorValue, change, rate, metricHint(label, rate)]),
    ["部门销售排名", rankText(current.summary.department_rank, current.summary.department_group_count), rankText(prior.summary.department_rank, prior.summary.department_group_count), rankChangeText(current.summary.department_rank, prior.summary.department_rank), null, "排名数字越小代表部门内位置越靠前"],
    [],
    ["建议沟通顺序"],
    ...suggestions.map((suggestion, index) => [`${index + 1}. ${suggestion}`]),
    [],
    ["说明：本文件仅包含汇总经营数据，不含会员姓名、手机号、卡号等个人信息。"],
  ];
  const sheet = XLSX.utils.aoa_to_sheet(rows);
  applyBase(sheet, `A1:F${rows.length}`);
  applyTitle(sheet, "F", "品牌会员经营沟通简报", "供应商沟通材料｜仅供经营复盘使用");

  for (const range of ["B5:C5", "E5:F5", "B6:C6", "E6:F6", "B7:C7", "E7:F7", "A9:F9", "A10:F10", "A12:F12", "A21:F21", "A22:F22", "A23:F23", "A24:F24", `A26:F26`]) merge(sheet, range);
  for (const row of [5, 6, 7]) {
    styleRange(sheet, `A${row}:A${row}`, { font: { name: FONT_NAME, bold: true, color: { rgb: COLORS.muted } }, fill: { fgColor: { rgb: COLORS.graySoft } } });
    styleRange(sheet, `D${row}:D${row}`, { font: { name: FONT_NAME, bold: true, color: { rgb: COLORS.muted } }, fill: { fgColor: { rgb: COLORS.graySoft } } });
    styleRange(sheet, `B${row}:C${row}`, { font: { name: FONT_NAME, bold: true, color: { rgb: COLORS.ink } }, border: thinBottom });
    styleRange(sheet, `E${row}:F${row}`, { font: { name: FONT_NAME, bold: true, color: { rgb: COLORS.ink } }, border: thinBottom });
  }
  styleRange(sheet, "A9:F9", sectionStyle);
  styleRange(sheet, "A10:F10", { fill: { fgColor: { rgb: COLORS.tealPale } }, font: { name: FONT_NAME, sz: 11, bold: true, color: { rgb: COLORS.tealDark } }, alignment: { wrapText: true, vertical: "center" }, border: { left: { style: "medium", color: { rgb: COLORS.teal } } } });
  styleRange(sheet, "A12:F12", sectionStyle);
  applyTable(sheet, 13, 19, "F");
  styleRange(sheet, "A21:F21", sectionStyle);
  for (const row of [22, 23, 24]) styleRange(sheet, `A${row}:F${row}`, { fill: { fgColor: { rgb: COLORS.warm } }, font: { name: FONT_NAME, color: { rgb: COLORS.ink } }, alignment: { wrapText: true, vertical: "center" }, border: { left: { style: "medium", color: { rgb: COLORS.amber } } } });
  styleRange(sheet, "A26:F26", { font: { name: FONT_NAME, sz: 9, italic: true, color: { rgb: COLORS.muted } }, alignment: { wrapText: true } });

  setNumberFormat(sheet, "B14:D14", MONEY_FORMAT);
  setNumberFormat(sheet, "B15:D15", COUNT_FORMAT);
  setNumberFormat(sheet, "B16:D16", MONEY_FORMAT);
  setNumberFormat(sheet, "B17:D17", "0.00");
  setNumberFormat(sheet, "B18:E18", PERCENT_FORMAT);
  setNumberFormat(sheet, "E14:E17", PERCENT_FORMAT);
  for (let row = 14; row <= 18; row += 1) {
    const rate = metrics[row - 14]?.[4];
    if (rate == null) continue;
    styleRange(sheet, `E${row}`, { font: { name: FONT_NAME, bold: true, color: { rgb: rate >= 0 ? COLORS.green : COLORS.red } }, fill: { fgColor: { rgb: rate >= 0 ? COLORS.greenSoft : COLORS.redSoft } } });
  }

  sheet["!cols"] = [{ wch: 18 }, { wch: 17 }, { wch: 17 }, { wch: 16 }, { wch: 14 }, { wch: 42 }];
  sheet["!rows"]![9] = { hpt: 58 };
  sheet["!rows"]![21] = { hpt: 34 };
  sheet["!rows"]![22] = { hpt: 34 };
  sheet["!rows"]![23] = { hpt: 34 };
  sheet["!rows"]![25] = { hpt: 28 };
  return sheet;
}

function createMemberStructureSheet(report: BrandMemberReport) {
  const current = report.target.current;
  const prior = report.target.prior;
  const rows: unknown[][] = [
    ["会员客群结构"],
    [],
    [`${report.target.group_name}｜本期与同期客群构成对比`],
    [],
    ["客群", "本期人数", "人数占比", "本期销售收入（元）", "销售占比", "同期人数", "同期销售收入（元）", "人数变化"],
    ...current.segments.map((row) => {
      const priorRow = prior.segments.find((item) => item.code === row.code);
      return [row.label, row.buyer_count, row.buyer_share, roundMoney(row.sales_revenue), row.sales_share, priorRow?.buyer_count ?? 0, roundMoney(priorRow?.sales_revenue ?? 0), row.buyer_count - (priorRow?.buyer_count ?? 0)];
    }),
    [],
    ["客群定义"],
    ["品牌老客", "分析期开始前曾在目标柜组发生正向购买的会员"],
    ["同部门流入", "分析期开始前未购买目标柜组，但曾在目标柜组所属部门购买的会员"],
    ["跨部门流入", "分析期开始前未在目标部门购买，但曾在门店其他部门购买的会员"],
    ["外部招新", "分析期开始前没有门店正向购买记录的会员"],
    [],
    ["会员等级消费分析"],
    ["会员等级", "本期购买会员", "人数占比", "本期销售收入（元）", "销售占比", "会员人均消费（元）", "消费频次", "同期销售收入（元）"],
    ...current.member_level_consumption.map((row) => {
      const priorRow = prior.member_level_consumption.find((item) => item.level_code === row.level_code);
      return [
        row.level_label,
        row.buyer_count,
        row.buyer_share,
        roundMoney(row.sales_revenue),
        row.sales_share,
        roundMoney(row.spend_per_buyer),
        roundDecimal(row.purchase_frequency),
        roundMoney(priorRow?.sales_revenue ?? 0),
      ];
    }),
    ["说明：会员等级取交易小票 salehead.custtype，按等级内会员去重；期间等级变化的会员可能出现在多个等级。"],
  ];
  const sheet = XLSX.utils.aoa_to_sheet(rows);
  applyBase(sheet, `A1:H${rows.length}`);
  applyTitle(sheet, "H", "会员客群结构", `${report.target.group_name}｜本期与同期客群构成对比`);
  applyTable(sheet, 5, 9, "H");
  styleRange(sheet, "A11:H11", sectionStyle);
  merge(sheet, "A11:H11");
  for (let row = 12; row <= 15; row += 1) {
    merge(sheet, `B${row}:H${row}`);
    styleRange(sheet, `A${row}:H${row}`, { border: thinBottom, alignment: { wrapText: true, vertical: "center" } });
    styleRange(sheet, `A${row}`, { font: { name: FONT_NAME, bold: true, color: { rgb: COLORS.tealDark } } });
  }
  styleRange(sheet, "A17:H17", sectionStyle);
  merge(sheet, "A17:H17");
  applyTable(sheet, 18, 23, "H");
  setNumberFormat(sheet, "B6:B9", COUNT_FORMAT);
  setNumberFormat(sheet, "C6:C9", PERCENT_FORMAT);
  setNumberFormat(sheet, "D6:D9", MONEY_FORMAT);
  setNumberFormat(sheet, "E6:E9", PERCENT_FORMAT);
  setNumberFormat(sheet, "F6:F9", COUNT_FORMAT);
  setNumberFormat(sheet, "G6:G9", MONEY_FORMAT);
  setNumberFormat(sheet, "H6:H9", "+#,##0;[Red]-#,##0;0");
  setNumberFormat(sheet, "B19:B23", COUNT_FORMAT);
  setNumberFormat(sheet, "C19:C23", PERCENT_FORMAT);
  setNumberFormat(sheet, "D19:D23", MONEY_FORMAT);
  setNumberFormat(sheet, "E19:E23", PERCENT_FORMAT);
  setNumberFormat(sheet, "F19:F23", MONEY_FORMAT);
  setNumberFormat(sheet, "G19:G23", "0.00");
  setNumberFormat(sheet, "H19:H23", MONEY_FORMAT);
  merge(sheet, "A24:H24");
  styleRange(sheet, "A24:H24", { font: { name: FONT_NAME, sz: 9, italic: true, color: { rgb: COLORS.muted } }, alignment: { wrapText: true, vertical: "center" } });
  sheet["!cols"] = [{ wch: 18 }, { wch: 14 }, { wch: 14 }, { wch: 18 }, { wch: 14 }, { wch: 14 }, { wch: 18 }, { wch: 14 }];
  return sheet;
}

function createOldCustomerSheet(report: BrandMemberReport) {
  const current = report.target.current.old_customer_funnel;
  const prior = report.target.prior.old_customer_funnel;
  const currentBase = current.historical_target_member_count || 1;
  const priorBase = prior.historical_target_member_count || 1;
  const rows: unknown[][] = [
    ["品牌老客经营漏斗"],
    [],
    [`${report.target.group_name}｜从历史品牌会员到本期回购`],
    [],
    ["阶段", "本期人数", "占历史品牌会员", "同期人数", "同期占比", "沟通解读"],
    ["历史品牌会员", current.historical_target_member_count, 1, prior.historical_target_member_count, 1, "品牌历史会员池"],
    ["到店", current.store_visit_count, current.store_visit_count / currentBase, prior.store_visit_count, prior.store_visit_count / priorBase, "本期在门店发生正向购买"],
    ["到目标部门", current.department_visit_count, current.department_visit_count / currentBase, prior.department_visit_count, prior.department_visit_count / priorBase, "本期回到目标柜组所属部门"],
    ["回购目标柜组", current.target_repurchase_count, current.target_repurchase_count / currentBase, prior.target_repurchase_count, prior.target_repurchase_count / priorBase, "本期再次购买目标柜组"],
    [],
    ["经营提示"],
    [`本期历史品牌会员中已有${current.store_visit_count}人到店、${current.target_repurchase_count}人回购目标柜组。建议优先复盘到店但未回购品牌的会员承接机会。`],
  ];
  const sheet = XLSX.utils.aoa_to_sheet(rows);
  applyBase(sheet, `A1:F${rows.length}`);
  applyTitle(sheet, "F", "品牌老客经营漏斗", `${report.target.group_name}｜从历史品牌会员到本期回购`);
  applyTable(sheet, 5, 9, "F");
  styleRange(sheet, "A11:F11", sectionStyle);
  merge(sheet, "A11:F11");
  merge(sheet, "A12:F12");
  styleRange(sheet, "A12:F12", { fill: { fgColor: { rgb: COLORS.warm } }, alignment: { wrapText: true, vertical: "center" }, border: { left: { style: "medium", color: { rgb: COLORS.amber } } } });
  setNumberFormat(sheet, "B6:B9", COUNT_FORMAT);
  setNumberFormat(sheet, "C6:C9", PERCENT_FORMAT);
  setNumberFormat(sheet, "D6:D9", COUNT_FORMAT);
  setNumberFormat(sheet, "E6:E9", PERCENT_FORMAT);
  sheet["!cols"] = [{ wch: 20 }, { wch: 14 }, { wch: 18 }, { wch: 14 }, { wch: 14 }, { wch: 38 }];
  sheet["!rows"]![11] = { hpt: 38 };
  return sheet;
}

function createInflowSheet(report: BrandMemberReport) {
  const sourceRows = report.target.current.inflow_sources;
  const rows: unknown[][] = [
    ["内部流入来源"],
    [],
    [`${report.target.group_name}｜本期同部门与跨部门流入会员的主要历史来源`],
    [],
    ["流入类型", "来源部门", "来源柜组编码", "来源柜组", "归属会员数", "历史销售收入（元）"],
    ...(sourceRows.length
      ? sourceRows.map((row) => [row.segment_code === "same_department_inflow" ? "同部门流入" : "跨部门流入", row.department_name || "—", row.group_code, row.group_name, row.buyer_count, roundMoney(row.historical_sales)])
      : [["暂无内部流入来源数据", "—", "—", "—", 0, 0]]),
    [],
    ["说明：每位内部流入会员仅归入其历史销售收入最高的一个来源柜组，避免重复计算。"],
  ];
  const sheet = XLSX.utils.aoa_to_sheet(rows);
  applyBase(sheet, `A1:F${rows.length}`);
  applyTitle(sheet, "F", "内部流入来源", `${report.target.group_name}｜本期同部门与跨部门流入会员的主要历史来源`);
  const endRow = 5 + Math.max(sourceRows.length, 1);
  applyTable(sheet, 5, endRow, "F");
  merge(sheet, `A${rows.length}:F${rows.length}`);
  styleRange(sheet, `A${rows.length}:F${rows.length}`, { font: { name: FONT_NAME, sz: 9, italic: true, color: { rgb: COLORS.muted } }, alignment: { wrapText: true } });
  setNumberFormat(sheet, `E6:E${endRow}`, COUNT_FORMAT);
  setNumberFormat(sheet, `F6:F${endRow}`, MONEY_FORMAT);
  sheet["!cols"] = [{ wch: 16 }, { wch: 24 }, { wch: 18 }, { wch: 32 }, { wch: 14 }, { wch: 18 }];
  return sheet;
}

function createCompetitorSheet(report: BrandMemberReport) {
  const rows: unknown[][] = [
    ["竞品柜组对比"],
    [],
    [`${report.target.group_name}｜本期与同期经营指标对比`],
    [],
    ["竞品柜组", "所属部门", "本期销售收入（元）", "同期销售收入（元）", "本期购买会员数", "同期购买会员数", "本期会员人均消费（元）", "本期会员消费频次"],
    ...report.competitors.map((row) => [row.group_name, row.department_name || "—", roundMoney(row.current.sales_revenue), roundMoney(row.prior.sales_revenue), row.current.member_buyer_count, row.prior.member_buyer_count, roundMoney(row.current.spend_per_buyer), roundDecimal(row.current.purchase_frequency)]),
  ];
  const sheet = XLSX.utils.aoa_to_sheet(rows);
  applyBase(sheet, `A1:H${rows.length}`);
  applyTitle(sheet, "H", "竞品柜组对比", `${report.target.group_name}｜本期与同期经营指标对比`);
  applyTable(sheet, 5, rows.length, "H");
  setNumberFormat(sheet, `C6:D${rows.length}`, MONEY_FORMAT);
  setNumberFormat(sheet, `E6:F${rows.length}`, COUNT_FORMAT);
  setNumberFormat(sheet, `G6:G${rows.length}`, MONEY_FORMAT);
  setNumberFormat(sheet, `H6:H${rows.length}`, "0.00");
  sheet["!cols"] = [{ wch: 30 }, { wch: 24 }, { wch: 18 }, { wch: 18 }, { wch: 16 }, { wch: 16 }, { wch: 20 }, { wch: 20 }];
  return sheet;
}

function createDefinitionsSheet(report: BrandMemberReport) {
  const rows: unknown[][] = [
    ["数据口径说明"],
    [],
    ["供应商沟通版｜汇总数据口径与使用边界"],
    [],
    ["口径项", "供应商沟通口径", "数据范围", "备注"],
    ["销售收入", "目标柜组销售与退货的净额", "所选本期 / 同期", "退货按负数计入"],
    ["购买会员数", "期间在目标柜组至少发生一笔正向购买的会员数", "所选本期 / 同期", "按会员去重"],
    ["会员历史身份", "分别追溯至各分析期开始日期之前的全部门店消费历史", "分析期开始前", "用于划分品牌老客与流入客群"],
    ["内部流入", "包含同部门流入与跨部门流入", "目标门店", "同一会员仅归入一个客群"],
    [],
    ["隐私说明"],
    ["本报告仅使用汇总指标，不包含会员姓名、手机号、会员卡号或其他个人识别信息。"],
    ["数据来源", "ShopView 销售及会员交易汇总数据"],
    ["目标柜组", `${report.target.group_name}（${report.target.group_code}）`],
  ];
  const sheet = XLSX.utils.aoa_to_sheet(rows);
  applyBase(sheet, `A1:D${rows.length}`);
  applyTitle(sheet, "D", "数据口径说明", "供应商沟通版｜汇总数据口径与使用边界");
  applyTable(sheet, 5, 9, "D");
  styleRange(sheet, "A11:D11", sectionStyle);
  merge(sheet, "A11:D11");
  merge(sheet, "A12:D12");
  merge(sheet, "B13:D13");
  merge(sheet, "B14:D14");
  styleRange(sheet, "A12:D12", { fill: { fgColor: { rgb: COLORS.tealPale } }, alignment: { wrapText: true, vertical: "center" }, border: { left: { style: "medium", color: { rgb: COLORS.teal } } } });
  for (const row of [13, 14]) {
    styleRange(sheet, `A${row}`, { font: { name: FONT_NAME, bold: true, color: { rgb: COLORS.muted } } });
    styleRange(sheet, `A${row}:D${row}`, { border: thinBottom, alignment: { wrapText: true, vertical: "center" } });
  }
  sheet["!cols"] = [{ wch: 18 }, { wch: 46 }, { wch: 22 }, { wch: 28 }];
  sheet["!rows"]![11] = { hpt: 38 };
  return sheet;
}

export function buildSupplierWorkbook(report: BrandMemberReport, storeName: string, conclusion?: string) {
  const workbook = XLSX.utils.book_new();
  workbook.Props = {
    Title: `${report.target.group_name} 品牌会员经营沟通简报`,
    Subject: "品牌供应商经营沟通材料",
    Author: "ShopView",
    Company: storeName,
    Comments: "仅包含汇总经营数据，不含会员个人信息。",
    CreatedDate: new Date(),
  };
  XLSX.utils.book_append_sheet(workbook, createOverviewSheet(report, storeName, conclusion), "经营摘要");
  XLSX.utils.book_append_sheet(workbook, createMemberStructureSheet(report), "会员结构");
  XLSX.utils.book_append_sheet(workbook, createOldCustomerSheet(report), "老客经营");
  XLSX.utils.book_append_sheet(workbook, createInflowSheet(report), "流入来源");
  if (report.competitors.length) XLSX.utils.book_append_sheet(workbook, createCompetitorSheet(report), "竞品对比");
  XLSX.utils.book_append_sheet(workbook, createDefinitionsSheet(report), "数据口径");
  return workbook;
}

export function exportSupplierWorkbook(report: BrandMemberReport, storeName: string, conclusion?: string) {
  const workbook = buildSupplierWorkbook(report, storeName, conclusion);
  const current = report.target.current;
  XLSX.writeFile(
    workbook,
    `品牌经营沟通简报_${cleanFilePart(storeName)}_${cleanFilePart(report.target.group_name)}_${current.period.start_date}_${current.period.end_date}.xlsx`,
    { compression: true, cellStyles: true },
  );
}
