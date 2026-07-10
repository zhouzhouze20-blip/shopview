export const OD0002_ALL_STORES = "all";

export type Od0002DimensionKey =
  | "stores"
  | "departments"
  | "areas"
  | "categories"
  | "groups"
  | "floors";

export interface Od0002Metric {
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

export interface Od0002Row {
  store_code: string | null;
  store_name: string | null;
  dimension_code: string | null;
  dimension_name: string | null;
  metrics: Od0002Metric;
}

export interface Od0002Quality {
  unmatched_area_category_group_count: number;
  unmatched_floor_group_count: number;
  unmatched_area_category_sales_current: number;
  unmatched_floor_sales_current: number;
}

export interface Od0002Response {
  dates: {
    start_date: string;
    end_date: string;
    prior_start_date: string;
    prior_end_date: string;
  };
  selected_store: string | null;
  dimensions: Record<Od0002DimensionKey, Od0002Row[]>;
  totals: Record<Od0002DimensionKey, Od0002Metric>;
  quality: Od0002Quality;
  generated_at: string;
}

export const OD0002_TABS: ReadonlyArray<{
  key: Od0002DimensionKey;
  label: string;
}> = [
  { key: "stores", label: "分店" },
  { key: "departments", label: "部门" },
  { key: "areas", label: "区域" },
  { key: "categories", label: "品类" },
  { key: "groups", label: "柜组" },
  { key: "floors", label: "楼层" },
];

function isLeapYear(year: number): boolean {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function daysInMonth(year: number, month: number): number {
  if (month === 2) return isLeapYear(year) ? 29 : 28;
  return [4, 6, 9, 11].includes(month) ? 30 : 31;
}

export function previousYearDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match) throw new Error(`Invalid ISO date: ${iso}`);

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month)) {
    throw new Error(`Invalid ISO date: ${iso}`);
  }

  const previousYear = year - 1;
  if (previousYear < 0) throw new Error(`Invalid ISO date: ${iso}`);
  const previousDay = Math.min(day, daysInMonth(previousYear, month));
  return `${String(previousYear).padStart(4, "0")}-${match[2]}-${String(previousDay).padStart(2, "0")}`;
}

export function buildOd0002Params(
  start: string,
  end: string,
  storeId: string,
): URLSearchParams {
  const params = new URLSearchParams({ start_date: start, end_date: end });
  const normalizedStore = storeId.trim();
  if (normalizedStore && normalizedStore !== OD0002_ALL_STORES) {
    params.set("store_id", normalizedStore);
  }
  return params;
}
