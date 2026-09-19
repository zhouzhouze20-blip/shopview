import XLSX from "xlsx-js-style";

export interface CampaignMetricSet {
  sales_amount: number;
  ticket_count: number;
  average_ticket: number | null;
  member_sales_amount: number;
  member_ticket_count: number;
  consuming_member_count: number;
  member_average_ticket: number | null;
  member_spend: number | null;
  member_sales_share: number | null;
  new_member_count: number;
  new_member_consuming_count: number;
  new_member_sales_amount: number;
  new_member_conversion: number | null;
}

export interface CampaignDashboard {
  scope: Record<string, string>;
  quality: Record<string, string | number | null>;
  overview: {
    current: CampaignMetricSet;
    comparison: CampaignMetricSet;
    change_percent: Record<string, number | null>;
  };
  daily_sales: Array<Record<string, string | number>>;
  recharge: {
    summary: Record<string, number>;
    details: Array<Record<string, string | number | null>>;
  };
  gift_redemption: {
    summary: Record<string, number | null>;
    daily: Array<Record<string, string | number>>;
    templates: Array<Record<string, string | number>>;
    details: Array<Record<string, string | number | null>>;
  };
  definitions: Record<string, string>;
}

const THEME = {
  primary: "1D4ED8",
  primaryDark: "1E3A8A",
  primaryLight: "DBEAFE",
  header: "2563EB",
  stripe: "F8FAFC",
  border: "CBD5E1",
  text: "0F172A",
  muted: "64748B",
  rise: "DC2626",
  fall: "16A34A",
} as const;

const NUMBER_FORMATS = {
  money: '"¥"#,##0.00;[Green]-"¥"#,##0.00;"¥"0.00',
  integer: '#,##0;[Green]-#,##0;0',
  percent: '0.0%;[Green]-0.0%;0.0%',
  date: 'yyyy-mm-dd',
  datetime: 'yyyy-mm-dd hh:mm',
  text: '@',
} as const;

type ColumnFormat = keyof typeof NUMBER_FORMATS;

interface SheetStyleOptions {
  title: string;
  subtitle: string;
  widths: number[];
  formats?: Record<string, ColumnFormat>;
  rowFormats?: Record<string, ColumnFormat>;
  trendColumn?: string;
  autoFilter?: boolean;
  wrapColumns?: string[];
}

function asNumber(value: unknown) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function asPercent(value: unknown) {
  const parsed = asNumber(value);
  return parsed === null ? null : parsed / 100;
}

function asDate(value: unknown, includeTime = false) {
  if (typeof value !== "string" || !value) return value ?? null;
  const matched = value.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (!matched) return value;
  return new Date(
    Number(matched[1]),
    Number(matched[2]) - 1,
    Number(matched[3]),
    includeTime ? Number(matched[4] || 0) : 0,
    includeTime ? Number(matched[5] || 0) : 0,
    includeTime ? Number(matched[6] || 0) : 0,
  );
}

export function filterGiftRedemptionDetails(
  details: CampaignDashboard["gift_redemption"]["details"],
  templateId: string,
) {
  if (templateId === "all") return details;
  return details.filter((row) => String(row.template_id) === templateId);
}

