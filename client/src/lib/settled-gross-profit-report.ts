export const SETTLED_GROSS_PROFIT_ALL_STORES = "all";
export const SETTLED_GROSS_PROFIT_ALL_DEPARTMENTS = "all";

export interface SettledGrossProfitRow {
  store_code: string;
  store_name: string | null;
  department_code: string;
  department_name: string;
  group_code: string;
  group_name: string;
  supplier_code: string;
  supplier_name: string;
  floor_code: string;
  floor_name: string;
  business_area: number | null;
  operation_mode_code: string;
  operation_mode_name: string;
  area_code: string | null;
  area_name: string;
  contract_code: string | null;
  sales_qty: number | null;
  sales_revenue: number | null;
  tax_excluded_sales: number | null;
  front_profit: number | null;
  tax_excluded_profit_adjustment: number | null;
  floor_adjustment: number | null;
  sales_floor_cost: number | null;
  original_rate_profit: number | null;
  appliance_rebate: number | null;
  contract_end_date: string | null;
  contract_profit: number | null;
}

export interface SettledGrossProfitTotals {
  sales_qty: number | null;
  sales_revenue: number | null;
  tax_excluded_sales: number | null;
  front_profit: number | null;
  tax_excluded_profit_adjustment: number | null;
  floor_adjustment: number | null;
  sales_floor_cost: number | null;
  original_rate_profit: number | null;
  appliance_rebate: number | null;
  contract_profit: number | null;
}

export interface SettledGrossProfitResponse {
  dates: { start_date: string; end_date: string };
  selected_store: string | null;
  selected_department: string | null;
  rows: SettledGrossProfitRow[];
  totals: SettledGrossProfitTotals;
  quality: {
    row_count: number;
    unresolved_contract_group_count: number;
    unresolved_contract_sales: number;
    missing_supplier_name_count: number;
    missing_area_name_count: number;
  };
  generated_at: string;
}

export function buildSettledGrossProfitParams(
  start: string,
  end: string,
  storeId: string,
  departmentId: string,
): URLSearchParams {
  const params = new URLSearchParams({ start_date: start, end_date: end });
  if (storeId && storeId !== SETTLED_GROSS_PROFIT_ALL_STORES) {
    params.set("store_id", storeId);
  }
  if (departmentId && departmentId !== SETTLED_GROSS_PROFIT_ALL_DEPARTMENTS) {
    params.set("department_id", departmentId);
  }
  return params;
}

export function formatSettledMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatSettledQuantity(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

export function paginateSettledRows<T>(
  rows: readonly T[],
  page: number,
  pageSize = 50,
): T[] {
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(totalPages, Math.max(1, Math.trunc(page) || 1));
  return rows.slice((safePage - 1) * pageSize, safePage * pageSize);
}

export function settledGrossProfitMessage(state: {
  isLoading?: boolean;
  error?: unknown;
  hasData?: boolean;
  rowCount?: number;
}): string | null {
  if (state.isLoading) return "正在加载报表…";
  if (state.error) {
    const message = state.error instanceof Error ? state.error.message : String(state.error);
    return /403|无功能权限|无权限/.test(message)
      ? "无权限查看此报表"
      : "报表加载失败，请稍后重试";
  }
  if (state.hasData && state.rowCount === 0) return "暂无数据";
  return null;
}
