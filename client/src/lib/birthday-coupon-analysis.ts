import XLSX from "xlsx-js-style";

export type BirthdayCouponRow = Record<string, number | string | boolean | null>;

export type BirthdayCouponReport = {
  scope: BirthdayCouponRow;
  summary: BirthdayCouponRow;
  monthly: BirthdayCouponRow[];
  daily: BirthdayCouponRow[];
  departments: BirthdayCouponRow[];
  groups: BirthdayCouponRow[];
  members: BirthdayCouponRow[];
  quality_issues: BirthdayCouponRow[];
  detail: BirthdayCouponRow;
  source: Record<string, number | string | boolean | string[] | null | undefined> & { tables?: string[] };
};

export type BirthdayCouponExportDetails = {
  member_levels: BirthdayCouponRow[];
  level_members: BirthdayCouponRow[];
  member_sales: BirthdayCouponRow[];
  usage_flows: BirthdayCouponRow[];
  followups: BirthdayCouponRow[];
  detail: Record<string, unknown>;
};

const moneyValue = (value: unknown) => Number(value || 0);
const percentValue = (value: unknown) => (value === null || value === undefined ? null : Number(value) / 100);

export function birthdayCouponStatusLabel(status: unknown) {
  switch (String(status || "").toUpperCase()) {
    case "REDEEMED":
      return "已核销";
    case "EXPIRED_UNUSED":
      return "已过期未用";
    case "UNUSED":
      return "有效期内未用";
    default:
      return "待核对";
  }
}

export function maskBirthdayCouponMemberNo(value: unknown) {
  const text = String(value || "").trim();
  if (!text) return "—";
  if (text.length <= 4) return text;
  return `${text.slice(0, 2)}${"*".repeat(Math.min(6, Math.max(2, text.length - 6)))}${text.slice(-4)}`;
}

export function maskBirthdayCouponMemberName(value: unknown) {
  const text = String(value || "").trim();
  if (!text) return "—";
  if (text.length === 1) return text;
  return `${text.slice(0, 1)}${"*".repeat(Math.max(1, text.length - 1))}`;
}

export function birthdayCouponAssetLabel(couponNo: unknown, assetId: unknown, index?: number) {
  const couponText = String(couponNo || "").trim();
  if (couponText && !/^0+$/.test(couponText)) return couponText;
  const assetText = String(assetId || "").trim();
  if (assetText) return `资产序号 …${assetText.slice(-6)}`;
  return `第 ${Number(index || 0) + 1} 张券`;
}

export function birthdayCouponExportFilename(report: BirthdayCouponReport) {
  const couponType = String(report.scope.coupon_type || "L").toUpperCase();
  const couponName = String(report.scope.coupon_name || (couponType === "C" ? "美妆券" : "中心生日券"));
  const start = String(report.scope.start_month || "开始月");
  const end = String(report.scope.end_month || "结束月");
  return `中心${couponName}${couponType}券分析_${start}_${end}.xlsx`;
}

export function centerCouponGroupsForDepartment(report: BirthdayCouponReport, departmentCode: unknown) {
  const code = String(departmentCode || "");
  return (report.groups || []).filter((row) => String(row.department_code || "") === code);
}

const headerStyle = {
  font: { bold: true, color: { rgb: "FFFFFF" } },
  fill: { patternType: "solid", fgColor: { rgb: "334155" } },
  alignment: { horizontal: "center", vertical: "center" },
  border: {
    top: { style: "thin", color: { rgb: "CBD5E1" } },
    bottom: { style: "thin", color: { rgb: "CBD5E1" } },
    left: { style: "thin", color: { rgb: "CBD5E1" } },
    right: { style: "thin", color: { rgb: "CBD5E1" } },
  },
};

