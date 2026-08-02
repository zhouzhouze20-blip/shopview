import XLSX from "xlsx-js-style";

import type {
  MonthlyFollowupMetric,
  MonthlyFollowupResponse,
  MonthlyFollowupRow,
} from "./monthly-followup-report.ts";

const AMOUNT_FORMAT = '#,##0.00;[Red]-#,##0.00';
const PERCENT_FORMAT = '0.0%;[Red]-0.0%';
const SIGNED_PERCENT_FORMAT = '+0.0%;[Red]-0.0%;0.0%';
const METRIC_COLUMN_COUNT = 9;

type SheetDefinition = {
  name: string;
  rows: MonthlyFollowupRow[];
  fixedHeaders: string[];
  fixedValues: (row: MonthlyFollowupRow) => Array<string | number>;
};

function amountWan(value: number | null | undefined): number {
  return Number(value ?? 0) / 10_000;
}

function metricCells(metric: MonthlyFollowupMetric): Array<number | null> {
  return [
    amountWan(metric.sales_current),
    amountWan(metric.sales_prior),
    metric.sales_yoy,
    amountWan(metric.profit_current),
    amountWan(metric.profit_prior),
    metric.profit_yoy,
    metric.margin_current,
    metric.margin_prior,
    metric.margin_change,
  ];
}

function aggregateRows(
  rows: MonthlyFollowupRow[],
  keyFor: (row: MonthlyFollowupRow) => string,
  create: (row: MonthlyFollowupRow) => Partial<MonthlyFollowupRow>,
): MonthlyFollowupRow[] {
  const grouped = new Map<string, MonthlyFollowupRow>();
  for (const row of rows) {
    const key = keyFor(row);
    let target = grouped.get(key);
    if (!target) {
      const blankMetric = (): MonthlyFollowupMetric => ({
        sales_current: 0,
        sales_prior: 0,
        sales_yoy: null,
        profit_current: 0,
        profit_prior: 0,
        profit_yoy: null,
        margin_current: null,
        margin_prior: null,
        margin_change: null,
      });
      target = {
        store_code: row.store_code,
        store_name: row.store_name,
        department_code: null,
        department_name: null,
        dimension_code: null,
        dimension_name: null,
        ...create(row),
        monthly: row.monthly.map((month) => ({
          ...blankMetric(),
          financial_month: month.financial_month,
          label: month.label,
        })),
        totals: blankMetric(),
      };
      grouped.set(key, target);
    }
    row.monthly.forEach((month, index) => {
      const metric = target!.monthly[index];
      metric.sales_current += month.sales_current;
      metric.sales_prior += month.sales_prior;
      metric.profit_current += month.profit_current;
      metric.profit_prior += month.profit_prior;
    });
  }
  const finish = (metric: MonthlyFollowupMetric) => {
    metric.sales_yoy = metric.sales_prior === 0 ? null : metric.sales_current / metric.sales_prior - 1;
    metric.profit_yoy = metric.profit_prior === 0 ? null : metric.profit_current / metric.profit_prior - 1;
    metric.margin_current = metric.sales_current === 0 ? null : metric.profit_current / metric.sales_current;
    metric.margin_prior = metric.sales_prior === 0 ? null : metric.profit_prior / metric.sales_prior;
    metric.margin_change = metric.margin_current === null || metric.margin_prior === null
      ? null
      : metric.margin_current - metric.margin_prior;
  };
  for (const row of grouped.values()) {
    for (const month of row.monthly) {
      finish(month);
      row.totals.sales_current += month.sales_current;
      row.totals.sales_prior += month.sales_prior;
      row.totals.profit_current += month.profit_current;
      row.totals.profit_prior += month.profit_prior;
    }
    finish(row.totals);
  }
  return [...grouped.values()];
}