function appendSheet(
  workbook: XLSX.WorkBook,
  rows: Array<Record<string, unknown>>,
  name: string,
  options: SheetStyleOptions,
) {
  const sourceRows = rows.length ? rows : [{ 提示: "暂无数据" }];
  const headers = Object.keys(sourceRows[0]);
  const values = [
    [options.title, ...headers.slice(1).map(() => "")],
    [options.subtitle, ...headers.slice(1).map(() => "")],
    headers.map(() => ""),
    headers,
    ...sourceRows.map((row) => headers.map((header) => row[header] ?? null)),
  ];
  const worksheet = XLSX.utils.aoa_to_sheet(values, { cellDates: true });
  const lastColumn = Math.max(0, headers.length - 1);
  const lastRow = values.length - 1;

  worksheet["!merges"] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: lastColumn } },
    { s: { r: 1, c: 0 }, e: { r: 1, c: lastColumn } },
  ];
  worksheet["!cols"] = options.widths.map((wch) => ({ wch }));
  worksheet["!rows"] = values.map((_, rowIndex) => ({
    hpt: rowIndex === 0 ? 30 : rowIndex === 1 ? 34 : rowIndex === 2 ? 8 : rowIndex === 3 ? 26 : 22,
  }));
  worksheet["!freeze"] = { xSplit: 0, ySplit: 4 };
  worksheet["!margins"] = { left: 0.3, right: 0.3, top: 0.5, bottom: 0.5, header: 0.2, footer: 0.2 };
  if (options.autoFilter !== false) {
    worksheet["!autofilter"] = {
      ref: XLSX.utils.encode_range({ r: 3, c: 0 }, { r: lastRow, c: lastColumn }),
    };
  }

  const lightBottomBorder = { bottom: { style: "thin", color: { rgb: THEME.border } } };
  for (let rowIndex = 0; rowIndex <= lastRow; rowIndex += 1) {
    for (let columnIndex = 0; columnIndex <= lastColumn; columnIndex += 1) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      if (!worksheet[address]) worksheet[address] = { t: "s", v: "" };
      const cell = worksheet[address];
      if (rowIndex === 0) {
        cell.s = {
          fill: { patternType: "solid", fgColor: { rgb: THEME.primaryDark } },
          font: { name: "Microsoft YaHei", sz: 16, bold: true, color: { rgb: "FFFFFF" } },
          alignment: { horizontal: "left", vertical: "center", wrapText: true },
        };
      } else if (rowIndex === 1) {
        cell.s = {
          fill: { patternType: "solid", fgColor: { rgb: THEME.primaryLight } },
          font: { name: "Microsoft YaHei", sz: 10, color: { rgb: THEME.primaryDark } },
          alignment: { horizontal: "left", vertical: "center" },
        };
      } else if (rowIndex === 3) {
        cell.s = {
          fill: { patternType: "solid", fgColor: { rgb: THEME.header } },
          font: { name: "Microsoft YaHei", sz: 10, bold: true, color: { rgb: "FFFFFF" } },
          alignment: { horizontal: "center", vertical: "center", wrapText: true },
          border: lightBottomBorder,
        };
      } else if (rowIndex >= 4) {
        const header = headers[columnIndex];
        const metricName = String(sourceRows[rowIndex - 4]?.[headers[0]] ?? "");
        const format = options.formats?.[header] || (columnIndex > 0 ? options.rowFormats?.[metricName] : undefined);
        const numeric = format === "money" || format === "integer" || format === "percent";
        const wrapped = options.wrapColumns?.includes(header) || false;
        cell.s = {
          fill: { patternType: "solid", fgColor: { rgb: rowIndex % 2 === 0 ? "FFFFFF" : THEME.stripe } },
          font: { name: "Microsoft YaHei", sz: 10, color: { rgb: THEME.text } },
          alignment: {
            horizontal: numeric ? "right" : format === "date" || format === "datetime" ? "center" : "left",
            vertical: "center",
            wrapText: wrapped,
          },
          border: lightBottomBorder,
        };
        if (format) cell.z = NUMBER_FORMATS[format];
        if (header === options.trendColumn && typeof cell.v === "number") {
          cell.s.font = {
            ...cell.s.font,
            bold: true,
            color: { rgb: cell.v > 0 ? THEME.rise : cell.v < 0 ? THEME.fall : THEME.muted },
          };
        }
      }
    }
  }
  XLSX.utils.book_append_sheet(workbook, worksheet, name);
}

