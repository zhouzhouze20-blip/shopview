import XLSX from "xlsx-js-style";

import {
  DAILY_FOLLOWUP_AMOUNT_FORMAT,
  DAILY_FOLLOWUP_PERCENT_FORMAT,
  DAILY_FOLLOWUP_SIGNED_PERCENT_FORMAT,
  buildDailyFollowupWorkbookData,
  dailyFollowupTrendColor,
  type DailyFollowupExportData,
  type DailyFollowupTrackingSheetData,
} from "./daily-followup-export-data";
import {
  type DailyFollowupResponse,
  type DailyFollowupRow,
} from "./daily-followup-report";

function styleHeader(
  sheet: XLSX.WorkSheet,
  rowIndex: number,
  columnCount: number,
  fillColor = "2563EB",
) {
  for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
    const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
    if (!sheet[address]) continue;
    sheet[address].s = {
      fill: { fgColor: { rgb: fillColor } },
      font: { bold: true, color: { rgb: "FFFFFF" } },
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

function styleCurrentSheet(
  sheet: XLSX.WorkSheet,
  data: DailyFollowupExportData,
  report: DailyFollowupResponse,
) {
  const columnCount = data.currentViewRows[3]?.length ?? 1;
  const lastRow = data.currentViewRows.length - 1;
  sheet["!merges"] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: columnCount - 1 } }];
  if (sheet.A1) {
    sheet.A1.s = {
      font: { bold: true, sz: 16, color: { rgb: "1E3A8A" } },
      alignment: { horizontal: "center", vertical: "center" },
    };
  }
  styleHeader(sheet, data.currentHeaderRow, columnCount);
  for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
    const address = XLSX.utils.encode_cell({ r: lastRow, c: columnIndex });
    if (!sheet[address]) continue;
    sheet[address].s = {
      fill: { fgColor: { rgb: "DBEAFE" } },
      font: { bold: true, color: { rgb: "1E3A8A" } },
    };
  }
  sheet["!autofilter"] = {
    ref: XLSX.utils.encode_range({
      s: { r: data.currentHeaderRow, c: 0 },
      e: { r: lastRow, c: columnCount - 1 },
    }),
  };
  sheet["!cols"] = report.dimension === "departments"
    ? Array.from({ length: columnCount }, (_, index) => ({ wch: index < 2 ? 11 : 12 }))
    : Array.from({ length: columnCount }, (_, index) => {
        if (index === 0) return { wch: 14 };
        if (index === 1) return { wch: 14 };
        if (index === 2) return { wch: 12 };
        if (index === 3) return { wch: 18 };
        return { wch: 9 };
      });
  sheet["!rows"] = [{ hpt: 28 }, { hpt: 22 }, { hpt: 22 }, { hpt: 24 }];

  const firstAmountColumn = report.dimension === "departments" ? 2 : 4;
  for (let rowIndex = data.currentHeaderRow + 1; rowIndex <= lastRow; rowIndex += 1) {
    for (let columnIndex = firstAmountColumn; columnIndex < columnCount; columnIndex += 1) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      if (sheet[address] && typeof sheet[address].v === "number") {
        sheet[address].z = DAILY_FOLLOWUP_AMOUNT_FORMAT;
      }
    }
  }
}

function styleDetailSheet(sheet: XLSX.WorkSheet, rowCount: number) {
  styleHeader(sheet, 0, 17);
  sheet["!autofilter"] = { ref: `A1:Q${Math.max(1, rowCount)}` };
  sheet["!cols"] = [
    { wch: 13 },
    { wch: 13 },
    { wch: 12 },
    { wch: 20 },
    { wch: 16 },
    { wch: 20 },
    { wch: 16 },
    { wch: 26 },
    ...Array.from({ length: 9 }, () => ({ wch: 15 })),
  ];
  for (let rowIndex = 1; rowIndex < rowCount; rowIndex += 1) {
    for (const columnIndex of [8, 9, 11, 12]) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      if (sheet[address] && typeof sheet[address].v === "number") {
        sheet[address].z = DAILY_FOLLOWUP_AMOUNT_FORMAT;
      }
    }
    for (const columnIndex of [10, 13, 14, 15, 16]) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      if (sheet[address] && typeof sheet[address].v === "number") {
        sheet[address].z = columnIndex === 16
          ? DAILY_FOLLOWUP_SIGNED_PERCENT_FORMAT
          : DAILY_FOLLOWUP_PERCENT_FORMAT;
      }
    }
    for (const columnIndex of [10, 13, 16]) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      const color = sheet[address] ? dailyFollowupTrendColor(sheet[address].v) : undefined;
      if (sheet[address] && color) {
        sheet[address].s = {
          ...(sheet[address].s ?? {}),
          font: {
            ...(sheet[address].s?.font ?? {}),
            color: { rgb: color },
          },
        };
      }
    }
  }
}

