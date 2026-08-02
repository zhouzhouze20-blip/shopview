import type {
  DailyFollowupDay,
  DailyFollowupMetric,
  DailyFollowupResponse,
  DailyFollowupRow,
} from "./daily-followup-report";

export const OD0003_SHEETS = [
  "品牌销售",
  "部门区域类别",
  "部门区域",
  "区域类别",
  "门店区域",
  "部门销售",
] as const;

export type Od0003SheetName = (typeof OD0003_SHEETS)[number];
export type Od0003RowKind =
  | "detail"
  | "categorySubtotal"
  | "areaSubtotal"
  | "departmentSubtotal"
  | "grandTotal";

export interface Od0003TableRow {
  key: string;
  labels: string[];
  daily: DailyFollowupDay[];
  totals: DailyFollowupMetric;
  ytdTotals: DailyFollowupMetric;
  kind: Od0003RowKind;
}

export interface Od0003Sheet {
  name: Od0003SheetName;
  dimensionHeaders: string[];
  rows: Od0003TableRow[];
}

type Amounts = {
  salesCurrent: number;
  salesPrior: number;
  profitCurrent: number;
  profitPrior: number;
};

type Bucket = {
  labels: string[];
  daily: Amounts[];
  totals: Amounts;
  ytd: Amounts;
};

const emptyAmounts = (): Amounts => ({
  salesCurrent: 0,
  salesPrior: 0,
  profitCurrent: 0,
  profitPrior: 0,
});

function addMetric(target: Amounts, source: DailyFollowupMetric | undefined) {
  if (!source) return;
  target.salesCurrent += Number(source.sales_current || 0);
  target.salesPrior += Number(source.sales_prior || 0);
  target.profitCurrent += Number(source.profit_current || 0);
  target.profitPrior += Number(source.profit_prior || 0);
}

function metric(amounts: Amounts): DailyFollowupMetric {
  const salesChange = amounts.salesCurrent - amounts.salesPrior;
  const profitChange = amounts.profitCurrent - amounts.profitPrior;
  const currentMargin = amounts.salesCurrent === 0
    ? null
    : amounts.profitCurrent / amounts.salesCurrent;
  const priorMargin = amounts.salesPrior === 0
    ? null
    : amounts.profitPrior / amounts.salesPrior;
  return {
    sales_current: amounts.salesCurrent,
    sales_prior: amounts.salesPrior,
    sales_yoy: amounts.salesPrior === 0 ? null : salesChange / amounts.salesPrior,
    profit_current: amounts.profitCurrent,
    profit_prior: amounts.profitPrior,
    profit_yoy: amounts.profitPrior === 0 ? null : profitChange / amounts.profitPrior,
    margin_current: currentMargin,
    margin_prior: priorMargin,
    margin_change: currentMargin === null || priorMargin === null
      ? null
      : currentMargin - priorMargin,
  };
}

function aggregate(
  report: DailyFollowupResponse,
  rows: DailyFollowupRow[],
  labelsFor: (row: DailyFollowupRow) => string[],
): Od0003TableRow[] {
  const buckets = new Map<string, Bucket>();
  for (const row of rows) {
    const labels = labelsFor(row).map((value) => value || "未匹配");
    const key = JSON.stringify(labels);
    let bucket = buckets.get(key);
    if (!bucket) {
      bucket = {
        labels,
        daily: report.days.map(() => emptyAmounts()),
        totals: emptyAmounts(),
        ytd: emptyAmounts(),
      };
      buckets.set(key, bucket);
    }
    row.daily.forEach((day, index) => addMetric(bucket!.daily[index], day));
    addMetric(bucket.totals, row.totals);
    addMetric(bucket.ytd, row.ytd_totals);
  }
  return Array.from(buckets.entries())
    .sort(([, left], [, right]) =>
      left.labels.join("\u0000").localeCompare(right.labels.join("\u0000"), "zh-CN"))
    .map(([key, bucket]) => ({
      key,
      labels: bucket.labels,
      kind: "detail" as const,
      daily: bucket.daily.map((amounts, index) => ({
        ...metric(amounts),
        date: report.days[index]?.date || "",
        prior_date: report.days[index]?.prior_date || "",
      })),
      totals: metric(bucket.totals),
      ytdTotals: metric(bucket.ytd),
    }));
}

