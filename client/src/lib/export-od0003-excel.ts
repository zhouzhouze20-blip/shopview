import XLSX from "xlsx-js-style";

import {
  buildOd0003Sheets,
  OD0003_METRIC_HEADERS,
  od0003AggregateMetrics,
  od0003MetricHeaders,
  od0003MetricValues,
  od0003WeekGroups,
  type Od0003RowKind,
  type Od0003Sheet,
} from "./od0003-report";
import type { DailyFollowupResponse } from "./daily-followup-report";

export const OD0003_COLORS = {
  header: "D8E4BC",
  categorySubtotal: "CCC0DA",
  areaSubtotal: "B7DEE8",
  departmentSubtotal: "D8E4BC",
  grandTotal: "8DB4E2",
  target: "FFC000",
  border: "000000",
  negative: "FF0000",
} as const;

const AMOUNT_FORMAT = '0.00_);[Red]\\(0.00\\)';
const PERCENT_FORMAT = "0.00%;[Red]0.00%;0.00;@";
const TARGET_HEADERS = [
  "月度\n销售指标",
  "差额",
  "完成率",
  "月度\n毛利指标\n（含税）",
  "差额",
  "完成率",
];

function rowFill(kind: Od0003RowKind): string {
  return kind === "categorySubtotal"
    ? OD0003_COLORS.categorySubtotal
    : kind === "areaSubtotal"
      ? OD0003_COLORS.areaSubtotal
      : kind === "departmentSubtotal"
        ? OD0003_COLORS.departmentSubtotal
        : kind === "grandTotal"
          ? OD0003_COLORS.grandTotal
          : "FFFFFF";
}

function border() {
  return {
    top: { style: "thin", color: { rgb: OD0003_COLORS.border } },
    bottom: { style: "thin", color: { rgb: OD0003_COLORS.border } },
    left: { style: "thin", color: { rgb: OD0003_COLORS.border } },
    right: { style: "thin", color: { rgb: OD0003_COLORS.border } },
  };
}

function buildRows(report: DailyFollowupResponse, sheet: Od0003Sheet) {
  const dimensionCount = sheet.dimensionHeaders.length;
  const metricHeaders = od0003MetricHeaders(report.financial_month);
  const monthLabel = `${Number(report.financial_month.slice(5, 7))}月`;
  const weekGroups = od0003WeekGroups(report.days);
  const periodHeader = (label: string) => [
    `${label}销售额`, "", "", "",
    `${label}毛利额`, "", "", "",
    `${label}毛利率`, "", "",
  ];
  const periodLabels = [
    "1-12月",
    monthLabel,
    ...report.days.map((day) => day.label),
    ...weekGroups.map((group) => group.label),
  ];
  const topHeader = [...sheet.dimensionHeaders];
  const subHeader = [...sheet.dimensionHeaders];
  const periodStarts: number[] = [];
  const addPeriod = (label: string) => {
    periodStarts.push(topHeader.length);
    topHeader.push(...periodHeader(label));
    subHeader.push(...metricHeaders);
  };
  addPeriod(periodLabels[0]);
  const targetStart = sheet.name === "部门销售" ? topHeader.length : null;
  if (targetStart !== null) {
    topHeader.push(...TARGET_HEADERS);
    subHeader.push(...TARGET_HEADERS.map(() => ""));
  }
  periodLabels.slice(1).forEach(addPeriod);
  const body = sheet.rows.map((row) => {
    const weekMetrics = weekGroups.map((group) =>
      od0003AggregateMetrics(group.dayIndexes.map((index) => row.daily[index])));
    const values: Array<string | number> = [
      ...row.labels,
      ...od0003MetricValues(row.ytdTotals),
    ];
    if (targetStart !== null) values.push("", "", "", "", "", "");
    values.push(
      ...od0003MetricValues(row.totals),
      ...row.daily.flatMap(od0003MetricValues),
      ...weekMetrics.flatMap(od0003MetricValues),
    );
    return values;
  });
  return {
    rows: [topHeader, subHeader, ...body],
    dimensionCount,
    periodStarts,
    targetStart,
  };
}