function buildSheetRows(
  report: MonthlyFollowupResponse,
  definition: SheetDefinition,
): Array<Array<string | number | null>> {
  const blocks = [
    { label: "全年合计", metric: (row: MonthlyFollowupRow) => row.totals },
    ...report.months.map((month, index) => ({
      label: month.label,
      metric: (row: MonthlyFollowupRow) => row.monthly[index],
    })),
  ];
  const topHeader = [
    ...definition.fixedHeaders,
    ...blocks.flatMap((block) => [
      block.label,
      ...Array.from({ length: METRIC_COLUMN_COUNT - 1 }, () => ""),
    ]),
  ];
  const subHeader = [
    ...definition.fixedHeaders.map(() => ""),
    ...blocks.flatMap(() => [
      "本期销售",
      "同期销售",
      "销售同比",
      "本期毛利",
      "同期毛利",
      "毛利同比",
      "本期毛利率",
      "同期毛利率",
      "毛利率同比",
    ]),
  ];
  const body = definition.rows.map((row) => [
    ...definition.fixedValues(row),
    ...blocks.flatMap((block) => metricCells(block.metric(row))),
  ]);
  const total = [
    "合计",
    ...definition.fixedHeaders.slice(1).map(() => ""),
    ...blocks.flatMap((block, index) => metricCells(
      index === 0 ? report.totals : report.monthly_totals[index - 1],
    )),
  ];
  return [
    [`OD0004 销售逐月跟进表（${report.financial_year}年）`],
    ["财务年度", `${report.financial_year}年（逐月）`],
    ["本期范围", `${report.dates.start_date} 至 ${report.dates.end_date}`],
    ["同期范围", `${report.dates.prior_start_date} 至 ${report.dates.prior_end_date}`],
    ["权限范围", report.scope_description || "按当前账号业务范围"],
    topHeader,
    subHeader,
    ...body,
    total,
  ];
}

function styleSheet(
  sheet: XLSX.WorkSheet,
  rowCount: number,
  fixedColumnCount: number,
  blockCount: number,
) {
  const columnCount = fixedColumnCount + blockCount * METRIC_COLUMN_COUNT;
  const lastRow = rowCount - 1;
  sheet["!merges"] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: columnCount - 1 } },
    ...Array.from({ length: blockCount }, (_, index) => ({
      s: { r: 5, c: fixedColumnCount + index * METRIC_COLUMN_COUNT },
      e: { r: 5, c: fixedColumnCount + index * METRIC_COLUMN_COUNT + METRIC_COLUMN_COUNT - 1 },
    })),
  ];
  if (sheet.A1) {
    sheet.A1.s = {
      font: { bold: true, sz: 16, color: { rgb: "1E3A8A" } },
      alignment: { horizontal: "center", vertical: "center" },
    };
  }
  for (const headerRow of [5, 6]) {
    for (let column = 0; column < columnCount; column += 1) {
      const cell = sheet[XLSX.utils.encode_cell({ r: headerRow, c: column })];
      if (!cell) continue;
      cell.s = {
        fill: { fgColor: { rgb: "0B6FCF" } },
        font: { bold: true, color: { rgb: "FFFFFF" }, sz: 9 },
        alignment: { horizontal: "center", vertical: "center" },
        border: {
          top: { style: "thin", color: { rgb: "D1D5DB" } },
          bottom: { style: "thin", color: { rgb: "D1D5DB" } },
          left: { style: "thin", color: { rgb: "D1D5DB" } },
          right: { style: "thin", color: { rgb: "D1D5DB" } },
        },
      };
    }
  }
  for (let row = 7; row <= lastRow; row += 1) {
    for (let column = 0; column < columnCount; column += 1) {
      const cell = sheet[XLSX.utils.encode_cell({ r: row, c: column })];
      if (!cell) continue;
      cell.s = {
        ...(cell.s ?? {}),
        fill: { fgColor: { rgb: column < fixedColumnCount ? "EAF3FF" : "FFFFFF" } },
        font: { ...(cell.s?.font ?? {}), bold: row === lastRow || column < fixedColumnCount },
        border: {
          top: { style: "thin", color: { rgb: "D1D5DB" } },
          bottom: { style: "thin", color: { rgb: "D1D5DB" } },
          left: { style: "thin", color: { rgb: "D1D5DB" } },
          right: { style: "thin", color: { rgb: "D1D5DB" } },
        },
      };
    }
    for (let block = 0; block < blockCount; block += 1) {
      const start = fixedColumnCount + block * METRIC_COLUMN_COUNT;
      for (const offset of [0, 1, 3, 4]) {
        const cell = sheet[XLSX.utils.encode_cell({ r: row, c: start + offset })];
        if (cell && typeof cell.v === "number") cell.z = AMOUNT_FORMAT;
      }
      for (const offset of [2, 5, 6, 7, 8]) {
        const cell = sheet[XLSX.utils.encode_cell({ r: row, c: start + offset })];
        if (cell && typeof cell.v === "number") {
          cell.z = offset === 8 ? SIGNED_PERCENT_FORMAT : PERCENT_FORMAT;
        }
      }
    }
  }
  sheet["!freeze"] = { xSplit: fixedColumnCount, ySplit: 7 };
  sheet["!cols"] = [
    ...Array.from({ length: fixedColumnCount }, (_, index) => ({ wch: index === 0 ? 14 : 18 })),
    ...Array.from({ length: blockCount * METRIC_COLUMN_COUNT }, () => ({ wch: 12 })),
  ];
  sheet["!rows"] = [{ hpt: 28 }, { hpt: 20 }, { hpt: 20 }, { hpt: 20 }, { hpt: 20 }, { hpt: 22 }, { hpt: 24 }];
}