function subtotal(
  report: DailyFollowupResponse,
  rows: Od0003TableRow[],
  labels: string[],
  kind: Od0003RowKind,
  key: string,
): Od0003TableRow {
  const daily = report.days.map(() => emptyAmounts());
  const totals = emptyAmounts();
  const ytd = emptyAmounts();
  for (const row of rows) {
    row.daily.forEach((day, index) => addMetric(daily[index], day));
    addMetric(totals, row.totals);
    addMetric(ytd, row.ytdTotals);
  }
  return {
    key,
    labels,
    kind,
    daily: daily.map((amounts, index) => ({
      ...metric(amounts),
      date: report.days[index]?.date || "",
      prior_date: report.days[index]?.prior_date || "",
    })),
    totals: metric(totals),
    ytdTotals: metric(ytd),
  };
}

function withBrandSubtotals(
  report: DailyFollowupResponse,
  detailRows: Od0003TableRow[],
): Od0003TableRow[] {
  const result: Od0003TableRow[] = [];
  const byDepartment = new Map<string, Od0003TableRow[]>();
  for (const row of detailRows) {
    const department = row.labels[1] || "未匹配";
    const departmentRows = byDepartment.get(department) ?? [];
    departmentRows.push(row);
    byDepartment.set(department, departmentRows);
  }
  for (const [department, departmentRows] of byDepartment) {
    const byArea = new Map<string, Od0003TableRow[]>();
    for (const row of departmentRows) {
      const area = row.labels[2] || "未匹配";
      const areaRows = byArea.get(area) ?? [];
      areaRows.push(row);
      byArea.set(area, areaRows);
    }
    for (const [area, areaRows] of byArea) {
      const byCategory = new Map<string, Od0003TableRow[]>();
      for (const row of areaRows) {
        const category = row.labels[3] || "未匹配";
        const categoryRows = byCategory.get(category) ?? [];
        categoryRows.push(row);
        byCategory.set(category, categoryRows);
      }
      for (const [category, categoryRows] of byCategory) {
        result.push(...categoryRows);
        result.push(subtotal(
          report,
          categoryRows,
          ["", department, area, `${category}小计`, "", "", ""],
          "categorySubtotal",
          `category:${department}:${area}:${category}`,
        ));
      }
      result.push(subtotal(
        report,
        areaRows,
        ["", department, `${area}小计`, "", "", "", ""],
        "areaSubtotal",
        `area:${department}:${area}`,
      ));
    }
    result.push(subtotal(
      report,
      departmentRows,
      ["", `${department}合计`, "", "", "", "", ""],
      "departmentSubtotal",
      `department:${department}`,
    ));
  }
  result.push(subtotal(
    report,
    detailRows,
    ["中心合计", "", "", "", "", "", ""],
    "grandTotal",
    "grand-total",
  ));
  return result;
}