function styleSheet(
  sheet: XLSX.WorkSheet,
  widths: number[],
  options: { moneyColumns?: number[]; percentColumns?: number[]; freezeRows?: number } = {},
) {
  const range = XLSX.utils.decode_range(sheet["!ref"] || "A1:A1");
  for (let row = 1; row <= range.e.r; row += 1) {
    for (let column = range.s.c; column <= range.e.c; column += 1) {
      const cell = sheet[XLSX.utils.encode_cell({ r: row, c: column })];
      if (!cell) continue;
      cell.s = {
        ...(cell.s || {}),
        font: { color: { rgb: "1F2937" } },
        fill: { patternType: "solid", fgColor: { rgb: "FFFFFF" } },
        alignment: { vertical: "center" },
      };
    }
  }
  for (let column = range.s.c; column <= range.e.c; column += 1) {
    const cell = sheet[XLSX.utils.encode_cell({ r: 0, c: column })];
    if (cell) cell.s = headerStyle;
  }
  for (let row = 1; row <= range.e.r; row += 1) {
    for (const column of options.moneyColumns || []) {
      const cell = sheet[XLSX.utils.encode_cell({ r: row, c: column })];
      if (cell && typeof cell.v === "number") cell.z = "¥#,##0.00";
    }
    for (const column of options.percentColumns || []) {
      const cell = sheet[XLSX.utils.encode_cell({ r: row, c: column })];
      if (cell && typeof cell.v === "number") cell.z = "0.00%";
    }
  }
  sheet["!cols"] = widths.map((wch) => ({ wch }));
  sheet["!autofilter"] = { ref: XLSX.utils.encode_range({ r: 0, c: 0 }, { r: range.e.r, c: range.e.c }) };
  sheet["!freeze"] = { xSplit: 0, ySplit: options.freezeRows ?? 1 };
}

