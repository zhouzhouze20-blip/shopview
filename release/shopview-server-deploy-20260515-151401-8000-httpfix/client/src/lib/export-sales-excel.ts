import * as XLSX from "xlsx";

function clampSheetName(name: string): string {
  return name.length > 31 ? name.slice(0, 31) : name;
}

function n(v: unknown): number {
  const x = Number(v ?? 0);
  return Number.isFinite(x) ? x : 0;
}

/** 毛利率等：比率为 0–1，导出为百分比数值（如 12.34 表示 12.34%） */
function marginPctDisplay(ratio: unknown): number {
  const r = n(ratio);
  return Math.round(r * 10000) / 100;
}

function yoyDisplay(current: number, prior: number): string {
  const p = prior;
  const c = current;
  if (!(p > 0)) return "—";
  const pct = ((c - p) / p) * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

function safeFilenamePart(s: string): string {
  return s.replace(/[/\\?%*:|"<>]/g, "_");
}

function buildFilename(prefix: string, startDate: string, endDate: string, extra?: string): string {
  const mid = extra ? `_${safeFilenamePart(extra)}` : "";
  return `销售看板_${safeFilenamePart(prefix)}_${safeFilenamePart(startDate)}_${safeFilenamePart(endDate)}${mid}.xlsx`;
}

function writeWorkbook(sheetName: string, aoa: (string | number)[][], filename: string): void {
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, clampSheetName(sheetName));
  XLSX.writeFile(wb, filename);
}

// --- 门店 ---

export type StoreSummaryExport = {
  store_id: string;
  store_name: string;
  department_count: number;
  group_count: number;
  ticket_count: number;
  quantity: number;
  effective_sales: number;
  net_profit: number;
  net_margin?: number;
  ticket_margin?: number;
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
  same_period_ticket_count?: number;
  same_period_margin?: number;
};

export function exportStoresToExcel(rows: StoreSummaryExport[], startDate: string, endDate: string): void {
  const header = [
    "门店名称",
    "门店编码",
    "本期销售收入",
    "同期销售收入",
    "销售收入同比",
    "毛利",
    "同期毛利",
    "本期毛利率(%)",
    "同期毛利率(%)",
    "同期小票数",
  ];
  const body = rows.map((row) => [
    row.store_name || row.store_id,
    row.store_id,
    n(row.effective_sales),
    n(row.same_period_effective_sales),
    yoyDisplay(n(row.effective_sales), n(row.same_period_effective_sales)),
    n(row.net_profit),
    n(row.same_period_net_profit),
    marginPctDisplay(row.ticket_margin ?? row.net_margin),
    marginPctDisplay(row.same_period_margin),
    n(row.same_period_ticket_count),
  ]);

  let totEff = 0;
  let totSameEff = 0;
  let totProfit = 0;
  let totSameTicket = 0;
  let totSameProfit = 0;
  for (const row of rows) {
    totEff += n(row.effective_sales);
    totSameEff += n(row.same_period_effective_sales);
    totProfit += n(row.net_profit);
    totSameTicket += n(row.same_period_ticket_count);
    totSameProfit += n(row.same_period_net_profit);
  }
  const marginTotal = totEff > 0 ? (totProfit / totEff) * 100 : 0;
  const sameMarginTotal = totSameEff > 0 ? (totSameProfit / totSameEff) * 100 : 0;
  const footer: (string | number)[] = [
    "合计",
    "",
    totEff,
    totSameEff,
    yoyDisplay(totEff, totSameEff),
    totProfit,
    totSameProfit,
    Math.round(marginTotal * 100) / 100,
    Math.round(sameMarginTotal * 100) / 100,
    totSameTicket,
  ];

  const aoa = [header, ...body, footer];
  writeWorkbook("门店销售汇总", aoa, buildFilename("门店", startDate, endDate));
}

// --- 部门 ---

export type DepartmentSummaryExport = {
  department_code: string;
  department_name: string;
  group_count: number;
  ticket_count: number;
  quantity: number;
  effective_sales: number;
  net_profit: number;
  ticket_margin: number;
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
  same_period_ticket_count?: number;
  same_period_margin?: number;
};

export function exportDepartmentsToExcel(rows: DepartmentSummaryExport[], startDate: string, endDate: string): void {
  const header = [
    "部门名称",
    "部门编码",
    "本期销售收入",
    "同期销售收入",
    "销售收入同比",
    "毛利",
    "同期毛利",
    "本期毛利率(%)",
    "同期毛利率(%)",
    "同期小票数",
  ];
  const body = rows.map((row) => [
    row.department_name,
    row.department_code || "",
    n(row.effective_sales),
    n(row.same_period_effective_sales),
    yoyDisplay(n(row.effective_sales), n(row.same_period_effective_sales)),
    n(row.net_profit),
    n(row.same_period_net_profit),
    marginPctDisplay(row.ticket_margin),
    marginPctDisplay(row.same_period_margin),
    n(row.same_period_ticket_count),
  ]);

  let totEff = 0;
  let totSameEff = 0;
  let totProfit = 0;
  let totSameTicket = 0;
  let totSameProfit = 0;
  for (const row of rows) {
    totEff += n(row.effective_sales);
    totSameEff += n(row.same_period_effective_sales);
    totProfit += n(row.net_profit);
    totSameTicket += n(row.same_period_ticket_count);
    totSameProfit += n(row.same_period_net_profit);
  }
  const marginTotal = totEff > 0 ? (totProfit / totEff) * 100 : 0;
  const sameMarginTotal = totSameEff > 0 ? (totSameProfit / totSameEff) * 100 : 0;
  const footer: (string | number)[] = [
    "合计",
    "",
    totEff,
    totSameEff,
    yoyDisplay(totEff, totSameEff),
    totProfit,
    totSameProfit,
    Math.round(marginTotal * 100) / 100,
    Math.round(sameMarginTotal * 100) / 100,
    totSameTicket,
  ];

  writeWorkbook("部门销售汇总", [header, ...body, footer], buildFilename("部门", startDate, endDate));
}

// --- 柜组 ---

export type GroupSummaryExport = {
  group_code: string;
  group_name?: string | null;
  department_name?: string | null;
  ticket_count: number;
  quantity: number;
  effective_sales: number;
  net_profit: number;
  ticket_margin: number;
  net_margin: number;
  same_period_ticket_count?: number;
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
  same_period_margin?: number;
};

export function exportGroupsToExcel(rows: GroupSummaryExport[], startDate: string, endDate: string): void {
  const header = [
    "柜组名称",
    "柜组编码",
    "本期销售收入",
    "同期销售收入",
    "销售收入同比",
    "毛利",
    "同期毛利",
    "本期毛利率(%)",
    "同期毛利率(%)",
    "同期小票数",
  ];
  const body = rows.map((row) => [
    row.group_name || row.group_code,
    row.group_code,
    n(row.effective_sales),
    n(row.same_period_effective_sales),
    yoyDisplay(n(row.effective_sales), n(row.same_period_effective_sales)),
    n(row.net_profit),
    n(row.same_period_net_profit),
    marginPctDisplay(row.ticket_margin ?? row.net_margin),
    marginPctDisplay(row.same_period_margin),
    n(row.same_period_ticket_count),
  ]);

  let totEff = 0;
  let totSameEff = 0;
  let totProfit = 0;
  let totSameTicket = 0;
  let totSameProfit = 0;
  for (const row of rows) {
    totEff += n(row.effective_sales);
    totSameEff += n(row.same_period_effective_sales);
    totProfit += n(row.net_profit);
    totSameTicket += n(row.same_period_ticket_count);
    totSameProfit += n(row.same_period_net_profit);
  }
  const marginTotal = totEff > 0 ? (totProfit / totEff) * 100 : 0;
  const sameMarginTotal = totSameEff > 0 ? (totSameProfit / totSameEff) * 100 : 0;
  const footer: (string | number)[] = [
    "合计",
    "",
    totEff,
    totSameEff,
    yoyDisplay(totEff, totSameEff),
    totProfit,
    totSameProfit,
    Math.round(marginTotal * 100) / 100,
    Math.round(sameMarginTotal * 100) / 100,
    totSameTicket,
  ];

  writeWorkbook("柜组销售汇总", [header, ...body, footer], buildFilename("柜组", startDate, endDate));
}

// --- 部门商品分析 ---

export type DepartmentGoodsSummaryExport = {
  group_code?: string | null;
  group_name?: string | null;
  goods_code: string;
  barcode?: string | null;
  goods_name?: string | null;
  category_code?: string | null;
  category_name?: string | null;
  brand_code?: string | null;
  brand_name?: string | null;
  supplier_code?: string | null;
  supplier_name?: string | null;
  operation_method?: string | null;
  ticket_count: number;
  sales_qty: number;
  sales_amount: number;
  sales_revenue: number;
  sales_cost: number;
  sales_cost_adjustment: number;
  supplier_discount: number;
  gross_profit: number;
  gross_margin_rate: number;
};

export type DepartmentSupplierSummaryExport = {
  supplier_code: string;
  supplier_name?: string | null;
  group_count: number;
  goods_count: number;
  ticket_count: number;
  sales_qty: number;
  sales_amount: number;
  sales_revenue: number;
  sales_cost: number;
  sales_cost_adjustment: number;
  supplier_discount: number;
  gross_profit: number;
  gross_margin_rate: number;
};

function departmentGoodsFooter(rows: DepartmentGoodsSummaryExport[] | DepartmentSupplierSummaryExport[]): (string | number)[] {
  let ticketCount = 0;
  let qty = 0;
  let salesAmount = 0;
  let revenue = 0;
  let cost = 0;
  let costAdjustment = 0;
  let supplierDiscount = 0;
  let profit = 0;
  for (const row of rows) {
    ticketCount += n(row.ticket_count);
    qty += n(row.sales_qty);
    salesAmount += n(row.sales_amount);
    revenue += n(row.sales_revenue);
    cost += n(row.sales_cost);
    costAdjustment += n(row.sales_cost_adjustment);
    supplierDiscount += n(row.supplier_discount);
    profit += n(row.gross_profit);
  }
  return [
    "合计",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    ticketCount,
    qty,
    salesAmount,
    revenue,
    cost,
    costAdjustment,
    supplierDiscount,
    profit,
    revenue > 0 ? Math.round((profit / revenue) * 10000) / 100 : 0,
  ];
}

export function exportDepartmentGoodsToExcel(
  rows: DepartmentGoodsSummaryExport[],
  options: { startDate: string; endDate: string; departmentName?: string | null },
): void {
  const header = [
    "柜组",
    "商品代码",
    "商品条码",
    "商品名称",
    "类别",
    "品牌",
    "供应商",
    "经营方式",
    "小票数",
    "销售数量",
    "销售金额",
    "销售收入",
    "销售成本",
    "销售成本调整",
    "供应商折扣",
    "毛利",
    "毛利率(%)",
  ];
  const body = rows.map((row) => [
    row.group_name ? `${row.group_code || ""} ${row.group_name}`.trim() : row.group_code || "",
    row.goods_code,
    row.barcode || "",
    row.goods_name || "",
    row.category_name ? `${row.category_code || ""} ${row.category_name}`.trim() : row.category_code || "",
    row.brand_name ? `${row.brand_code || ""} ${row.brand_name}`.trim() : row.brand_code || "",
    row.supplier_name ? `${row.supplier_code || ""} ${row.supplier_name}`.trim() : row.supplier_code || "",
    row.operation_method || "",
    n(row.ticket_count),
    n(row.sales_qty),
    n(row.sales_amount),
    n(row.sales_revenue),
    n(row.sales_cost),
    n(row.sales_cost_adjustment),
    n(row.supplier_discount),
    n(row.gross_profit),
    marginPctDisplay(row.gross_margin_rate),
  ]);
  writeWorkbook(
    "部门商品明细",
    [header, ...body, departmentGoodsFooter(rows)],
    buildFilename("部门商品明细", options.startDate, options.endDate, options.departmentName || undefined),
  );
}

export function exportDepartmentSuppliersToExcel(
  rows: DepartmentSupplierSummaryExport[],
  options: { startDate: string; endDate: string; departmentName?: string | null },
): void {
  const header = [
    "供应商",
    "柜组数",
    "商品数",
    "小票数",
    "销售数量",
    "销售金额",
    "销售收入",
    "销售成本",
    "销售成本调整",
    "供应商折扣",
    "毛利",
    "毛利率(%)",
  ];
  const body = rows.map((row) => [
    row.supplier_name ? `${row.supplier_code || ""} ${row.supplier_name}`.trim() : row.supplier_code || "",
    n(row.group_count),
    n(row.goods_count),
    n(row.ticket_count),
    n(row.sales_qty),
    n(row.sales_amount),
    n(row.sales_revenue),
    n(row.sales_cost),
    n(row.sales_cost_adjustment),
    n(row.supplier_discount),
    n(row.gross_profit),
    marginPctDisplay(row.gross_margin_rate),
  ]);
  let groupCount = 0;
  let goodsCount = 0;
  for (const row of rows) {
    groupCount += n(row.group_count);
    goodsCount += n(row.goods_count);
  }
  const footer = departmentGoodsFooter(rows);
  writeWorkbook(
    "部门供应商汇总",
    [header, ...body, ["合计", groupCount, goodsCount, ...footer.slice(8)]],
    buildFilename("部门供应商汇总", options.startDate, options.endDate, options.departmentName || undefined),
  );
}

// --- 小票 ---

export type TicketSummaryExport = {
  billno: string | number;
  sale_date?: string | null;
  sale_datetime?: string | null;
  invoice_no?: string | number | null;
  cashier?: string | null;
  quantity: number;
  effective_sales: number;
  net_profit: number;
  ticket_margin: number;
  authorized_discount?: number;
  mzk?: number;
  lq?: number;
  point?: number;
  consumption_point?: number;
  birthday_month_member_point?: number;
  transaction_type?: string | null;
};

export function exportTicketsToExcel(
  rows: TicketSummaryExport[],
  options: {
    startDate: string;
    endDate: string;
    groupCode: string;
    groupName?: string | null;
    viewMode: "current" | "prior";
  },
): void {
  const modeLabel = options.viewMode === "prior" ? "上年同期" : "本期";
  const header = [
    "单据号",
    "日期",
    "销售类型",
    "小票号",
    "收银员",
    "商品数",
    "销售收入",
    "毛利",
    "毛利率(%)",
    "授权折扣",
    "面值卡(MZK)",
    "礼券(LQ)",
    "消费加积分",
    "生日月会员加积分",
  ];
  const body = rows.map((row) => [
    row.billno,
    String(row.sale_datetime || row.sale_date || "").trim() || "—",
    String(row.transaction_type || "").trim() || "—",
    row.invoice_no != null && `${row.invoice_no}` !== "" ? row.invoice_no : "—",
    row.cashier || "—",
    n(row.quantity),
    n(row.effective_sales),
    n(row.net_profit),
    marginPctDisplay(row.ticket_margin),
    n(row.authorized_discount),
    n(row.mzk),
    n(row.lq),
    n(row.consumption_point),
    n(row.birthday_month_member_point),
  ]);

  let sumQty = 0;
  let sumSales = 0;
  let sumProfit = 0;
  let sumAuthZk = 0;
  let sumMzk = 0;
  let sumLq = 0;
  let sumConsumptionPoint = 0;
  let sumBirthdayMonthMemberPoint = 0;
  for (const row of rows) {
    sumQty += n(row.quantity);
    sumSales += n(row.effective_sales);
    sumProfit += n(row.net_profit);
    sumAuthZk += n(row.authorized_discount);
    sumMzk += n(row.mzk);
    sumLq += n(row.lq);
    sumConsumptionPoint += n(row.consumption_point);
    sumBirthdayMonthMemberPoint += n(row.birthday_month_member_point);
  }
  const marginAll = sumSales > 0 ? (sumProfit / sumSales) * 100 : 0;
  const footer: (string | number)[] = [
    "合计",
    "",
    "",
    "",
    "",
    sumQty,
    sumSales,
    sumProfit,
    Math.round(marginAll * 100) / 100,
    sumAuthZk,
    sumMzk,
    sumLq,
    sumConsumptionPoint,
    sumBirthdayMonthMemberPoint,
  ];

  const groupTag = options.groupName
    ? `${options.groupCode}_${options.groupName}`
    : options.groupCode;
  const filename = buildFilename(
    "小票",
    options.startDate,
    options.endDate,
    `${safeFilenamePart(groupTag)}_${modeLabel}`,
  );

  writeWorkbook(`小票_${modeLabel}`, [header, ...body, footer], filename);
}