export function buildOd0003Sheets(report: DailyFollowupResponse): Od0003Sheet[] {
  const source = report.rows;
  const brandDetails = aggregate(report, source, (row) => [
    row.floor_code || "",
    row.department_name || row.department_code || "未匹配",
    row.area_name || "未匹配",
    row.category_name || "未匹配",
    row.dimension_name || row.dimension_code || "未匹配",
    row.is_key_brand ? "重点品牌" : "",
    row.manager_name || "",
  ]);
  const definitions: Array<{
    name: Od0003SheetName;
    headers: string[];
    labels: (row: DailyFollowupRow) => string[];
  }> = [
    {
      name: "部门区域类别",
      headers: ["部门名称", "区域名称", "类别名称"],
      labels: (row) => [
        row.department_name || row.department_code || "未匹配",
        row.area_name || "未匹配",
        row.category_name || "未匹配",
      ],
    },
    {
      name: "部门区域",
      headers: ["部门名称", "区域名称"],
      labels: (row) => [
        row.department_name || row.department_code || "未匹配",
        row.area_name || "未匹配",
      ],
    },
    {
      name: "区域类别",
      headers: ["区域名称", "类别名称"],
      labels: (row) => [
        row.area_name || "未匹配",
        row.category_name || "未匹配",
      ],
    },
    {
      name: "门店区域",
      headers: ["区域名称"],
      labels: (row) => [
        row.area_name || "未匹配",
      ],
    },
    {
      name: "部门销售",
      headers: ["部门名称"],
      labels: (row) => [
        row.department_name || row.department_code || "未匹配",
      ],
    },
  ];
  const result: Od0003Sheet[] = [{
    name: "品牌销售",
    dimensionHeaders: ["楼层", "部门名称", "区域名称", "类别名称", "品牌厅名称", "重点/业绩", "商品主管"],
    rows: withBrandSubtotals(report, brandDetails),
  }];
  for (const definition of definitions) {
    const detailRows = aggregate(report, source, definition.labels);
    result.push({
      name: definition.name,
      dimensionHeaders: definition.headers,
      rows: [
        ...detailRows,
        subtotal(
          report,
          detailRows,
          ["合计", ...Array(Math.max(0, definition.headers.length - 1)).fill("")],
          "grandTotal",
          `${definition.name}:grand-total`,
        ),
      ],
    });
  }
  return result;
}

export function od0003MetricValues(metricValue: DailyFollowupMetric): Array<number | ""> {
  const salesDiff = metricValue.sales_current - metricValue.sales_prior;
  const profitDiff = metricValue.profit_current - metricValue.profit_prior;
  return [
    metricValue.sales_current / 10_000,
    metricValue.sales_prior / 10_000,
    salesDiff / 10_000,
    metricValue.sales_yoy ?? "",
    metricValue.profit_current / 10_000,
    metricValue.profit_prior / 10_000,
    profitDiff / 10_000,
    metricValue.profit_yoy ?? "",
    metricValue.margin_current ?? "",
    metricValue.margin_prior ?? "",
    metricValue.margin_change ?? "",
  ];
}

export type Od0003WeekGroup = {
  label: string;
  dayIndexes: number[];
};

export function od0003WeekGroups(
  days: DailyFollowupResponse["days"],
): Od0003WeekGroup[] {
  const groups: Od0003WeekGroup[] = [];
  let indexes: number[] = [];
  const push = () => {
    if (!indexes.length) return;
    const first = days[indexes[0]];
    const last = days[indexes[indexes.length - 1]];
    const number = ["一", "二", "三", "四", "五", "六"][groups.length] ?? String(groups.length + 1);
    groups.push({
      label: `第${number}周${first.label.replace("-", ".")}-${last.label.replace("-", ".")}`,
      dayIndexes: indexes,
    });
    indexes = [];
  };
  days.forEach((day, index) => {
    indexes.push(index);
    const parsed = new Date(`${day.date}T00:00:00`);
    if (parsed.getDay() === 0) push();
  });
  push();
  return groups;
}

export function od0003AggregateMetrics(
  metrics: Array<DailyFollowupMetric | undefined>,
): DailyFollowupMetric {
  const amounts = emptyAmounts();
  metrics.forEach((value) => addMetric(amounts, value));
  return metric(amounts);
}

export const OD0003_METRIC_HEADERS = [
  "本期销售",
  "同期销售",
  "同比增减额",
  "同比增减率",
  "本期毛利",
  "同期毛利",
  "同比增减额",
  "同比增减率",
  "本期毛利率",
  "同期毛利率",
  "毛利率增减",
] as const;

export function od0003MetricHeaders(financialMonth: string): string[] {
  const year = Number(financialMonth.slice(0, 4));
  const current = String(year % 100).padStart(2, "0");
  const prior = String((year - 1) % 100).padStart(2, "0");
  return [
    `${current}年销`,
    `${prior}年销`,
    `${prior}同比额`,
    `${prior}同比率`,
    `${current}年毛`,
    `${prior}年毛`,
    `${prior}同比额`,
    `${prior}同比率`,
    `${current}年率`,
    `${prior}年率`,
    `${prior}同比`,
  ];
}
