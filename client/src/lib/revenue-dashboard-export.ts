import XLSX from "xlsx-js-style";

export type RevenueDashboardFeeBreakdown = {
  fee_type_code?: string | null;
  fee_type_name?: string | null;
  tax_excluded_amount: number;
};

export type RevenueDashboardExportItem = {
  store_id: number;
  store_code?: string | null;
  store_name?: string | null;
  department_code?: string | null;
  department_name: string;
  group_code?: string | null;
  group_name: string;
  unit_codes?: string | null;
  unit_count: number;
  sales_gross_profit_amount: number;
  fee_amount: number;
  extra_amount: number;
  total_amount: number;
  fee_breakdown?: RevenueDashboardFeeBreakdown[];
};

export type RevenueDashboardExportData = {
  filename: string;
  feeColumns: string[];
  summaryRows: Array<Array<string | number>>;
  feeDetailRows: Array<Array<string | number>>;
  notesRows: Array<Array<string | number>>;
};

const amount = (value: number | null | undefined) => Number(value || 0);

const feeColumnName = (fee: RevenueDashboardFeeBreakdown) => {
  const code = String(fee.fee_type_code || "").trim();
  const name = String(fee.fee_type_name || "").trim() || "未分类收费";
  return code ? `${code} ${name}` : name;
};

const compareText = (left: string | null | undefined, right: string | null | undefined) =>
  String(left || "").localeCompare(String(right || ""), "zh-CN", {
    numeric: true,
    sensitivity: "base",
  });

export function buildRevenueDashboardExportData(
  items: RevenueDashboardExportItem[],
  startDate: string,
  endDate: string,
): RevenueDashboardExportData {
  const feeColumns = Array.from(
    new Set(
      items.flatMap((item) => (item.fee_breakdown || []).map(feeColumnName)),
    ),
  ).sort(compareText);

  const staticHeaders = [
    "开始日期",
    "结束日期",
    "门店编码",
    "门店",
    "部门编码",
    "部门",
    "柜组编码",
    "柜组",
    "图上经营单元",
    "销售毛利（不含税）",
    "去税收费汇总",
    "其他收益",
    "总收益",
    "收费分类校验差额",
  ];

  const sortedItems = [...items].sort(
    (left, right) =>
      compareText(left.store_code || left.store_name, right.store_code || right.store_name) ||
      compareText(left.department_code || left.department_name, right.department_code || right.department_name) ||
      compareText(left.group_code || left.group_name, right.group_code || right.group_name),
  );

  const detailRows = sortedItems.map((item) => {
    const breakdown = new Map<string, number>();
    (item.fee_breakdown || []).forEach((fee) => {
      const key = feeColumnName(fee);
      breakdown.set(key, amount(breakdown.get(key)) + amount(fee.tax_excluded_amount));
    });
    const feeBreakdownTotal = Array.from(breakdown.values()).reduce((sum, value) => sum + value, 0);
    return [
      startDate,
      endDate,
      item.store_code || "",
      item.store_name || "",
      item.department_code || "",
      item.department_name || "未归属部门",
      item.group_code || "",
      item.group_name || "未归属柜组",
      item.unit_codes || "",
      amount(item.sales_gross_profit_amount),
      amount(item.fee_amount),
      amount(item.extra_amount),
      amount(item.total_amount),
      amount(item.fee_amount) - feeBreakdownTotal,
      ...feeColumns.map((column) => amount(breakdown.get(column))),
    ];
  });

  const amountColumnStart = 9;
  const totalRow = Array.from(
    { length: staticHeaders.length + feeColumns.length },
    (_, columnIndex): string | number => {
      if (columnIndex === 3) return "合计";
      if (columnIndex >= amountColumnStart) {
        return detailRows.reduce(
          (sum, row) => sum + amount(row[columnIndex] as number),
          0,
        );
      }
      return "";
    },
  );

  const feeDetailRows = [
    [
      "开始日期",
      "结束日期",
      "门店编码",
      "门店",
      "部门编码",
      "部门",
      "柜组编码",
      "柜组",
      "收费项目编码",
      "收费项目",
      "不含税金额",
    ],
    ...sortedItems.flatMap((item) =>
      (item.fee_breakdown || []).map((fee) => [
        startDate,
        endDate,
        item.store_code || "",
        item.store_name || "",
        item.department_code || "",
        item.department_name || "未归属部门",
        item.group_code || "",
        item.group_name || "未归属柜组",
        fee.fee_type_code || "",
        fee.fee_type_name || "未分类收费",
        amount(fee.tax_excluded_amount),
      ]),
    ),
  ];

  return {
    filename: `收益看板_柜组最明细_${startDate}_${endDate}.xlsx`,
    feeColumns,
    summaryRows: [
      [...staticHeaders, ...feeColumns.map((column) => `${column}（不含税）`)],
      ...detailRows,
      totalRow,
    ],
    feeDetailRows,
    notesRows: [
      ["收益看板导出说明"],
      ["查询日期", `${startDate} 至 ${endDate}`],
      ["日期口径", "销售毛利按财务日期；收费按付款日期；其他收益按确认收益日期"],
      ["数据范围", "仅导出当前账号数据权限范围内的数据"],
      ["明细粒度", "一行一个门店 / 部门 / 柜组"],
      ["销售毛利", "不含税；包含已计入销售毛利的损失承担"],
      ["去税收费汇总", "不含税；仅统计已关联付款日期的收费；不含已计入销售毛利的损失承担"],
      ["未付款收费", "未关联结算付款日期或租赁付款日期的收费不进入本次导出"],
      ["收费明细列", "按收费项目编码和名称动态展开，不含税金额"],
      ["其他收益", "已确认的其他收益"],
      ["总收益", "销售毛利（不含税） + 去税收费汇总 + 其他收益"],
      ["收费分类校验差额", "去税收费汇总 - 各收费明细列合计；正常应为 0"],
    ],
  };
}