export function exportMonthlyFollowupExcel(
  departmentReport: MonthlyFollowupResponse,
  groupReport: MonthlyFollowupResponse,
  specialSaleReport: MonthlyFollowupResponse,
): string {
  const areaRows = aggregateRows(
    groupReport.rows,
    (row) => `${row.store_code ?? ""}|${row.area_name ?? "未匹配"}`,
    (row) => ({
      dimension_code: row.area_name ?? "未匹配",
      dimension_name: row.area_name ?? "未匹配",
    }),
  );
  const definitions: SheetDefinition[] = [
    {
      name: "部门",
      rows: departmentReport.rows,
      fixedHeaders: ["门店", "部门"],
      fixedValues: (row) => [row.store_name || row.store_code || "", row.dimension_name || "未匹配"],
    },
    {
      name: "区域",
      rows: areaRows,
      fixedHeaders: ["门店", "区域"],
      fixedValues: (row) => [row.store_name || row.store_code || "", row.dimension_name || "未匹配"],
    },
    {
      name: "柜组",
      rows: groupReport.rows,
      fixedHeaders: ["门店", "部门", "区域", "类别", "经营方式", "柜组名称"],
      fixedValues: (row) => [
        row.store_name || row.store_code || "",
        row.department_name || "未匹配",
        row.area_name || "未匹配",
        row.category_name || "未匹配",
        row.operation_method || "未匹配",
        row.dimension_name || "未匹配",
      ],
    },
    {
      name: "柜组销售",
      rows: groupReport.rows,
      fixedHeaders: ["门店", "部门", "区域", "类别", "经营方式", "柜组名称"],
      fixedValues: (row) => [
        row.store_name || row.store_code || "",
        row.department_name || "未匹配",
        row.area_name || "未匹配",
        row.category_name || "未匹配",
        row.operation_method || "未匹配",
        row.dimension_name || "未匹配",
      ],
    },
    {
      name: "特卖",
      rows: specialSaleReport.rows,
      fixedHeaders: ["门店", "部门", "区域", "类别", "经营方式", "柜组名称", "品牌编码", "品牌名称"],
      fixedValues: (row) => [
        row.store_name || row.store_code || "",
        row.department_name || "未匹配",
        row.area_name || "未匹配",
        row.category_name || "未匹配",
        row.operation_method || "未匹配",
        row.dimension_name || "未匹配",
        row.brand_code || "",
        row.brand_name || "未匹配",
      ],
    },
  ];
  const workbook = XLSX.utils.book_new();
  for (const definition of definitions) {
    const rows = buildSheetRows(
      definition.name === "部门"
        ? departmentReport
        : definition.name === "特卖"
          ? specialSaleReport
          : groupReport,
      definition,
    );
    const sheet = XLSX.utils.aoa_to_sheet(rows);
    styleSheet(sheet, rows.length, definition.fixedHeaders.length, 13);
    XLSX.utils.book_append_sheet(workbook, sheet, definition.name);
  }
  const filename = `OD0004销售逐月跟进表_${departmentReport.financial_year}.xlsx`;
  XLSX.writeFile(workbook, filename);
  return filename;
}
