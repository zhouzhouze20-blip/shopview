export const STORE_OTHER_INCOME_ALL_STORES = "all";

export type StoreOtherIncomeComparison = {
  current: number;
  prior: number;
  difference: number;
  rate: number | null;
};

export type StoreOtherIncomeRow = {
  row_type: "detail" | "category_total" | "grand_total";
  store_code: string;
  store_name: string;
  department_code?: string | null;
  department_name?: string | null;
  subject_code?: string | null;
  category: string;
  fee_name: string;
  months: Record<string, StoreOtherIncomeComparison>;
  total: StoreOtherIncomeComparison;
};

export type StoreOtherIncomeReport = {
  report_name: string;
  financial_year: number;
  prior_year: number;
  end_period: number;
  periods: number[];
  unit: "元";
  selected_store?: string | null;
  scope_description: string;
  summary: StoreOtherIncomeComparison;
  store_rows: StoreOtherIncomeRow[];
  department_rows: StoreOtherIncomeRow[];
  quality: {
    source_row_count: number;
    store_count: number;
    department_count: number;
  };
};

export function buildStoreOtherIncomeParams(filters: {
  financialYear: number;
  endPeriod: number;
  storeId?: string;
}): URLSearchParams {
  const params = new URLSearchParams({
    financial_year: String(filters.financialYear),
    end_period: String(filters.endPeriod),
  });
  if (filters.storeId && filters.storeId !== STORE_OTHER_INCOME_ALL_STORES) {
    params.set("store_id", filters.storeId);
  }
  return params;
}

export function formatIncomeWan(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value / 10_000);
}

export function formatIncomeRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("zh-CN", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function storeOtherIncomeRowClass(rowType: StoreOtherIncomeRow["row_type"]): string {
  if (rowType === "grand_total") return "bg-blue-100 font-semibold";
  if (rowType === "category_total") return "bg-slate-100 font-semibold";
  return "bg-white";
}
