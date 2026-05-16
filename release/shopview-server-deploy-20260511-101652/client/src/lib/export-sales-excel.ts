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
