export const DAILY_FOLLOWUP_ALL_STORES = "all";
export const DAILY_FOLLOWUP_ALL_DEPARTMENTS = "all";

export type DailyFollowupDimension = "departments" | "groups" | "special_sales";

export interface DailyFollowupMetric {
  sales_current: number;
  sales_prior: number;
  sales_yoy: number | null;
  profit_current: number;
  profit_prior: number;
  profit_yoy: number | null;
  margin_current: number | null;
  margin_prior: number | null;
  margin_change: number | null;
}

export interface DailyFollowupDay extends DailyFollowupMetric {
  date: string;
  prior_date: string;
}

export interface DailyFollowupRow {
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
  daily: DailyFollowupDay[];
  totals: DailyFollowupMetric;
  ytd_totals?: DailyFollowupMetric;
}

export interface DailyFollowupResponse {
  financial_month: string;
  dates: {
    start_date: string;
    end_date: string;
    prior_start_date: string;
    prior_end_date: string;
  };
  cumulative_dates?: {
    start_date: string;
    end_date: string;
    prior_start_date: string;
    prior_end_date: string;
  };
  dimension: DailyFollowupDimension;
  selected_store: string | null;
  selected_department: string | null;
  scope_description: string;
  days: Array<{ date: string; prior_date: string; label: string }>;
  rows: DailyFollowupRow[];
  daily_totals: DailyFollowupDay[];
  totals: DailyFollowupMetric;
  ytd_totals?: DailyFollowupMetric;
  ytd_dates?: {
    start_date: string;
    end_date: string;
    prior_start_date: string;
    prior_end_date: string;
  };
  generated_at: string;
}

function monthValue(year: number, month: number): string {
  return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}`;
}

export function financialMonthForDate(value: Date): string {
  const year = value.getFullYear();
  const month = value.getMonth() + 1;
  if (value.getDate() <= 28) return monthValue(year, month);
  return month === 12 ? monthValue(year + 1, 1) : monthValue(year, month + 1);
}

export function financialMonthRange(financialMonth: string): {
  start: string;
  end: string;
} {
  const match = /^(\d{4})-(\d{2})$/.exec(financialMonth);
  if (!match) throw new Error(`Invalid financial month: ${financialMonth}`);
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (year < 2 || month < 1 || month > 12) {
    throw new Error(`Invalid financial month: ${financialMonth}`);
  }
  const previousYear = month === 1 ? year - 1 : year;
  const previousMonth = month === 1 ? 12 : month - 1;
  const previousMonthLastDay = new Date(previousYear, previousMonth, 0).getDate();
  return {
    start: previousMonthLastDay >= 29
      ? `${monthValue(previousYear, previousMonth)}-29`
      : `${financialMonth}-01`,
    end: `${financialMonth}-28`,
  };
}

export function buildDailyFollowupParams(input: {
  financialMonth: string;
  dimension: DailyFollowupDimension;
  storeId?: string | null;
  departmentId?: string | null;
}): URLSearchParams {
  const match = /^(\d{4})-(\d{2})$/.exec(input.financialMonth);
  if (!match) throw new Error(`Invalid financial month: ${input.financialMonth}`);
  const params = new URLSearchParams({
    financial_year: String(Number(match[1])),
    financial_month: String(Number(match[2])),
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

export function formatDailyMoneyWan(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return (value / 10_000).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatDailyPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toLocaleString("zh-CN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}%`;
}

export function formatDailyPercentagePointChange(
  value: number | null | undefined,
): string {
  if (value === null || value === undefined) return "—";
  const percentagePoints = value * 100;
  const sign = percentagePoints > 0 ? "+" : "";
  return `${sign}${percentagePoints.toLocaleString("zh-CN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}个百分点`;
}

export function formatDailyDate(value: string): string {
  const match = /^\d{4}-(\d{2})-(\d{2})$/.exec(value);
  return match ? `${match[1]}-${match[2]}` : value;
}

export function financialMonthLabel(financialMonth: string): string {
  const range = financialMonthRange(financialMonth);
  const [year, month] = financialMonth.split("-");
  return `${year}年${Number(month)}月财务月（${range.start.slice(5)}—${range.end.slice(5)}）`;
}