function styleTrackingSheet(
  sheet: XLSX.WorkSheet,
  data: DailyFollowupTrackingSheetData,
) {
  const topHeaderRow = data.headerRows[0];
  const subHeaderRow = data.headerRows[1];
  const columnCount = data.rows[topHeaderRow]?.length ?? 1;
  const lastRow = data.rows.length - 1;
  const { fixedColumnCount, metricColumnsPerDay } = data;
  const amountOffsets = metricColumnsPerDay === 3 ? [0, 1] : [0, 1, 3, 4];
  const percentOffsets = metricColumnsPerDay === 9
    ? [2, 5, 6, 7, 8]
    : metricColumnsPerDay === 3
      ? [2]
      : [2, 5];
  const trendOffsets = metricColumnsPerDay === 9
    ? [2, 5, 8]
    : percentOffsets;

  sheet["!merges"] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: columnCount - 1 } },
    {
      s: { r: lastRow, c: 0 },
      e: { r: lastRow, c: fixedColumnCount - 1 },
    },
    ...Array.from(
      { length: (columnCount - fixedColumnCount) / metricColumnsPerDay },
      (_, groupIndex) => {
        const columnIndex = fixedColumnCount + groupIndex * metricColumnsPerDay;
        return {
          s: { r: topHeaderRow, c: columnIndex },
          e: {
            r: topHeaderRow,
            c: columnIndex + metricColumnsPerDay - 1,
          },
        };
      },
    ),
  ];
  for (let rowIndex = 0; rowIndex < topHeaderRow; rowIndex += 1) {
    for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      if (!sheet[address]) {
        sheet[address] = { t: "s", v: "" };
      }
      sheet[address].s = {
        ...(sheet[address].s ?? {}),
        fill: { fgColor: { rgb: "FFFFFF" } },
        font: {
          ...(sheet[address].s?.font ?? {}),
          color: { rgb: "111827" },
        },
      };
    }
  }
  if (sheet.A1) {
    sheet.A1.s = {
      ...(sheet.A1.s ?? {}),
      fill: { fgColor: { rgb: "FFFFFF" } },
      font: { bold: true, sz: 16, color: { rgb: "1E3A8A" } },
      alignment: { horizontal: "center", vertical: "center" },
    };
  }
  styleHeader(sheet, topHeaderRow, columnCount, "0B6FCF");
  styleHeader(sheet, subHeaderRow, columnCount, "0B6FCF");
  for (const rowIndex of [topHeaderRow, subHeaderRow]) {
    for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      if (sheet[address]) {
        sheet[address].s = {
          ...(sheet[address].s ?? {}),
          font: {
            ...(sheet[address].s?.font ?? {}),
            sz: 9,
          },
        };
      }
    }
  }

  for (let rowIndex = subHeaderRow + 1; rowIndex <= lastRow; rowIndex += 1) {
    for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
      const address = XLSX.utils.encode_cell({ r: rowIndex, c: columnIndex });
      if (!sheet[address]) continue;
      sheet[address].s = {
        ...(sheet[address].s ?? {}),
        fill: {
          fgColor: {
            rgb: columnIndex < fixedColumnCount ? "0B6FCF" : "FFFFFF",
          },
        },
        font: {
          ...(sheet[address].s?.font ?? {}),
          bold: columnIndex < fixedColumnCount,
          sz: 9,
          color: {
            rgb: columnIndex < fixedColumnCount ? "FFFFFF" : "111827",
          },
        },
        alignment: {
          vertical: "center",
          horizontal: columnIndex < fixedColumnCount ? "left" : "right",
        },
        border: {
          top: { style: "thin", color: { rgb: "D1D5DB" } },
          bottom: { style: "thin", color: { rgb: "D1D5DB" } },
          left: { style: "thin", color: { rgb: "D1D5DB" } },
          right: { style: "thin", color: { rgb: "D1D5DB" } },
        },
      };
    }
    for (
      let columnIndex = fixedColumnCount;
      columnIndex < columnCount;
      columnIndex += metricColumnsPerDay
    ) {
      for (const offset of amountOffsets) {
        const amountAddress = XLSX.utils.encode_cell({
          r: rowIndex,
          c: columnIndex + offset,
        });
        if (sheet[amountAddress] && typeof sheet[amountAddress].v === "number") {
          sheet[amountAddress].z = DAILY_FOLLOWUP_AMOUNT_FORMAT;
        }
      }
      for (const offset of percentOffsets) {
        const percentAddress = XLSX.utils.encode_cell({
          r: rowIndex,
          c: columnIndex + offset,
        });
        if (sheet[percentAddress] && typeof sheet[percentAddress].v === "number") {
          sheet[percentAddress].z = offset === 8
            ? DAILY_FOLLOWUP_SIGNED_PERCENT_FORMAT
            : DAILY_FOLLOWUP_PERCENT_FORMAT;
          const color = trendOffsets.includes(offset)
            ? dailyFollowupTrendColor(sheet[percentAddress].v)
            : undefined;
          if (color) {
            sheet[percentAddress].s = {
              ...(sheet[percentAddress].s ?? {}),
              font: {
                ...(sheet[percentAddress].s?.font ?? {}),
                color: { rgb: color },
              },
            };
          }
        }
      }
    }
  }

  for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
    const address = XLSX.utils.encode_cell({ r: lastRow, c: columnIndex });
    if (!sheet[address]) continue;
    const metricOffset = (
      columnIndex >= fixedColumnCount
        ? (columnIndex - fixedColumnCount) % metricColumnsPerDay
        : -1
    );
    const trendColor = trendOffsets.includes(metricOffset)
      ? dailyFollowupTrendColor(sheet[address].v)
      : undefined;
    sheet[address].s = {
      ...(sheet[address].s ?? {}),
      fill: {
        fgColor: {
          rgb: columnIndex < fixedColumnCount ? "0B6FCF" : "DBEAFE",
        },
      },
      font: {
        ...(sheet[address].s?.font ?? {}),
        bold: true,
        sz: 9,
        color: {
          rgb: columnIndex < fixedColumnCount
            ? "FFFFFF"
            : trendColor ?? "1E3A8A",
        },
      },
      alignment: {
        vertical: "center",
        horizontal: columnIndex < fixedColumnCount ? "center" : "right",
      },
      border: {
        ...(sheet[address].s?.border ?? {}),
        top: { style: "medium", color: { rgb: "0B6FCF" } },
      },
    };
  }

  sheet["!cols"] = Array.from({ length: columnCount }, (_, columnIndex) => {
    if (fixedColumnCount === 8) {
      if (columnIndex === 0) return { wch: 12 };
      if (columnIndex === 1) return { wch: 18 };
      if (columnIndex === 2) return { wch: 16 };
      if (columnIndex === 3) return { wch: 20 };
      if (columnIndex === 4) return { wch: 16 };
      if (columnIndex === 5) return { wch: 24 };
      if (columnIndex === 6) return { wch: 14 };
      if (columnIndex === 7) return { wch: 24 };
    } else if (fixedColumnCount === 6) {
      if (columnIndex === 0) return { wch: 14 };
      if (columnIndex === 1) return { wch: 13 };
      if (columnIndex === 2) return { wch: 9 };
      if (columnIndex === 3) return { wch: 11 };
      if (columnIndex === 4) return { wch: 9 };
      if (columnIndex === 5) return { wch: 18 };
    } else if (columnIndex < 2) {
      return { wch: 14 };
    }
    return { wch: 9 };
  });
  if (lastRow >= subHeaderRow) {
    sheet["!autofilter"] = {
      ref: XLSX.utils.encode_range({
        s: { r: subHeaderRow, c: 0 },
        e: { r: Math.max(subHeaderRow, lastRow - 1), c: columnCount - 1 },
      }),
    };
  }
  sheet["!rows"] = [
    { hpt: 24 },
    { hpt: 19 },
    { hpt: 19 },
    { hpt: 19 },
    { hpt: 19 },
    { hpt: 20 },
    { hpt: 20 },
  ];
}