export function buildNewCenturyCampaignWorkbook(report: CampaignDashboard) {
  const workbook = XLSX.utils.book_new();
  const storeName = report.scope.store_name || "常州新世纪商城（603）";
  const periodLabel = `活动期 ${report.scope.start_date} 至 ${report.scope.end_date}｜同期 ${report.scope.compare_start_date} 至 ${report.scope.compare_end_date}`;
  workbook.Props = {
    Title: `新世纪整体活动分析 ${report.scope.start_date} 至 ${report.scope.end_date}`,
    Subject: "销售、会员、增值及礼品券核销分析",
    Author: "ShopView",
    Company: "常州新世纪商城",
  };
  const overview = [
    { 指标: "销售额", 活动期: asNumber(report.overview.current.sales_amount), 同期: asNumber(report.overview.comparison.sales_amount), 同比: asPercent(report.overview.change_percent.sales_amount) },
    { 指标: "小票数", 活动期: asNumber(report.overview.current.ticket_count), 同期: asNumber(report.overview.comparison.ticket_count), 同比: asPercent(report.overview.change_percent.ticket_count) },
    { 指标: "客单价", 活动期: asNumber(report.overview.current.average_ticket), 同期: asNumber(report.overview.comparison.average_ticket), 同比: asPercent(report.overview.change_percent.average_ticket) },
    { 指标: "会员消费人数", 活动期: asNumber(report.overview.current.consuming_member_count), 同期: asNumber(report.overview.comparison.consuming_member_count), 同比: asPercent(report.overview.change_percent.consuming_member_count) },
    { 指标: "会员消费额", 活动期: asNumber(report.overview.current.member_sales_amount), 同期: asNumber(report.overview.comparison.member_sales_amount), 同比: asPercent(report.overview.change_percent.member_sales_amount) },
    { 指标: "招新人数", 活动期: asNumber(report.overview.current.new_member_count), 同期: asNumber(report.overview.comparison.new_member_count), 同比: asPercent(report.overview.change_percent.new_member_count) },
  ];
  const dailySales = report.daily_sales.map((row) => ({
    日期: asDate(row.business_date),
    销售额: asNumber(row.sales_amount),
    小票数: asNumber(row.ticket_count),
    会员消费人数: asNumber(row.member_count),
  }));
  const rechargeSummary = [
    { 指标: "增值面值", 数值: asNumber(report.recharge.summary.increase_face_amount) },
    { 指标: "冲正/退值", 数值: asNumber(report.recharge.summary.reversal_face_amount) },
    { 指标: "净增值", 数值: asNumber(report.recharge.summary.net_face_amount) },
    { 指标: "涉及会员", 数值: asNumber(report.recharge.summary.member_count) },
    { 指标: "日志笔数", 数值: asNumber(report.recharge.summary.flow_count) },
  ];
  const rechargeDetails = report.recharge.details.map((row) => ({
    日期: asDate(row.business_date),
    会员号: row.member_no,
    券种编码: row.coupon_type,
    券种名称: row.coupon_name,
    动作: row.action_name,
    来源: row.source_name,
    面值: asNumber(row.face_amount),
    流水号: String(row.sequence_no ?? ""),
  }));
  const giftSummary = [
    { 指标: "礼品券核销张数", 数值: asNumber(report.gift_redemption.summary.redemption_count) },
    { 指标: "核销会员日", 数值: asNumber(report.gift_redemption.summary.member_day_count) },
    { 指标: "有消费会员日", 数值: asNumber(report.gift_redemption.summary.consuming_member_day_count) },
    { 指标: "同日消费转化率", 数值: asPercent(report.gift_redemption.summary.conversion_rate) },
    { 指标: "同日小票数", 数值: asNumber(report.gift_redemption.summary.same_day_ticket_count) },
    { 指标: "同日消费额", 数值: asNumber(report.gift_redemption.summary.same_day_sales_amount) },
    { 指标: "消费会员客单", 数值: asNumber(report.gift_redemption.summary.spend_per_consumer) },
    { 指标: "未匹配会员核销数", 数值: asNumber(report.gift_redemption.summary.unmatched_redemption_count) },
  ];
  const giftTemplates = report.gift_redemption.templates.map((row) => ({
    礼品券模板ID: String(row.template_id ?? ""),
    礼品券: row.gift_name,
    核销张数: row.redemption_count,
    核销会员数: row.member_count,
    有消费核销数: row.consuming_redemption_count,
  }));
  const giftDetails = report.gift_redemption.details.map((row) => ({
    核销时间: asDate(row.used_date_time, true),
    礼品券: row.gift_name,
    礼品券模板ID: String(row.template_id ?? ""),
    券码: row.coupon_code,
    会员号: row.member_no,
    手机号: row.mobile,
    等级: row.level_code,
    券金额: asNumber(row.coupon_money),
    同日小票数: asNumber(row.same_day_ticket_count),
    同日消费额: asNumber(row.same_day_sales_amount),
  }));
  const definitions = [
    { 项目: "门店", 说明: report.scope.store_name || "常州新世纪商城（603）" },
    { 项目: "活动期", 说明: `${report.scope.start_date} 至 ${report.scope.end_date}` },
    { 项目: "同期", 说明: `${report.scope.compare_start_date} 至 ${report.scope.compare_end_date}` },
    { 项目: "卡券数据质量", 说明: report.quality.message },
    ...Object.entries(report.definitions).map(([item, description]) => ({ 项目: item, 说明: description })),
  ];

  appendSheet(workbook, overview, "活动总览", {
    title: "新世纪活动分析｜活动总览",
    subtitle: `${storeName}｜${periodLabel}｜同比：上涨红色、下跌绿色`,
    widths: [22, 18, 18, 16],
    formats: { 同比: "percent" },
    rowFormats: {
      销售额: "money",
      小票数: "integer",
      客单价: "money",
      会员消费人数: "integer",
      会员消费额: "money",
      招新人数: "integer",
    },
    trendColumn: "同比",
  });
  appendSheet(workbook, dailySales, "逐日销售", {
    title: "新世纪活动分析｜逐日销售",
    subtitle: `${storeName}｜${periodLabel}`,
    widths: [15, 20, 14, 18],
    formats: { 日期: "date", 销售额: "money", 小票数: "integer", 会员消费人数: "integer" },
  });
  appendSheet(workbook, rechargeSummary, "增值汇总", {
    title: "新世纪活动分析｜增值汇总",
    subtitle: `${storeName}｜${periodLabel}｜m/M 为增值，n/N/w 为冲正或退值`,
    widths: [26, 20],
    rowFormats: {
      增值面值: "money",
      "冲正/退值": "money",
      净增值: "money",
      涉及会员: "integer",
      日志笔数: "integer",
    },
  });
  appendSheet(workbook, rechargeDetails, "增值明细", {
    title: "新世纪活动分析｜增值明细",
    subtitle: `${storeName}｜${periodLabel}｜共 ${rechargeDetails.length.toLocaleString("zh-CN")} 条`,
    widths: [15, 24, 16, 30, 14, 16, 16, 24],
    formats: { 日期: "date", 会员号: "text", 券种编码: "text", 面值: "money", 流水号: "text" },
  });
  appendSheet(workbook, giftSummary, "礼品券整体汇总", {
    title: "新世纪活动分析｜礼品券整体汇总",
    subtitle: `${storeName}｜${periodLabel}｜gift 类型礼品券`,
    widths: [28, 20],
    rowFormats: {
      礼品券核销张数: "integer",
      核销会员日: "integer",
      有消费会员日: "integer",
      同日消费转化率: "percent",
      同日小票数: "integer",
      同日消费额: "money",
      消费会员客单: "money",
      未匹配会员核销数: "integer",
    },
  });
  appendSheet(workbook, giftTemplates, "礼品券类型汇总", {
    title: "新世纪活动分析｜礼品券类型汇总",
    subtitle: `${storeName}｜${periodLabel}｜共 ${giftTemplates.length.toLocaleString("zh-CN")} 种礼品券`,
    widths: [22, 42, 14, 16, 18],
    formats: { 礼品券模板ID: "text", 核销张数: "integer", 核销会员数: "integer", 有消费核销数: "integer" },
  });
  appendSheet(workbook, giftDetails, "礼品券核销消费明细", {
    title: "新世纪活动分析｜礼品券核销消费明细",
    subtitle: `${storeName}｜${periodLabel}｜共 ${giftDetails.length.toLocaleString("zh-CN")} 条`,
    widths: [21, 42, 22, 26, 24, 20, 12, 16, 14, 18],
    formats: { 核销时间: "datetime", 礼品券模板ID: "text", 券码: "text", 会员号: "text", 手机号: "text", 券金额: "money", 同日小票数: "integer", 同日消费额: "money" },
  });
  appendSheet(workbook, definitions, "数据口径", {
    title: "新世纪活动分析｜数据口径",
    subtitle: `${storeName}｜导出时间 ${new Date().toLocaleString("zh-CN", { hour12: false })}`,
    widths: [26, 96],
    autoFilter: false,
    wrapColumns: ["说明"],
  });
  return workbook;
}

export function exportNewCenturyCampaign(report: CampaignDashboard) {
  XLSX.writeFile(
    buildNewCenturyCampaignWorkbook(report),
    `新世纪整体活动分析_${report.scope.start_date}_${report.scope.end_date}.xlsx`,
  );
}
