import { findFinancialMonthContaining, getFinancialMonthWindow } from "./financialMonth.ts";

export type FinancialMonthSalesRow = {
  store_id?: string;
  department_code?: string;
  department_name?: string;
  group_code?: string;
  effective_sales: number;
  same_period_effective_sales?: number;
};

/** 按已应用筛选的截止日计算财务月累计；同期按去年同日截止，不能使用主页的「财务月已过天数」对齐。 */
export function buildMobileFinancialMonthDates(endDate: string) {
  const window = findFinancialMonthContaining(endDate);
  const priorWindow = getFinancialMonthWindow(window.year - 1, window.index);
  const [, month, day] = endDate.split("-").map(Number);
  const priorDay = Math.min(day, new Date(window.year - 1, month, 0).getDate());
  const priorEnd = `${window.year - 1}-${String(month).padStart(2, "0")}-${String(priorDay).padStart(2, "0")}`;
  return {
    start_date: window.start,
    end_date: endDate,
    prior_start_date: priorWindow.start,
    prior_end_date: priorEnd,
  };
}

export function buildMobileFinancialMonthRequest({
  endDate,
  level,
  storeId,
  departmentCode,
  keyword,
  includeRentalAndBackofficeSales,
}: {
  endDate: string;
  level: string;
  storeId?: string;
  departmentCode?: string;
  keyword?: string;
  includeRentalAndBackofficeSales: boolean;
}): string | null {
  if (!["stores", "departments", "groups"].includes(level)) return null;
  if (level !== "stores" && !storeId) return null;
  if (level === "groups" && departmentCode === undefined) return null;
  const dates = buildMobileFinancialMonthDates(endDate);
  // 闰年2月29日属于第3财务月，去年同日回退为2月28日，尚未进入去年第3期。
  if (dates.prior_start_date > dates.prior_end_date) return null;
  const params = new URLSearchParams({
    ...dates,
    exclude_rental: String(!includeRentalAndBackofficeSales),
    exclude_backoffice_departments: String(!includeRentalAndBackofficeSales),
    // 独立的月累计排序可能不同于页面日销售排序，取接口允许的最大范围。
    limit: "1000",
  });
  if (level !== "stores") params.set("store_id", storeId!);
  if (level === "groups") {
    if (departmentCode?.trim()) params.set("department_code", departmentCode);
    else params.set("unassigned_department", "true");
    if (keyword) params.set("keyword", keyword);
  }
  return `/api/sales/summary/${level}?${params}`;
}

export function financialMonthRowKey(level: string, row: FinancialMonthSalesRow): string {
  if (level === "stores") return row.store_id ?? "";
  if (level === "departments") return `${row.department_code ?? ""}:${row.department_name ?? ""}`;
  return row.group_code ?? "";
}
