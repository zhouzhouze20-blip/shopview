import {
  DAILY_FOLLOWUP_ALL_DEPARTMENTS,
  DAILY_FOLLOWUP_ALL_STORES,
  type DailyFollowupDimension,
  type DailyFollowupMetric,
} from "./daily-followup-report.ts";

export type MonthlyFollowupDimension = DailyFollowupDimension;
export type MonthlyFollowupMetric = DailyFollowupMetric;

export interface MonthlyFollowupMonth extends MonthlyFollowupMetric {
  financial_month: string;
  label: string;
}

export interface MonthlyFollowupRow {
  store_code: string | null;
  store_name: string | null;
  department_code: string | null;
  department_name: string | null;
  area_name?: string | null;
  category_name?: string | null;
  floor_code?: string | null;
  operation_method?: string | null;
  is_key_brand?: boolean;
  manager_name?: string | null;
  dimension_code: string | null;
  dimension_name: string | null;
  brand_code?: string | null;
  brand_name?: string | null;
  monthly: MonthlyFollowupMonth[];
  totals: MonthlyFollowupMetric;
}

export interface MonthlyFollowupResponse {
  financial_year: number;
  dates: {
    start_date: string;
    end_date: string;
    prior_start_date: string;
    prior_end_date: string;
  };
  dimension: MonthlyFollowupDimension;
  selected_store: string | null;
  selected_department: string | null;
  scope_description: string;
  months: Array<{
    financial_month: string;
    label: string;
    start_date: string;
    end_date: string;
    prior_start_date: string;
    prior_end_date: string;
    comparison_end: string | null;
    prior_comparison_end: string | null;
  }>;
  rows: MonthlyFollowupRow[];
  monthly_totals: MonthlyFollowupMonth[];
  totals: MonthlyFollowupMetric;
  generated_at: string;
}

export function currentFinancialYear(value: Date): number {
  return value.getFullYear();
}

export function buildMonthlyFollowupParams(input: {
  financialYear: number;
  dimension: MonthlyFollowupDimension;
  storeId?: string | null;
  departmentId?: string | null;
}): URLSearchParams {
  if (!Number.isInteger(input.financialYear) || input.financialYear < 2000 || input.financialYear > 2100) {
    throw new Error(`Invalid financial year: ${input.financialYear}`);
  }
  const params = new URLSearchParams({
    financial_year: String(input.financialYear),
    dimension: input.dimension,
  });
  const storeId = input.storeId?.trim();
  if (storeId && storeId !== DAILY_FOLLOWUP_ALL_STORES) {
    params.set("store_id", storeId);
  }
  const departmentId = input.departmentId?.trim();
  if (departmentId && departmentId !== DAILY_FOLLOWUP_ALL_DEPARTMENTS) {
    params.set("department_id", departmentId);
  }
  return params;
}