const headerStyle = {
  font: { bold: true, color: { rgb: "FFFFFF" } },
  fill: { fgColor: { rgb: "1E3A5F" } },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
  border: {
    top: { style: "thin", color: { rgb: "CBD5E1" } },
    bottom: { style: "thin", color: { rgb: "CBD5E1" } },
    left: { style: "thin", color: { rgb: "CBD5E1" } },
    right: { style: "thin", color: { rgb: "CBD5E1" } },
  },
};

function styleDataSheet(
  sheet: XLSX.WorkSheet,
  rows: Array<Array<string | number>>,
  amountColumnStart: number,
  hasTotalRow = false,
) {
  const range = XLSX.utils.decode_range(sheet["!ref"] || "A1:A1");
  for (let column = range.s.c; column <= range.e.c; column += 1) {
    const header = sheet[XLSX.utils.encode_cell({ r: 0, c: column })];
    if (header) header.s = headerStyle;
  }
  for (let row = 1; row <= range.e.r; row += 1) {
    for (let column = amountColumnStart; column <= range.e.c; column += 1) {
      const cell = sheet[XLSX.utils.encode_cell({ r: row, c: column })];
      if (cell) cell.z = '#,##0.00;[Red]-#,##0.00';
    }
  }
  if (hasTotalRow) {
    const lastRow = rows.length - 1;
    for (let column = range.s.c; column <= range.e.c; column += 1) {
      const cell = sheet[XLSX.utils.encode_cell({ r: lastRow, c: column })];
      if (cell) {
        cell.s = {
          font: { bold: true },
          fill: { fgColor: { rgb: "E2E8F0" } },
        };
      }
    }
  }
  sheet["!autofilter"] = {
    ref: XLSX.utils.encode_range({
      s: { r: 0, c: 0 },
      e: {
        r: Math.max(0, rows.length - (hasTotalRow ? 2 : 1)),
        c: range.e.c,
      },
    }),
  };
  sheet["!rows"] = [{ hpt: 32 }];
}

export function exportRevenueDashboardExcel(
  items: RevenueDashboardExportItem[],
  startDate: string,
  endDate: string,
) {
  const data = buildRevenueDashboardExportData(items, startDate, endDate);
  const workbook = XLSX.utils.book_new();

  const summarySheet = XLSX.utils.aoa_to_sheet(data.summaryRows);
  styleDataSheet(summarySheet, data.summaryRows, 9, true);
  summarySheet["!cols"] = [
    { wch: 12 },
    { wch: 12 },
    { wch: 12 },
    { wch: 22 },
    { wch: 14 },
    { wch: 22 },
    { wch: 16 },
    { wch: 24 },
    { wch: 28 },
    ...Array.from({ length: 5 + data.feeColumns.length }, () => ({ wch: 18 })),
  ];
  XLSX.utils.book_append_sheet(workbook, summarySheet, "柜组收益明细");

  const feeDetailSheet = XLSX.utils.aoa_to_sheet(data.feeDetailRows);
  if (data.feeDetailRows.length > 0) {
    styleDataSheet(feeDetailSheet, data.feeDetailRows, 10);
  }
  feeDetailSheet["!cols"] = [
    { wch: 12 },
    { wch: 12 },
    { wch: 12 },
    { wch: 22 },
    { wch: 14 },
    { wch: 22 },
    { wch: 16 },
    { wch: 24 },
    { wch: 14 },
    { wch: 28 },
    { wch: 18 },
  ];
  XLSX.utils.book_append_sheet(workbook, feeDetailSheet, "收费分类明细");

  const notesSheet = XLSX.utils.aoa_to_sheet(data.notesRows);
  notesSheet["!cols"] = [{ wch: 22 }, { wch: 72 }];
  const titleCell = notesSheet.A1;
  if (titleCell) {
    titleCell.s = {
      font: { bold: true, sz: 16, color: { rgb: "1E3A5F" } },
    };
  }
  XLSX.utils.book_append_sheet(workbook, notesSheet, "导出说明");

  workbook.Props = {
    Title: "收益看板柜组最明细",
    Subject: `${startDate} 至 ${endDate}`,
    Author: "ShopView",
  };
  XLSX.writeFile(workbook, data.filename);
}
