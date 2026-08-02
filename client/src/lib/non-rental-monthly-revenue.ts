export const NON_RENTAL_ALL_DEPARTMENTS = "all";

export type NonRentalMonthlyMetricKey =
  | "tax_included_sales"
  | "tax_excluded_sales"
  | "gross_profit"
  | "fee"
  | "contribution"
  | "gross_margin"
  | "contract_profit"
  | "concession_loss"
  | "concession_loss_rate";

export type NonRentalMonthlyRowType =
  | "brand"
  | "department_total"
  | "special_total"
  | "store_total";

export interface NonRentalMonthlyMetrics {
  tax_included_sales: number;
  tax_excluded_sales: number;
  gross_profit: number;
  fee: number;
  contribution: number;
  gross_margin: number | null;
  contract_profit: number;
  concession_loss: number;
  concession_loss_rate: number | null;
}

export interface NonRentalMonthlyRevenueRow {
  row_type: NonRentalMonthlyRowType;
  row_key: string;
  store_code: string;
  store_name: string;
  big_category: string;
  department_code: string;
  department_name: string;
  floor_code: string;
  floor_name: string;
  area_code: string;
  area_name: string;
  category_code: string;
  category_name: string;
  group_code: string;
  group_name: string;
  brand_code: string;
  brand_name: string;
  is_special_sale: boolean;
  months: Record<string, NonRentalMonthlyMetrics>;
  annual: NonRentalMonthlyMetrics;
}

export interface NonRentalMonthlyRevenueResponse {
  financial_year: number;
  dates: { start_date: string; end_date: string };
  periods: Array<{
    month: number;
    label: string;
    start_date: string;
    end_date: string;
  }>;
  selected_store: string;
  selected_department: string | null;
  regular_rows: NonRentalMonthlyRevenueRow[];
  special_rows: NonRentalMonthlyRevenueRow[];
  grand_total: NonRentalMonthlyRevenueRow;
  quality: {
    regular_brand_count: number;
    special_brand_count: number;
    missing_area_category_count: number;
    latest_sales_date: string | null;
  };
  scope_description: string;
  generated_at: string;
}

export const NON_RENTAL_MONTHLY_METRICS: ReadonlyArray<{
  key: NonRentalMonthlyMetricKey;
  label: string;
  kind: "amount" | "rate";
}> = [
  { key: "tax_included_sales", label: "销售含税", kind: "amount" },
  { key: "tax_excluded_sales", label: "销售不含税", kind: "amount" },
  { key: "gross_profit", label: "毛利额", kind: "amount" },
  { key: "fee", label: "收费", kind: "amount" },
  { key: "contribution", label: "贡献值", kind: "amount" },
  { key: "gross_margin", label: "毛利率", kind: "rate" },
  { key: "contract_profit", label: "合同毛利", kind: "amount" },
  { key: "concession_loss", label: "让利损失额", kind: "amount" },
  { key: "concession_loss_rate", label: "让利损失率", kind: "rate" },
];

export function buildNonRentalMonthlyRevenueParams(filters: {
  financialYear: number;
  storeId: string;
  departmentId?: string;
}): URLSearchParams {
  const params = new URLSearchParams({
    financial_year: String(filters.financialYear),
    store_id: filters.storeId.trim(),
  });
  const departmentId = filters.departmentId?.trim();
  if (departmentId && departmentId !== NON_RENTAL_ALL_DEPARTMENTS) {
    params.set("department_id", departmentId);
  }
  return params;
}

export function formatNonRentalMetric(
  metrics: NonRentalMonthlyMetrics,
  key: NonRentalMonthlyMetricKey,
  kind: "amount" | "rate",
): string {
  const value = metrics[key];
  if (value === null || value === undefined) return "—";
  if (kind === "rate") {
    return `${(value * 100).toLocaleString("zh-CN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}%`;
  }
  return (value / 10_000).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function financialMonthPeriodLabel(
  financialYear: number,
  month: number,
): string {
  if (month === 1) {
    return `${financialYear}-01-01 至 ${financialYear}-01-28`;
  }
  if (month === 12) {
    return `${financialYear}-11-29 至 ${financialYear}-12-31`;
  }

  const startYear = financialYear;
  const startMonth = month - 1;
  const previousMonthDays = new Date(startYear, startMonth, 0).getDate();
  const start = previousMonthDays >= 29
    ? `${startYear}-${String(startMonth).padStart(2, "0")}-29`
    : `${financialYear}-${String(month).padStart(2, "0")}-01`;
  return `${start} 至 ${financialYear}-${String(month).padStart(2, "0")}-28`;
}

export function rowTone(rowType: NonRentalMonthlyRowType): string {
  return rowType === "brand" ? "" : "bg-[#b4c6e7] font-semibold";
}
