import type {
  DailyFollowupMetric,
  DailyFollowupResponse,
  DailyFollowupRow,
} from "./daily-followup-report";

export type DailyFollowupMetricView = "sales" | "profit";

export type DailyFollowupExportOptions = {
  metricView: DailyFollowupMetricView;
  rows?: DailyFollowupRow[];
};

export type DailyFollowupExportData = {
  currentViewRows: Array<Array<string | number>>;
  detailRows: Array<Array<string | number>>;
  currentHeaderRow: number;
  filename: string;
  sheetName: string;
};

export type DailyFollowupTrackingSheetData = {
  rows: Array<Array<string | number>>;
  headerRows: [number, number];
  fixedColumnCount: number;
  metricColumnsPerDay: number;
  sheetName: string;
};

export type DailyFollowupWorkbookData = {
  trackingSheet: DailyFollowupTrackingSheetData;
  trackingSheets: DailyFollowupTrackingSheetData[];
  viewSheets: DailyFollowupExportData[];
  detailRows: Array<Array<string | number>>;
  detailSheetName: string;
  filename: string;
};

export const DAILY_FOLLOWUP_AMOUNT_FORMAT = "#,##0.00";
export const DAILY_FOLLOWUP_PERCENT_FORMAT = "0.0%";
export const DAILY_FOLLOWUP_SIGNED_PERCENT_FORMAT = "+0.0%;[Red]-0.0%;0.0%";
export const DAILY_FOLLOWUP_GROWTH_COLOR = "DC2626";
export const DAILY_FOLLOWUP_DECLINE_COLOR = "059669";
const DAILY_FOLLOWUP_REPORT_NAME = "OD0001 销售逐日跟进表";
const TRACKING_METRIC_HEADERS = [
  "本期销售",
  "同期销售",
  "销售同比",
  "本期毛利",
  "同期毛利",
  "毛利同比",
  "本期毛利率",
  "同期毛利率",
  "毛利率同比",
];

export function dailyFollowupTrendColor(value: unknown): string | undefined {
  if (typeof value !== "number" || value === 0) return undefined;
  return value > 0
    ? DAILY_FOLLOWUP_GROWTH_COLOR
    : DAILY_FOLLOWUP_DECLINE_COLOR;
}

const metricLabel = (view: DailyFollowupMetricView) =>
  view === "sales" ? "销售收入" : "毛利";

const dimensionLabel = (dimension: DailyFollowupResponse["dimension"]) => {
  if (dimension === "departments") return "部门逐日";
  if (dimension === "special_sales") return "特卖逐日";
  return "柜组逐日";
};

const metricCurrent = (metric: DailyFollowupMetric, view: DailyFollowupMetricView) =>
  view === "sales" ? metric.sales_current : metric.profit_current;

const toWan = (value: number | null | undefined) =>
  Math.round((Number(value ?? 0) / 10_000) * 1_000_000) / 1_000_000;

const formatExportDate = (value: string) => {
  const match = /^\d{4}-(\d{2})-(\d{2})$/.exec(value);
  return match ? `${match[1]}-${match[2]}` : value;
};

const cumulativeDateRange = (report: DailyFollowupResponse) =>
  report.cumulative_dates ?? report.dates;