export function buildBirthdayCouponWorkbook(
  report: BirthdayCouponReport,
  exportDetails?: BirthdayCouponExportDetails,
) {
  const workbook = XLSX.utils.book_new();
  const couponType = String(report.scope.coupon_type || "L").toUpperCase();

  const monthlyRows = [
    [
      "发放月份",
      "发放会员人次",
      "发放金额",
      "净核销会员人次",
      "会员核销率",
      "净核销金额",
      "金额核销率",
      "未使用金额",
      "其中已过期未使用",
      "首个发放日",
      "最后发放日",
      "有效期起",
      "有效期止",
      "非1日发放笔数",
      "超额发放笔数",
      "面值异常笔数",
      "批次状态",
    ],
    ...report.monthly.map((row) => [
      String(row.period_month || "").slice(0, 7),
      Number(row.issued_member_count || 0),
      moneyValue(row.issued_amount),
      Number(row.net_redeemed_member_count || 0),
      percentValue(row.member_redemption_rate),
      moneyValue(row.net_redeemed_amount),
      percentValue(row.amount_redemption_rate),
      moneyValue(row.unused_amount),
      moneyValue(row.expired_unused_amount),
      row.first_issue_date || "",
      row.last_issue_date || "",
      row.valid_from || "",
      row.valid_to || "",
      Number(row.off_schedule_issue_count || 0),
      Number(row.duplicate_issue_count || 0),
      Number(row.face_value_exception_count || 0),
      row.cohort_status === "EXPIRED" ? "已到期" : "有效期内",
    ]),
  ];
  const monthlySheet = XLSX.utils.aoa_to_sheet(monthlyRows);
  styleSheet(monthlySheet, [12, 16, 16, 18, 14, 16, 14, 16, 20, 13, 13, 13, 13, 16, 16, 16, 12], {
    moneyColumns: [2, 5, 7, 8],
    percentColumns: [4, 6],
  });
  XLSX.utils.book_append_sheet(workbook, monthlySheet, "月度汇总");

  const departmentRows = [
    ["部门编码", "部门名称", "核销小票数", "带动销售额", `分摊${couponType}券金额`, "销售带动倍数", "销售毛利", "毛利率"],
    ...report.departments.map((row) => [
      row.department_code || "",
      row.department_name || "",
      Number(row.ticket_count || 0),
      moneyValue(row.driven_sales_amount),
      moneyValue(row.allocated_coupon_amount),
      Number(row.sales_leverage || 0),
      moneyValue(row.gross_profit),
      percentValue(row.gross_margin_rate),
    ]),
  ];
  const departmentSheet = XLSX.utils.aoa_to_sheet(departmentRows);
  styleSheet(departmentSheet, [14, 22, 14, 18, 18, 16, 18, 14], {
    moneyColumns: [3, 4, 6],
    percentColumns: [7],
  });
  XLSX.utils.book_append_sheet(workbook, departmentSheet, "部门带动");

  const groupRows = [
    ["部门编码", "部门名称", "柜组编码", "柜组名称", "核销小票数", "带动销售额", `分摊${couponType}券金额`, "销售带动倍数", "销售毛利", "毛利率"],
    ...(report.groups || []).map((row) => [
      row.department_code || "",
      row.department_name || "",
      row.group_code || "",
      row.group_name || "",
      Number(row.ticket_count || 0),
      moneyValue(row.driven_sales_amount),
      moneyValue(row.allocated_coupon_amount),
      Number(row.sales_leverage || 0),
      moneyValue(row.gross_profit),
      percentValue(row.gross_margin_rate),
    ]),
  ];
  const groupSheet = XLSX.utils.aoa_to_sheet(groupRows);
  styleSheet(groupSheet, [14, 22, 16, 26, 14, 18, 18, 16, 18, 14], {
    moneyColumns: [5, 6, 8],
    percentColumns: [9],
  });
  XLSX.utils.book_append_sheet(workbook, groupSheet, "柜组带动");

  const memberRows = [
    [
      "发放月份",
      "会员卡号",
      "会员等级",
      "发放笔数",
      "发放日期",
      "有效期起",
      "有效期止",
      "发放金额",
      "消费笔数",
      "首次核销日",
      "末次核销日",
      "核销金额",
      "退券金额",
      "消费冲正金额",
      "净核销金额",
      "未使用金额",
      "状态",
      "超额发放",
    ],
    ...report.members.map((row) => [
      String(row.period_month || "").slice(0, 7),
      row.member_no || "",
      row.customer_level || "",
      Number(row.issue_count || 0),
      row.issue_date || "",
      row.valid_from || "",
      row.valid_to || "",
      moneyValue(row.issued_amount),
      Number(row.consume_count || 0),
      row.first_redeem_date || "",
      row.last_redeem_date || "",
      moneyValue(row.gross_redeemed_amount),
      moneyValue(row.return_amount),
      moneyValue(row.consume_reverse_amount),
      moneyValue(row.net_redeemed_amount),
      moneyValue(row.unused_amount),
      birthdayCouponStatusLabel(row.redemption_status),
      row.duplicate_issue ? "是" : "否",
    ]),
  ];
  const memberSheet = XLSX.utils.aoa_to_sheet(memberRows);
  styleSheet(memberSheet, [12, 22, 12, 12, 13, 13, 13, 15, 12, 13, 13, 15, 15, 17, 15, 15, 16, 12], {
    moneyColumns: [7, 11, 12, 13, 14, 15],
  });
  XLSX.utils.book_append_sheet(workbook, memberSheet, "会员明细");

  if (exportDetails) {
    const levelRows = [
      ["发放月份", "会员级别", "领券会员", "发放张数", "发放金额", "净核销会员", "净核销金额", "当月消费会员", "当月小票", "当月消费金额"],
      ...exportDetails.member_levels.map((row) => [
        String(row.period_month || "").slice(0, 7),
        row.customer_level || "未识别",
        Number(row.issued_member_count || 0),
        Number(row.issue_count || 0),
        moneyValue(row.issued_amount),
        Number(row.redeemed_member_count || 0),
        moneyValue(row.net_redeemed_amount),
        Number(row.consuming_member_count || 0),
        Number(row.ticket_count || 0),
        moneyValue(row.monthly_sales_amount),
      ]),
    ];
    const levelSheet = XLSX.utils.aoa_to_sheet(levelRows);
    styleSheet(levelSheet, [12, 18, 14, 14, 16, 16, 16, 18, 14, 18], { moneyColumns: [4, 6, 9] });
    XLSX.utils.book_append_sheet(workbook, levelSheet, "会员级别汇总");

    const levelMemberRows = [
      ["发放月份", "会员卡号", "会员姓名", "会员级别", "发放张数", "发放金额", "净核销金额", "是否使用本券", "当月小票", "当月消费金额", "末次消费时间"],
      ...exportDetails.level_members.map((row) => [
        String(row.period_month || "").slice(0, 7),
        row.member_no || "",
        row.customer_name || "",
        row.customer_level || "未识别",
        Number(row.issue_count || 0),
        moneyValue(row.issued_amount),
        moneyValue(row.net_redeemed_amount),
        Number(row.net_redeemed_amount || 0) > 0 ? "是" : "否",
        Number(row.ticket_count || 0),
        moneyValue(row.monthly_sales_amount),
        row.last_sale_time || "",
      ]),
    ];
    const levelMemberSheet = XLSX.utils.aoa_to_sheet(levelMemberRows);
    styleSheet(levelMemberSheet, [12, 22, 16, 18, 14, 16, 16, 16, 14, 18, 20], { moneyColumns: [5, 6, 9] });
    XLSX.utils.book_append_sheet(workbook, levelMemberSheet, "会员月消费");

    const memberSalesRows = [
      ["发放月份", "会员卡号", "会员姓名", "会员级别", "销售时间", "业务单号", "SKU数", "数量", "消费金额", "消费部门", "消费柜组", "品牌编码"],
      ...exportDetails.member_sales.map((row) => [
        String(row.period_month || "").slice(0, 7),
        row.member_no || "",
        row.customer_name || "",
        row.customer_level || "未识别",
        row.sale_time || "",
        row.billno || "",
        Number(row.sku_count || 0),
        Number(row.quantity || 0),
        moneyValue(row.sales_amount),
        row.departments || "未归属部门",
        row.groups || "未归属柜组",
        row.brand_codes || "未标识",
      ]),
    ];
    const memberSalesSheet = XLSX.utils.aoa_to_sheet(memberSalesRows);
    styleSheet(memberSalesSheet, [12, 22, 16, 18, 20, 18, 12, 12, 16, 28, 32, 24], { moneyColumns: [8] });
    XLSX.utils.book_append_sheet(workbook, memberSalesSheet, "会员月消费小票");

    const usageRows = [
      ["发放月份", "会员卡号", "会员级别", "券资产序号", "券号", "发放日", "发生日", "动作", "发生金额", "券后余额", "销售时间", "业务单号", "收银机", "小票号", "消费柜组", "小票销售额"],
      ...exportDetails.usage_flows.map((row) => [
        String(row.period_month || "").slice(0, 7),
        row.member_no || "",
        row.customer_level || "未识别",
        row.coupon_asset_id || "",
        row.coupon_no || "",
        row.issue_date || "",
        row.flow_date || "",
        row.action_name || row.action_code || "",
        moneyValue(row.flow_amount),
        moneyValue(row.balance_amount),
        row.sale_time || "",
        row.billno || "",
        row.cashier_no || "",
        row.invoice_no || "",
        row.group_names || "未归属柜组",
        moneyValue(row.sales_amount),
      ]),
    ];
    const usageSheet = XLSX.utils.aoa_to_sheet(usageRows);
    styleSheet(usageSheet, [12, 22, 18, 22, 18, 13, 13, 14, 15, 15, 20, 18, 14, 14, 32, 16], {
      moneyColumns: [8, 9, 15],
    });
    XLSX.utils.book_append_sheet(workbook, usageSheet, "用券明细");

    if (couponType === "C") {
      const followupRows = [
        ["发放月份", "会员卡号", "会员姓名", "会员级别", "跟进品牌柜组编码", "跟进品牌柜组", "部门", "品类主管", "历史12月消费", "历史小票", "历史末次消费", "当月消费", "当月小票", "当月末次消费", "C券使用次数", "C券净核销", "状态"],
        ...(exportDetails.followups || []).map((row) => [
          String(row.period_month || "").slice(0, 7),
          row.member_no || "",
          row.customer_name || "",
          row.customer_level || "",
          row.followup_group_code || "",
          row.followup_group_name || "待分配",
          row.department_name || "",
          row.manager_name || "待维护",
          moneyValue(row.history_sales_amount),
          Number(row.history_ticket_count || 0),
          row.last_history_sale_time || "",
          moneyValue(row.current_sales_amount),
          Number(row.current_ticket_count || 0),
          row.last_current_sale_time || "",
          Number(row.coupon_use_count || 0),
          moneyValue(row.net_redeemed_amount),
          row.followup_status_label || "待核对",
        ]),
      ];
      const followupSheet = XLSX.utils.aoa_to_sheet(followupRows);
      styleSheet(followupSheet, [12, 22, 16, 18, 20, 28, 22, 16, 18, 14, 20, 18, 14, 20, 16, 16, 18], {
        moneyColumns: [8, 11, 15],
      });
      XLSX.utils.book_append_sheet(workbook, followupSheet, "C券会员跟进");
    }
  }

  const qualityRows = [
    ["月份", "问题编码", "问题", "数量"],
    ...report.quality_issues.map((row) => [
      row.period_month || "",
      row.issue_code || "",
      row.issue_name || "",
      Number(row.issue_count || 0),
    ]),
  ];
  const qualitySheet = XLSX.utils.aoa_to_sheet(qualityRows);
  styleSheet(qualitySheet, [12, 24, 28, 12]);
  XLSX.utils.book_append_sheet(workbook, qualitySheet, "异常核对");

  const noteRows = [
    ["项目", "说明"],
    ["分析对象", `${report.scope.store_name || "常州购物中心"} / ${couponType}券 / ${report.scope.coupon_name || "中心券"}`],
    ["发放识别", `动作码 ${report.scope.issue_action || "M"}；当前源表字典标为后台买券，业务按中心券批量发放解释`],
    ["预期规则", `每月${report.scope.expected_issue_day || 1}日发放；单张${report.scope.expected_face_value || 100}元；每位会员标准${report.scope.expected_issue_count_per_member || 1}张`],
    ["批次归属", report.source.cohort_rule || "按券日志有效期起始月归属发放批次"],
    ["会员核销率", "净核销会员人次 ÷ 发放会员人次；同一会员跨月分别计入对应券种批次"],
    ["金额核销率", "净核销金额 ÷ 发放金额；净核销扣除退券和消费冲正，计入退券冲正"],
    ["带动销售额", `使用${couponType}券小票的商品销售收入；跨部门/柜组小票按商品销售额归属，券金额按销售额比例分摊`],
    ["数据最新日", report.source.latest_data_date || "—"],
    ["发放日志覆盖起", report.source.issue_coverage_start || "—"],
    ["源表", Array.isArray(report.source.tables) ? report.source.tables.join("、") : "—"],
    ["导出范围", `${report.scope.start_month || ""} 至 ${report.scope.end_month || ""}`],
  ];
  const noteSheet = XLSX.utils.aoa_to_sheet(noteRows);
  styleSheet(noteSheet, [20, 100]);
  XLSX.utils.book_append_sheet(workbook, noteSheet, "口径说明");

  return workbook;
}

export function exportBirthdayCouponWorkbook(
  report: BirthdayCouponReport,
  exportDetails?: BirthdayCouponExportDetails,
) {
  XLSX.writeFile(buildBirthdayCouponWorkbook(report, exportDetails), birthdayCouponExportFilename(report));
}