function styleSheet(
  worksheet: XLSX.WorkSheet,
  report: DailyFollowupResponse,
  sheet: Od0003Sheet,
  rows: Array<Array<string | number>>,
  dimensionCount: number,
  periodStarts: number[],
  targetStart: number | null,
) {
  const columnCount = rows[1].length;
  const metricCount = OD0003_METRIC_HEADERS.length;
  const merges: XLSX.Range[] = [];
  for (let index = 0; index < dimensionCount; index += 1) {
    merges.push({ s: { r: 0, c: index }, e: { r: 1, c: index } });
  }
  for (const start of periodStarts) {
    merges.push(
      { s: { r: 0, c: start }, e: { r: 0, c: start + 3 } },
      { s: { r: 0, c: start + 4 }, e: { r: 0, c: start + 7 } },
      { s: { r: 0, c: start + 8 }, e: { r: 0, c: start + 10 } },
    );
  }
  if (targetStart !== null) {
    for (let index = 0; index < TARGET_HEADERS.length; index += 1) {
      merges.push({
        s: { r: 0, c: targetStart + index },
        e: { r: 1, c: targetStart + index },
      });
    }
  }
  worksheet["!merges"] = merges;
  worksheet["!freeze"] = { xSplit: dimensionCount, ySplit: 2 };
  worksheet["!cols"] = Array.from({ length: columnCount }, (_, index) => {
    if (index >= dimensionCount) return { wch: 9 };
    if (sheet.name === "品牌销售") {
      return { wch: [6.125, 11.625, 9.25, 7.375, 19.5, 9, 7.625][index] ?? 10 };
    }
    return { wch: index === 0 ? 16 : 11 };
  });
  worksheet["!rows"] = rows.map(() => ({ hpt: 24.95 }));

  for (let rowIndex = 0; rowIndex < rows.length; rowIndex += 1) {
    const dataKind = rowIndex >= 2 ? sheet.rows[rowIndex - 2]?.kind : null;
    const fill = rowIndex < 2 ? OD0003_COLORS.header : rowFill(dataKind || "detail");
    for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      if (!worksheet[address]) worksheet[address] = { t: "s", v: "" };
      worksheet[address].s = {
        fill: { fgColor: { rgb: fill } },
        font: {
          name: "Arial",
          sz: 9,
          bold: rowIndex < 2 || dataKind !== "detail",
          color: { rgb: "000000" },
        },
        alignment: {
          horizontal: "center",
          vertical: "center",
          wrapText: true,
        },
        border: border(),
      };
      if (rowIndex >= 2 && periodStarts.some(
        (start) => columnIndex >= start && columnIndex < start + metricCount,
      )) {
        const periodStart = periodStarts.find(
          (start) => columnIndex >= start && columnIndex < start + metricCount,
        )!;
        const metricOffset = columnIndex - periodStart;
        worksheet[address].z = metricOffset >= 3 && metricOffset !== 4 && metricOffset !== 5 && metricOffset !== 6
          ? PERCENT_FORMAT
          : AMOUNT_FORMAT;
      }
      if (
        rowIndex >= 2
        && targetStart !== null
        && columnIndex >= targetStart
        && columnIndex < targetStart + TARGET_HEADERS.length
      ) {
        const targetOffset = columnIndex - targetStart;
        worksheet[address].z = [2, 5].includes(targetOffset)
          ? PERCENT_FORMAT
          : AMOUNT_FORMAT;
      }
    }
  }
  const endCell = XLSX.utils.encode_cell({ r: Math.max(1, rows.length - 1), c: columnCount - 1 });
  worksheet["!autofilter"] = {
    ref: `${XLSX.utils.encode_cell({ r: 1, c: 0 })}:${endCell}`,
  };
}

export function buildOd0003Workbook(report: DailyFollowupResponse): XLSX.WorkBook {
  const workbook = XLSX.utils.book_new();
  for (const sheet of buildOd0003Sheets(report)) {
    const data = buildRows(report, sheet);
    const worksheet = XLSX.utils.aoa_to_sheet(data.rows);
    styleSheet(
      worksheet,
      report,
      sheet,
      data.rows,
      data.dimensionCount,
      data.periodStarts,
      data.targetStart,
    );
    XLSX.utils.book_append_sheet(workbook, worksheet, sheet.name);
  }
  workbook.Props = {
    Title: `OD0003 中心销售跟进表 ${report.financial_month}`,
    Subject: "中心销售、毛利与同期跟进",
    Company: "ShopView",
  };
  return workbook;
}

export function downloadOd0003Workbook(report: DailyFollowupResponse) {
  const store = report.selected_store
    ? report.rows[0]?.store_name || report.selected_store
    : "全部门店";
  const department = report.selected_department
    ? report.rows[0]?.department_name || report.selected_department
    : "全部门";
  const safe = (value: string) => value.replace(/[/\\?%*:|"<>]/g, "_");
  XLSX.writeFile(
    buildOd0003Workbook(report),
    safe(`OD0003中心销售跟进表_${store}_${department}_${report.financial_month}.xlsx`),
  );
}
