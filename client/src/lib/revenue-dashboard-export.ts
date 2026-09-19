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
  raw_sales_gross_profit_amount: number;
  raw_fee_amount: number;
  raw_extra_amount: number;
  sales_adjustment_amount: number;
  fee_adjustment_amount: number;
  extra_adjustment_amount: number;
  close_adjustment_amount: number;
  sales_gross_profit_amount: number;
  fee_amount: number;
  extra_amount: number;
  total_amount: number;
  fee_breakdown?: RevenueDashboardFeeBreakdown[];
};

export type RevenueDashboardExtraExportItem = {
  id: string;
  store_id: number;
  store_code?: string | null;
  store_name?: string | null;
  revenue_date: string;
  subject_code?: string | null;
  subject_name?: string | null;
  extra_type?: string | null;
  department_code?: string | null;
  department_name?: string | null;
  explanation?: string | null;
  voucher_no?: string | null;
  amount: number;
  source_detail_key?: string | null;
  source_group_code?: string | null;
  source_group_name?: string | null;
  unit_code?: string | null;
  match_method?: string | null;
  match_status?: string | null;
  match_reason?: string | null;
};

export type RevenueDashboardExportData = {
  filename: string;
  feeColumns: string[];
  summaryRows: Array<Array<string | number>>;
  feeDetailRows: Array<Array<string | number>>;
  extraSubjectRows: Array<Array<string | number>>;
  extraDetailRows: Array<Array<string | number>>;
  notesRows: Array<Array<string | number>>;
};