export function exportDailyFollowupExcel(
  report: DailyFollowupResponse,
  options: {
    rows?: DailyFollowupRow[];
    companionReport?: DailyFollowupResponse;
    companionRows?: DailyFollowupRow[];
    specialSaleReport?: DailyFollowupResponse;
    specialSaleRows?: DailyFollowupRow[];
  } = {},
): string {
  const data = buildDailyFollowupWorkbookData(
    report,
    options.rows,
    options.companionReport
      ? {
          report: options.companionReport,
          rows: options.companionRows,
        }
      : undefined,
    options.specialSaleReport
      ? {
          report: options.specialSaleReport,
          rows: options.specialSaleRows,
        }
      : undefined,
  );
  const workbook = XLSX.utils.book_new();
  for (const trackingSheetData of data.trackingSheets) {
    const trackingSheet = XLSX.utils.aoa_to_sheet(trackingSheetData.rows);
    styleTrackingSheet(trackingSheet, trackingSheetData);
    XLSX.utils.book_append_sheet(
      workbook,
      trackingSheet,
      trackingSheetData.sheetName.slice(0, 31),
    );
  }
  for (const viewSheet of data.viewSheets) {
    const sheet = XLSX.utils.aoa_to_sheet(viewSheet.currentViewRows);
    styleCurrentSheet(sheet, viewSheet, report);
    XLSX.utils.book_append_sheet(workbook, sheet, viewSheet.sheetName.slice(0, 31));
  }
  const detailSheet = XLSX.utils.aoa_to_sheet(data.detailRows);
  styleDetailSheet(detailSheet, data.detailRows.length);
  XLSX.utils.book_append_sheet(workbook, detailSheet, data.detailSheetName);
  XLSX.writeFile(workbook, data.filename);
  return data.filename;
}
