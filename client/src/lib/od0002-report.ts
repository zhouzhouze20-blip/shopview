export const OD0002_ALL_STORES = "all";
export const OD0002_ALL_DEPARTMENTS = "all";

export type Od0002DimensionKey =
  | "stores"
  | "departments"
  | "department_categories"
  | "areas"
  | "categories"
  | "groups"
  | "special_sales"
  | "floors";

export interface Od0002Metric {
  ticket_count_current: number;
  ticket_count_prior: number;
  ticket_count_yoy: number | null;
  average_ticket_current: number | null;
  average_ticket_prior: number | null;
  average_ticket_yoy: number | null;
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
  department_code?: string | null;
  department_name?: string | null;
  area_code?: string | null;
  area_name?: string | null;
  category_code?: string | null;
  category_name?: string | null;
  brand_code?: string | null;
  brand_name?: string | null;
  row_type?: Od0002HierarchyRowType;
  metrics: Od0002Metric;
  total: Od0002Metric;
}

export type Od0002HierarchyRowType = "category" | "area_subtotal" | "department_subtotal";

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
  { key: "department_categories", label: "部门（含品类）" },
  { key: "areas", label: "区域" },
  { key: "categories", label: "品类" },
  { key: "groups", label: "柜组" },
  { key: "special_sales", label: "特卖" },
  { key: "floors", label: "楼层" },
];

export const OD0002_HIERARCHY_COLUMNS = ["store", "department", "area", "category"] as const;
export const OD0002_METRIC_GROUP_LABELS = ["销售收入", "毛利", "毛利率", "来客数", "客单"] as const;

export function isOd0002DepartmentCategoryTab(tab: Od0002DimensionKey): boolean {
  return tab === "department_categories";
}

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
  if (year <= 1 || month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month)) {
    throw new Error(`Invalid ISO date: ${iso}`);
  }

  const previousYear = year - 1;
  const previousDay = Math.min(day, daysInMonth(previousYear, month));
  return `${String(previousYear).padStart(4, "0")}-${match[2]}-${String(previousDay).padStart(2, "0")}`;
}

export function buildOd0002Params(
  start: string,
  end: string,
  storeId: string,
  departmentId: string = OD0002_ALL_DEPARTMENTS,
  priorStart?: string,
  priorEnd?: string,
): URLSearchParams {
  const params = new URLSearchParams({ start_date: start, end_date: end });
  if (priorStart?.trim()) params.set("prior_start_date", priorStart.trim());
  if (priorEnd?.trim()) params.set("prior_end_date", priorEnd.trim());
  const normalizedStore = storeId.trim();
  if (normalizedStore && normalizedStore !== OD0002_ALL_STORES) {
    params.set("store_id", normalizedStore);
  }
  const normalizedDepartment = departmentId.trim();
  if (normalizedDepartment && normalizedDepartment !== OD0002_ALL_DEPARTMENTS) {
    params.set("department_id", normalizedDepartment);
  }
  return params;
}

export type Od0002PeriodFilters = {
  start: string;
  end: string;
  priorStart: string;
  priorEnd: string;
};

export function changeOd0002CurrentDate<T extends Od0002PeriodFilters>(
  draft: T,
  field: "start" | "end",
  value: string,
): T {
  if (field === "start") {
    return {
      ...draft,
      start: value,
      priorStart: value ? previousYearDate(value) : "",
    };
  }
  return {
    ...draft,
    end: value,
    priorEnd: value ? previousYearDate(value) : "",
  };
}

export type Od0002DepartmentDraft = Od0002DraftFilters & { departmentId: string };

export function changeOd0002Store<T extends Od0002DepartmentDraft>(draft: T, storeId: string): T {
  return { ...draft, storeId, departmentId: OD0002_ALL_DEPARTMENTS };
}

export type Od0002VisibleColumn = "store" | "dimension" | "sales" | "profit" | "margin";

export function formatMoneyWan(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return (value / 10_000).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return Math.round(value).toLocaleString("zh-CN");
}

export function formatMoneyYuan(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}%`;
}

export function visibleOd0002Columns(
  tab: Od0002DimensionKey,
  storeId: string,
): Od0002VisibleColumn[] {
  return [
    ...(tab !== "stores" && storeId === OD0002_ALL_STORES ? (["store"] as const) : []),
    "dimension",
    "sales",
    "profit",
    "margin",
  ];
}

export function paginateRows<T>(rows: readonly T[], page: number, pageSize = 50): T[] {
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(totalPages, Math.max(1, Math.trunc(page) || 1));
  return rows.slice((safePage - 1) * pageSize, safePage * pageSize);
}

export function getOd0002QueryMessage(state: {
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

export function contentDispositionFilename(header: string | null): string | null {
  if (!header) return null;
  const encoded = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(header)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded.trim()).split(/[\\/]/).pop() || null;
    } catch {
      return null;
    }
  }
  const plain = /filename\s*=\s*(?:"([^"]+)"|([^;]+))/i.exec(header);
  const filename = (plain?.[1] ?? plain?.[2])?.trim();
  return filename?.split(/[\\/]/).pop() || null;
}

export type Od0002DraftFilters = { start: string; end: string; storeId: string };

export function syncOd0002DraftFromGlobalStore<T extends Od0002DraftFilters>(
  draft: T,
  globalStoreId: string | number | null,
  dirty: boolean,
): T {
  if (dirty) return draft;
  return {
    ...draft,
    storeId: globalStoreId === null ? OD0002_ALL_STORES : String(globalStoreId),
  };
}

export type Od0002StoreOption = { value: string; label: string };

export function normalizeOd0002StoreOptions(
  permissionRows: ReadonlyArray<{ store_id: string | number; store_code: string; store_name?: string | null }>,
  scopedReportRows: ReadonlyArray<{ store_code: string | null; store_name: string | null }> = [],
): Od0002StoreOption[] {
  const options = new Map<string, string>();
  permissionRows.forEach((row) => {
    const value = row.store_code.trim();
    if (value) options.set(value, row.store_name?.trim() || value);
  });
  scopedReportRows.forEach((row) => {
    const value = row.store_code?.trim();
    if (value && !options.has(value)) options.set(value, row.store_name?.trim() || value);
  });
  return Array.from(options, ([value, label]) => ({ value, label }));
}

export function scheduleObjectUrlRevoke(
  url: string,
  revoke: (url: string) => void = URL.revokeObjectURL,
  schedule: (callback: () => void, delay: number) => unknown = setTimeout,
): void {
  schedule(() => revoke(url), 0);
}