const amount = (value: number | null | undefined) => Number(value || 0);
const moneyDifference = (value: number) => (Math.abs(value) < 0.005 ? 0 : value);

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
  extraItems: RevenueDashboardExtraExportItem[] = [],
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
    "富基收费（调整前）",
    "富基收费对应月结调整",
    "富基收费（调整后）",
    "NC非富基收费（调整前）",
    "NC非富基对应月结调整",
    "NC非富基收费（调整后）",
    "月结调整合计",
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
      amount(item.raw_fee_amount),
      amount(item.fee_adjustment_amount),
      amount(item.fee_amount),
      amount(item.raw_extra_amount),
      amount(item.extra_adjustment_amount),
      amount(item.extra_amount),
      amount(item.close_adjustment_amount),
      amount(item.total_amount),
      moneyDifference(amount(item.fee_amount) - feeBreakdownTotal),
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
      "看板收费金额",
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

  const sortedExtraItems = [...extraItems].sort(
    (left, right) =>
      compareText(left.store_code || left.store_name, right.store_code || right.store_name) ||
      compareText(left.department_code || left.department_name, right.department_code || right.department_name) ||
      compareText(left.subject_code || left.subject_name, right.subject_code || right.subject_name) ||
      compareText(left.revenue_date, right.revenue_date) ||
      compareText(left.voucher_no, right.voucher_no) ||
      compareText(left.source_detail_key || left.id, right.source_detail_key || right.id),
  );

  const subjectBuckets = new Map<
    string,
    {
      store_code: string;
      store_name: string;
      department_code: string;
      department_name: string;
      subject_code: string;
      subject_name: string;
      extra_type: string;
      detail_count: number;
      amount: number;
    }
  >();
  sortedExtraItems.forEach((item) => {
    const storeCode = String(item.store_code || "");
    const storeName = String(item.store_name || "");
    const departmentCode = String(item.department_code || "");
    const departmentName = String(item.department_name || "未归属部门");
    const subjectCode = String(item.subject_code || "未编码");
    const subjectName = String(item.subject_name || item.extra_type || "未命名科目");
    const extraType = String(item.extra_type || "其他收益");
    const key = [
      storeCode,
      storeName,
      departmentCode,
      departmentName,
      subjectCode,
      subjectName,
      extraType,
    ].join("\u001f");
    const bucket = subjectBuckets.get(key) || {
      store_code: storeCode,
      store_name: storeName,
      department_code: departmentCode,
      department_name: departmentName,
      subject_code: subjectCode,
      subject_name: subjectName,
      extra_type: extraType,
      detail_count: 0,
      amount: 0,
    };
    bucket.detail_count += 1;
    bucket.amount += amount(item.amount);
    subjectBuckets.set(key, bucket);
  });

  const subjectDetailRows = Array.from(subjectBuckets.values())
    .sort(
      (left, right) =>
        compareText(left.store_code || left.store_name, right.store_code || right.store_name) ||
        compareText(left.department_code || left.department_name, right.department_code || right.department_name) ||
        compareText(left.subject_code || left.subject_name, right.subject_code || right.subject_name),
    )
    .map((row) => [
      startDate,
      endDate,
      row.store_code,
      row.store_name,
      row.department_code,
      row.department_name,
      row.subject_code,
      row.subject_name,
      row.extra_type,
      row.detail_count,
      row.amount,
    ]);
  const subjectTotalRow: Array<string | number> = [
    "",
    "",
    "",
    "合计",
    "",
    "",
    "",
    "",
    "",
    subjectDetailRows.reduce((sum, row) => sum + amount(row[9] as number), 0),
    subjectDetailRows.reduce((sum, row) => sum + amount(row[10] as number), 0),
  ];
  const extraSubjectRows = [
    [
      "开始日期",
      "结束日期",
      "门店编码",
      "门店",
      "部门编码",
      "部门",
      "科目编码",
      "科目名称",
      "收益类型",
      "明细笔数",
      "科目金额",
    ],
    ...subjectDetailRows,
    subjectTotalRow,
  ];

  const extraRawRows = sortedExtraItems.map((item) => [
    String(item.revenue_date || "").slice(0, 10),
    item.store_code || "",
    item.store_name || "",
    item.department_code || "",
    item.department_name || "未归属部门",
    item.subject_code || "未编码",
    item.subject_name || item.extra_type || "未命名科目",
    item.extra_type || "其他收益",
    item.explanation || "",
    item.voucher_no || "",
    item.source_group_code || "",
    item.source_group_name || "",
    item.unit_code || "",
    item.match_method || "",
    item.match_reason || "",
    amount(item.amount),
    item.source_detail_key || item.id,
  ]);
  const extraTotalRow: Array<string | number> = [
    "",
    "",
    "合计",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    extraRawRows.reduce((sum, row) => sum + amount(row[15] as number), 0),
    "",
  ];
  const extraDetailRows = [
    [
      "确认日期",
      "门店编码",
      "门店",
      "部门编码",
      "部门",
      "科目编码",
      "科目名称",
      "收益类型",
      "摘要",
      "NC凭证",
      "柜组编码",
      "柜组/来源部门",
      "图上经营单元",
      "匹配方式",
      "匹配说明",
      "金额",
      "来源明细键",
    ],
    ...extraRawRows,
    extraTotalRow,
  ];

  return {
    filename: `收益看板_柜组最明细_${startDate}_${endDate}.xlsx`,
    feeColumns,
    summaryRows: [
      [...staticHeaders, ...feeColumns.map((column) => `${column}（看板口径）`)],
      ...detailRows,
      totalRow,
    ],
    feeDetailRows,
    extraSubjectRows,
    extraDetailRows,
    notesRows: [
      ["收益看板导出说明"],
      ["查询日期", `${startDate} 至 ${endDate}`],
      ["日期口径", "销售毛利按财务日期；收费按付款日期且剔除票减及保证金；其他收益按财务期间"],
      ["数据范围", "仅导出当前账号数据权限范围内的数据"],
      ["明细粒度", "一行一个门店 / 部门 / 柜组"],
      ["销售毛利", "不含税；包含已计入销售毛利的损失承担"],
      ["富基收费", "调整前金额单独展示；未月结期间为去税金额，已确认月结期间使用含税原金额"],
      ["未付款收费", "未关联结算付款日期或租赁付款日期的收费不进入本次导出"],
      ["收费排除项", "票减收费、履约保证金及设备保证金不进入富基收费收益"],
      ["收费明细列", "按收费项目编码和名称动态展开；月结期间另含月结调整项目"],
      ["NC非富基收费", "调整前金额单独展示，包括已确认的 NC6051 电表、物业、营运等"],
      ["月结调整", "NC6051控制数－富基收费－NC非富基收费；保留原收费和NC明细，不直接覆盖"],
      ["其他收益科目汇总", "按门店、部门、NC科目和收益类型汇总，金额保留两位小数"],
      ["其他收益摘要明细", "按门店、部门、科目、确认日期排序；保留摘要、NC凭证、柜位归属和来源明细键"],
      ["总收益", "销售毛利（不含税） + 富基收费（调整前） + NC非富基收费（调整前） + 月结调整"],
      ["收费分类校验差额", "富基收费（调整后） - 各收费明细列合计；正常应为 0"],
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
  amountColumnEnd?: number,
) {
  const range = XLSX.utils.decode_range(sheet["!ref"] || "A1:A1");
  for (let column = range.s.c; column <= range.e.c; column += 1) {
    const header = sheet[XLSX.utils.encode_cell({ r: 0, c: column })];
    if (header) header.s = headerStyle;
  }
  for (let row = 1; row <= range.e.r; row += 1) {
    for (let column = range.s.c; column <= range.e.c; column += 1) {
      const cell = sheet[XLSX.utils.encode_cell({ r: row, c: column })];
      if (cell) {
        cell.s = {
          fill: { fgColor: { rgb: "FFFFFF" } },
          font: { color: { rgb: "0F172A" } },
          border: {
            bottom: { style: "hair", color: { rgb: "E2E8F0" } },
          },
        };
      }
    }
    const lastAmountColumn = Math.min(amountColumnEnd ?? range.e.c, range.e.c);
    for (let column = amountColumnStart; column <= lastAmountColumn; column += 1) {
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

export function buildRevenueDashboardWorkbook(
  items: RevenueDashboardExportItem[],
  startDate: string,
  endDate: string,
  extraItems: RevenueDashboardExtraExportItem[] = [],
) {
  const data = buildRevenueDashboardExportData(items, startDate, endDate, extraItems);
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
    ...Array.from({ length: 10 + data.feeColumns.length }, () => ({ wch: 18 })),
  ];
  XLSX.utils.book_append_sheet(workbook, summarySheet, "柜组收益明细");

  const feeDetailSheet = XLSX.utils.aoa_to_sheet(data.feeDetailRows);
  if (data.feeDetailRows.length > 0) {
    styleDataSheet(feeDetailSheet, data.feeDetailRows, 10, false, 10);
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

  const extraSubjectSheet = XLSX.utils.aoa_to_sheet(data.extraSubjectRows);
  styleDataSheet(extraSubjectSheet, data.extraSubjectRows, 10, true, 10);
  const extraSubjectRange = XLSX.utils.decode_range(extraSubjectSheet["!ref"] || "A1:A1");
  for (let row = 1; row <= extraSubjectRange.e.r; row += 1) {
    const countCell = extraSubjectSheet[XLSX.utils.encode_cell({ r: row, c: 9 })];
    if (countCell) countCell.z = "#,##0";
  }
  extraSubjectSheet["!cols"] = [
    { wch: 12 },
    { wch: 12 },
    { wch: 12 },
    { wch: 22 },
    { wch: 14 },
    { wch: 24 },
    { wch: 14 },
    { wch: 24 },
    { wch: 16 },
    { wch: 12 },
    { wch: 18 },
  ];
  XLSX.utils.book_append_sheet(workbook, extraSubjectSheet, "其他收益科目汇总");

  const extraDetailSheet = XLSX.utils.aoa_to_sheet(data.extraDetailRows);
  styleDataSheet(extraDetailSheet, data.extraDetailRows, 15, true, 15);
  extraDetailSheet["!cols"] = [
    { wch: 12 },
    { wch: 12 },
    { wch: 22 },
    { wch: 14 },
    { wch: 24 },
    { wch: 14 },
    { wch: 24 },
    { wch: 16 },
    { wch: 56 },
    { wch: 30 },
    { wch: 18 },
    { wch: 28 },
    { wch: 20 },
    { wch: 22 },
    { wch: 42 },
    { wch: 18 },
    { wch: 38 },
  ];
  XLSX.utils.book_append_sheet(workbook, extraDetailSheet, "其他收益摘要明细");

  const notesSheet = XLSX.utils.aoa_to_sheet(data.notesRows);
  notesSheet["!cols"] = [{ wch: 22 }, { wch: 72 }];
  const notesRange = XLSX.utils.decode_range(notesSheet["!ref"] || "A1:A1");
  for (let row = notesRange.s.r; row <= notesRange.e.r; row += 1) {
    for (let column = notesRange.s.c; column <= notesRange.e.c; column += 1) {
      const cell = notesSheet[XLSX.utils.encode_cell({ r: row, c: column })];
      if (cell) {
        cell.s = {
          fill: { fgColor: { rgb: "FFFFFF" } },
          font: { color: { rgb: "0F172A" } },
        };
      }
    }
  }
  const titleCell = notesSheet.A1;
  if (titleCell) {
    titleCell.s = {
      font: { bold: true, sz: 16, color: { rgb: "1E3A5F" } },
      fill: { fgColor: { rgb: "FFFFFF" } },
    };
  }
  XLSX.utils.book_append_sheet(workbook, notesSheet, "导出说明");

  workbook.Props = {
    Title: "收益看板柜组最明细",
    Subject: `${startDate} 至 ${endDate}`,
    Author: "ShopView",
  };
  return { workbook, filename: data.filename };
}

export function exportRevenueDashboardExcel(
  items: RevenueDashboardExportItem[],
  startDate: string,
  endDate: string,
  extraItems: RevenueDashboardExtraExportItem[] = [],
) {
  const { workbook, filename } = buildRevenueDashboardWorkbook(
    items,
    startDate,
    endDate,
    extraItems,
  );
  XLSX.writeFile(workbook, filename);
}