const safeFilenamePart = (value: string) => value.replace(/[/\\?%*:|"<>]/g, "_");

function organizationLabel(row: DailyFollowupRow, showStore: boolean): string {
  const name = row.dimension_name || row.dimension_code || "未匹配";
  return showStore && row.store_code ? `${row.store_code} · ${name}` : name;
}

function dayTotals(
  rows: DailyFollowupRow[],
  dayIndex: number,
  view: DailyFollowupMetricView,
): number {
  return rows.reduce(
    (sum, row) => sum + metricCurrent(row.daily[dayIndex], view),
    0,
  );
}

function rowTotal(row: DailyFollowupRow, view: DailyFollowupMetricView): number {
  return metricCurrent(row.totals, view);
}

type DailyFollowupAmounts = {
  salesCurrent: number;
  salesPrior: number;
  profitCurrent: number;
  profitPrior: number;
};

const emptyAmounts = (): DailyFollowupAmounts => ({
  salesCurrent: 0,
  salesPrior: 0,
  profitCurrent: 0,
  profitPrior: 0,
});

function addMetric(
  amounts: DailyFollowupAmounts,
  metric: DailyFollowupMetric | undefined,
): void {
  if (!metric) return;
  amounts.salesCurrent += Number(metric.sales_current ?? 0);
  amounts.salesPrior += Number(metric.sales_prior ?? 0);
  amounts.profitCurrent += Number(metric.profit_current ?? 0);
  amounts.profitPrior += Number(metric.profit_prior ?? 0);
}

function metricFromAmounts(amounts: DailyFollowupAmounts): DailyFollowupMetric {
  const marginCurrent = amounts.salesCurrent === 0
    ? null
    : amounts.profitCurrent / amounts.salesCurrent;
  const marginPrior = amounts.salesPrior === 0
    ? null
    : amounts.profitPrior / amounts.salesPrior;
  return {
    sales_current: amounts.salesCurrent,
    sales_prior: amounts.salesPrior,
    sales_yoy: amounts.salesPrior === 0
      ? null
      : amounts.salesCurrent / amounts.salesPrior - 1,
    profit_current: amounts.profitCurrent,
    profit_prior: amounts.profitPrior,
    profit_yoy: amounts.profitPrior === 0
      ? null
      : amounts.profitCurrent / amounts.profitPrior - 1,
    margin_current: marginCurrent,
    margin_prior: marginPrior,
    margin_change: marginCurrent === null || marginPrior === null
      ? null
      : marginCurrent - marginPrior,
  };
}

function aggregateGroupRowsByArea(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[],
): DailyFollowupRow[] {
  const grouped = new Map<string, {
    storeCode: string | null;
    storeName: string | null;
    areaName: string;
    daily: DailyFollowupAmounts[];
    totals: DailyFollowupAmounts;
  }>();

  for (const row of rows) {
    const storeCode = row.store_code ?? null;
    const storeName = row.store_name ?? null;
    const areaName = row.area_name || "未匹配";
    const key = JSON.stringify([storeCode ?? "", areaName]);
    let area = grouped.get(key);
    if (!area) {
      area = {
        storeCode,
        storeName,
        areaName,
        daily: report.days.map(() => emptyAmounts()),
        totals: emptyAmounts(),
      };
      grouped.set(key, area);
    }
    row.daily.forEach((metric, index) => addMetric(area.daily[index], metric));
    addMetric(area.totals, row.totals);
  }

  return Array.from(grouped.values())
    .sort((left, right) => (
      `${left.storeName ?? left.storeCode ?? ""}\u0000${left.areaName}`
        .localeCompare(
          `${right.storeName ?? right.storeCode ?? ""}\u0000${right.areaName}`,
          "zh-CN",
        )
    ))
    .map((area) => ({
      store_code: area.storeCode,
      store_name: area.storeName,
      department_code: null,
      department_name: null,
      area_name: area.areaName,
      category_name: null,
      operation_method: null,
      dimension_code: area.areaName,
      dimension_name: area.areaName,
      daily: area.daily.map((amounts, index) => ({
        ...metricFromAmounts(amounts),
        date: report.days[index]?.date ?? "",
        prior_date: report.days[index]?.prior_date ?? "",
      })),
      totals: metricFromAmounts(area.totals),
    }));
}

function trackingDayTotals(
  rows: DailyFollowupRow[],
  dayIndex: number,
): Array<string | number> {
  const totals = rows.reduce(
    (result, row) => {
      const metric = row.daily[dayIndex];
      if (!metric) return result;
      result.salesCurrent += Number(metric.sales_current ?? 0);
      result.salesPrior += Number(metric.sales_prior ?? 0);
      result.profitCurrent += Number(metric.profit_current ?? 0);
      result.profitPrior += Number(metric.profit_prior ?? 0);
      return result;
    },
    {
      salesCurrent: 0,
      salesPrior: 0,
      profitCurrent: 0,
      profitPrior: 0,
    },
  );
  return trackingMetricValues(metricFromAmounts(totals));
}

function trackingCumulativeTotals(
  rows: DailyFollowupRow[],
): Array<string | number> {
  const totals = rows.reduce((result, row) => {
    addMetric(result, row.totals);
    return result;
  }, emptyAmounts());
  const metric = metricFromAmounts(totals);
  return trackingMetricValues(metric);
}

function trackingMetricValues(
  metric: DailyFollowupMetric,
): Array<string | number> {
  return [
    toWan(metric.sales_current),
    toWan(metric.sales_prior),
    metric.sales_yoy ?? "",
    toWan(metric.profit_current),
    toWan(metric.profit_prior),
    metric.profit_yoy ?? "",
    metric.margin_current ?? "",
    metric.margin_prior ?? "",
    metric.margin_change ?? "",
  ];
}

function currentViewTable(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[],
  view: DailyFollowupMetricView,
): Array<Array<string | number>> {
  const cumulativeDates = cumulativeDateRange(report);
  const title = `${DAILY_FOLLOWUP_REPORT_NAME} · ${dimensionLabel(report.dimension)} · ${metricLabel(view)}`;
  const metadata = [
    "财务月",
    report.financial_month,
    "本期范围",
    `${cumulativeDates.start_date} 至 ${cumulativeDates.end_date}`,
    "同期范围",
    `${cumulativeDates.prior_start_date} 至 ${cumulativeDates.prior_end_date}`,
    "金额单位",
    "万元",
  ];
  const scope = ["数据范围", report.scope_description || "当前查询权限范围"];

  if (report.dimension === "departments") {
    const showStore = new Set(rows.map((row) => row.store_code).filter(Boolean)).size > 1;
    const header = [
      "日期",
      "同期日期",
      ...rows.map((row) => organizationLabel(row, showStore)),
      "合计",
    ];
    const body = report.days.map((day, dayIndex) => [
      day.date,
      day.prior_date,
      ...rows.map((row) => toWan(metricCurrent(row.daily[dayIndex], view))),
      toWan(dayTotals(rows, dayIndex, view)),
    ]);
    const footer = [
      "累计",
      "",
      ...rows.map((row) => toWan(rowTotal(row, view))),
      toWan(rows.reduce((sum, row) => sum + rowTotal(row, view), 0)),
    ];
    return [[title], metadata, scope, header, ...body, footer];
  }

  const header = [
    "门店",
    "部门",
    "柜组编码",
    "柜组名称",
    ...report.days.map((day) => formatExportDate(day.date)),
    "合计",
  ];
  const body = rows.map((row) => [
    row.store_name || row.store_code || "未匹配",
    row.department_name || row.department_code || "未匹配",
    row.dimension_code || "",
    row.dimension_name || "未匹配",
    ...row.daily.map((day) => toWan(metricCurrent(day, view))),
    toWan(rowTotal(row, view)),
  ]);
  const footer = [
    "合计",
    "",
    "",
    "",
    ...report.days.map((_, dayIndex) => toWan(dayTotals(rows, dayIndex, view))),
    toWan(rows.reduce((sum, row) => sum + rowTotal(row, view), 0)),
  ];
  return [[title], metadata, scope, header, ...body, footer];
}

function detailTable(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[],
): Array<Array<string | number>> {
  const header = [
    "日期",
    "同期日期",
    "门店编码",
    "门店名称",
    "部门编码",
    "部门名称",
    report.dimension === "groups" ? "柜组编码" : "统计编码",
    report.dimension === "groups" ? "柜组名称" : "统计名称",
    "本期销售（万元）",
    "同期销售（万元）",
    "销售同比",
    "本期毛利（万元）",
    "同期毛利（万元）",
    "毛利同比",
    "本期毛利率",
    "同期毛利率",
    "毛利率变动",
  ];
  const body = rows.flatMap((row) =>
    row.daily.map((day) => [
      day.date,
      day.prior_date,
      row.store_code || "",
      row.store_name || "",
      row.department_code || "",
      row.department_name || "",
      row.dimension_code || "",
      row.dimension_name || "",
      toWan(day.sales_current),
      toWan(day.sales_prior),
      day.sales_yoy ?? "",
      toWan(day.profit_current),
      toWan(day.profit_prior),
      day.profit_yoy ?? "",
      day.margin_current ?? "",
      day.margin_prior ?? "",
      day.margin_change ?? "",
    ]),
  );
  return [header, ...body];
}

function trackingTable(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[],
): Array<Array<string | number>> {
  const cumulativeDates = cumulativeDateRange(report);
  const title = `${DAILY_FOLLOWUP_REPORT_NAME} · ${dimensionLabel(report.dimension)}`;
  const financialMonth = ["财务月", report.financial_month, "金额单位", "万元"];
  const currentRange = [
    "本期范围",
    `${cumulativeDates.start_date} 至 ${cumulativeDates.end_date}`,
  ];
  const priorRange = [
    "同期范围",
    `${cumulativeDates.prior_start_date} 至 ${cumulativeDates.prior_end_date}`,
  ];
  const scope = ["数据范围", report.scope_description || "当前查询权限范围"];
  const metricHeaders = TRACKING_METRIC_HEADERS;

  if (report.dimension === "departments") {
    const fixedHeaders = ["门店", "部门"];
    const topHeader = [
      ...fixedHeaders.map(() => ""),
      "累计",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      ...report.days.flatMap((day) => [
        formatExportDate(day.date),
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
      ]),
    ];
    const subHeader = [
      ...fixedHeaders,
      ...metricHeaders,
      ...report.days.flatMap(() => metricHeaders),
    ];
    const body = rows.map((row) => [
      row.store_name || row.store_code || "未匹配",
      row.department_name || row.department_code || "未匹配",
      ...trackingMetricValues(row.totals),
      ...row.daily.flatMap((day) => trackingMetricValues(day)),
    ]);
    const total = [
      "合计",
      "",
      ...trackingCumulativeTotals(rows),
      ...report.days.flatMap((_, dayIndex) => trackingDayTotals(rows, dayIndex)),
    ];
    return [
      [title],
      financialMonth,
      currentRange,
      priorRange,
      scope,
      topHeader,
      subHeader,
      ...body,
      total,
    ];
  }

  const fixedHeaders = ["门店", "部门", "区域", "类别", "经营方式", "柜组名称"];
  const topHeader = [
    ...fixedHeaders.map(() => ""),
    "累计",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    ...report.days.flatMap((day) => [
      formatExportDate(day.date),
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
    ]),
  ];
  const subHeader = [
    ...fixedHeaders,
    ...metricHeaders,
    ...report.days.flatMap(() => metricHeaders),
  ];
  const body = rows.map((row) => [
    row.store_name || row.store_code || "未匹配",
    row.department_name || row.department_code || "未匹配",
    row.area_name || "未匹配",
    row.category_name || "未匹配",
    row.operation_method || "未匹配",
    row.dimension_name || "未匹配",
    ...trackingMetricValues(row.totals),
    ...row.daily.flatMap((day) => trackingMetricValues(day)),
  ]);
  const total = [
    "合计",
    "",
    "",
    "",
    "",
    "",
    ...trackingCumulativeTotals(rows),
    ...report.days.flatMap((_, dayIndex) => trackingDayTotals(rows, dayIndex)),
  ];
  return [
    [title],
    financialMonth,
    currentRange,
    priorRange,
    scope,
    topHeader,
    subHeader,
    ...body,
    total,
  ];
}

function areaTrackingTable(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[],
): Array<Array<string | number>> {
  const cumulativeDates = cumulativeDateRange(report);
  const title = `${DAILY_FOLLOWUP_REPORT_NAME} · 区域逐日`;
  const financialMonth = ["财务月", report.financial_month, "金额单位", "万元"];
  const currentRange = [
    "本期范围",
    `${cumulativeDates.start_date} 至 ${cumulativeDates.end_date}`,
  ];
  const priorRange = [
    "同期范围",
    `${cumulativeDates.prior_start_date} 至 ${cumulativeDates.prior_end_date}`,
  ];
  const scope = ["数据范围", report.scope_description || "当前查询权限范围"];
  const fixedHeaders = ["门店", "区域"];
  const metricHeaders = TRACKING_METRIC_HEADERS;
  const topHeader = [
    ...fixedHeaders.map(() => ""),
    "累计",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    ...report.days.flatMap((day) => [
      formatExportDate(day.date),
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
    ]),
  ];
  const subHeader = [
    ...fixedHeaders,
    ...metricHeaders,
    ...report.days.flatMap(() => metricHeaders),
  ];
  const body = rows.map((row) => [
    row.store_name || row.store_code || "未匹配",
    row.area_name || "未匹配",
    ...trackingMetricValues(row.totals),
    ...row.daily.flatMap((day) => trackingMetricValues(day)),
  ]);
  const total = [
    "合计",
    "",
    ...trackingCumulativeTotals(rows),
    ...report.days.flatMap((_, dayIndex) => trackingDayTotals(rows, dayIndex)),
  ];
  return [
    [title],
    financialMonth,
    currentRange,
    priorRange,
    scope,
    topHeader,
    subHeader,
    ...body,
    total,
  ];
}

function groupSalesTrackingTable(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[],
): Array<Array<string | number>> {
  const cumulativeDates = cumulativeDateRange(report);
  const title = `${DAILY_FOLLOWUP_REPORT_NAME} · 柜组逐日销售`;
  const financialMonth = ["财务月", report.financial_month, "金额单位", "万元"];
  const currentRange = [
    "本期范围",
    `${cumulativeDates.start_date} 至 ${cumulativeDates.end_date}`,
  ];
  const priorRange = [
    "同期范围",
    `${cumulativeDates.prior_start_date} 至 ${cumulativeDates.prior_end_date}`,
  ];
  const scope = ["数据范围", report.scope_description || "当前查询权限范围"];
  const fixedHeaders = ["门店", "部门", "区域", "类别", "经营方式", "柜组名称"];
  const metricHeaders = ["本期销售", "同期销售", "销售同比"];
  const topHeader = [
    ...fixedHeaders.map(() => ""),
    "累计",
    "",
    "",
    ...report.days.flatMap((day) => [
      formatExportDate(day.date),
      "",
      "",
    ]),
  ];
  const subHeader = [
    ...fixedHeaders,
    ...metricHeaders,
    ...report.days.flatMap(() => metricHeaders),
  ];
  const body = rows.map((row) => [
    row.store_name || row.store_code || "未匹配",
    row.department_name || row.department_code || "未匹配",
    row.area_name || "未匹配",
    row.category_name || "未匹配",
    row.operation_method || "未匹配",
    row.dimension_name || "未匹配",
    ...trackingMetricValues(row.totals).slice(0, 3),
    ...row.daily.flatMap((day) => [
      toWan(day.sales_current),
      toWan(day.sales_prior),
      day.sales_yoy ?? "",
    ]),
  ]);
  const total = [
    "合计",
    "",
    "",
    "",
    "",
    "",
    ...trackingCumulativeTotals(rows).slice(0, 3),
    ...report.days.flatMap((_, dayIndex) => (
      trackingDayTotals(rows, dayIndex).slice(0, 3)
    )),
  ];
  return [
    [title],
    financialMonth,
    currentRange,
    priorRange,
    scope,
    topHeader,
    subHeader,
    ...body,
    total,
  ];
}

function specialSaleTrackingTable(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[],
): Array<Array<string | number>> {
  const cumulativeDates = cumulativeDateRange(report);
  const title = `${DAILY_FOLLOWUP_REPORT_NAME} · 特卖逐日`;
  const financialMonth = ["财务月", report.financial_month, "金额单位", "万元"];
  const currentRange = [
    "本期范围",
    `${cumulativeDates.start_date} 至 ${cumulativeDates.end_date}`,
  ];
  const priorRange = [
    "同期范围",
    `${cumulativeDates.prior_start_date} 至 ${cumulativeDates.prior_end_date}`,
  ];
  const scope = ["数据范围", report.scope_description || "当前查询权限范围"];
  const fixedHeaders = [
    "门店编码",
    "门店名称",
    "部门编码",
    "部门名称",
    "柜组编码",
    "柜组名称",
    "品牌编码",
    "品牌名称",
  ];
  const metricHeaders = TRACKING_METRIC_HEADERS;
  const topHeader = [
    ...fixedHeaders.map(() => ""),
    "累计",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    ...report.days.flatMap((day) => [
      formatExportDate(day.date),
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
    ]),
  ];
  const subHeader = [
    ...fixedHeaders,
    ...metricHeaders,
    ...report.days.flatMap(() => metricHeaders),
  ];
  const body = rows.map((row) => [
    row.store_code || "",
    row.store_name || "未匹配",
    row.department_code || "",
    row.department_name || "未匹配",
    row.dimension_code || "",
    row.dimension_name || "未匹配",
    row.brand_code || "",
    row.brand_name || "未匹配",
    ...trackingMetricValues(row.totals),
    ...row.daily.flatMap((day) => trackingMetricValues(day)),
  ]);
  const total = [
    "合计",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    ...trackingCumulativeTotals(rows),
    ...report.days.flatMap((_, dayIndex) => trackingDayTotals(rows, dayIndex)),
  ];
  return [
    [title],
    financialMonth,
    currentRange,
    priorRange,
    scope,
    topHeader,
    subHeader,
    ...body,
    total,
  ];
}

export function buildDailyFollowupExportData(
  report: DailyFollowupResponse,
  options: DailyFollowupExportOptions,
): DailyFollowupExportData {
  const rows = options.rows ?? report.rows;
  const dimension = dimensionLabel(report.dimension);
  const metric = metricLabel(options.metricView);
  return {
    currentViewRows: currentViewTable(report, rows, options.metricView),
    detailRows: detailTable(report, rows),
    currentHeaderRow: 3,
    filename: safeFilenamePart(
      `OD0001销售逐日跟进表_${report.financial_month}_${dimension}_${metric}.xlsx`,
    ),
    sheetName: `${dimension}-${metric}`,
  };
}

export function buildDailyFollowupWorkbookData(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[] = report.rows,
  companion?: {
    report: DailyFollowupResponse;
    rows?: DailyFollowupRow[];
  },
  specialSales?: {
    report: DailyFollowupResponse;
    rows?: DailyFollowupRow[];
  },
): DailyFollowupWorkbookData {
  const dimension = dimensionLabel(report.dimension);
  const salesSheet = buildDailyFollowupExportData(report, {
    metricView: "sales",
    rows,
  });
  const profitSheet = buildDailyFollowupExportData(report, {
    metricView: "profit",
    rows,
  });
  const trackingSheet = {
    rows: trackingTable(report, rows),
    headerRows: [5, 6] as [number, number],
    fixedColumnCount: report.dimension === "groups" ? 6 : 2,
    metricColumnsPerDay: 9,
    sheetName: report.dimension === "groups" ? "柜组" : "部门",
  };
  const companionTrackingSheet = companion
    && companion.report.dimension !== report.dimension
    ? {
        rows: trackingTable(
          companion.report,
          companion.rows ?? companion.report.rows,
        ),
        headerRows: [5, 6] as [number, number],
        fixedColumnCount: companion.report.dimension === "groups" ? 6 : 2,
        metricColumnsPerDay: 9,
        sheetName: companion.report.dimension === "groups" ? "柜组" : "部门",
      }
    : null;
  const groupSource = report.dimension === "groups"
    ? { report, rows }
    : companion?.report.dimension === "groups"
      ? {
          report: companion.report,
          rows: companion.rows ?? companion.report.rows,
        }
      : null;
  const areaTrackingSheet = groupSource
    ? {
        rows: areaTrackingTable(
          groupSource.report,
          aggregateGroupRowsByArea(groupSource.report, groupSource.rows),
        ),
        headerRows: [5, 6] as [number, number],
        fixedColumnCount: 2,
        metricColumnsPerDay: 9,
        sheetName: "区域",
      }
    : null;
  const groupSalesTrackingSheet = groupSource
    ? {
        rows: groupSalesTrackingTable(groupSource.report, groupSource.rows),
        headerRows: [5, 6] as [number, number],
        fixedColumnCount: 6,
        metricColumnsPerDay: 3,
        sheetName: "柜组销售",
      }
    : null;
  const specialSaleTrackingSheet = specialSales
    ? {
        rows: specialSaleTrackingTable(
          specialSales.report,
          specialSales.rows ?? specialSales.report.rows,
        ),
        headerRows: [5, 6] as [number, number],
        fixedColumnCount: 8,
        metricColumnsPerDay: 9,
        sheetName: "特卖",
      }
    : null;
  const trackingSheets = [
    trackingSheet,
    ...(companionTrackingSheet ? [companionTrackingSheet] : []),
    ...(areaTrackingSheet ? [areaTrackingSheet] : []),
    ...(groupSalesTrackingSheet ? [groupSalesTrackingSheet] : []),
    ...(specialSaleTrackingSheet ? [specialSaleTrackingSheet] : []),
  ].sort((left, right) => {
    const order = {
      部门: 0,
      区域: 1,
      柜组: 2,
      柜组销售: 3,
      特卖: 4,
    } as Record<string, number>;
    return (order[left.sheetName] ?? 99) - (order[right.sheetName] ?? 99);
  });
  return {
    trackingSheet,
    trackingSheets,
    viewSheets: [salesSheet, profitSheet],
    detailRows: detailTable(report, rows),
    detailSheetName: "同期同比明细",
    filename: safeFilenamePart(
      companionTrackingSheet
        ? `OD0001销售逐日跟进表_${report.financial_month}.xlsx`
        : `OD0001销售逐日跟进表_${report.financial_month}_${dimension}.xlsx`,
    ),
  };
}
