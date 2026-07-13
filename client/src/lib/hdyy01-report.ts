export const HDYY01_ALL_STORES = "all";
export const HDYY01_ALL_DEPARTMENTS = "all";

export interface Hdyy01Row {
  store_code: string | null;
  store_name: string | null;
  department_code: string | null;
  department_name: string | null;
  group_code: string | null;
  group_name: string | null;
  area: number;
  floor_code: string | null;
  level1_code: string | null;
  level1_name: string | null;
  level2_code: string | null;
  level2_name: string | null;
  grade_label: string | null;
  quantity: number;
  sales_amount: number;
  tax_cost: number;
  profit: number;
  ticket_count: number;
  average_ticket: number | null;
  member_sales: number;
  stored_card_sales: number;
}

export interface Hdyy01Total {
  quantity: number;
  sales_amount: number;
  tax_cost: number;
  profit: number;
  ticket_count: number;
  average_ticket: number | null;
  member_sales: number;
  stored_card_sales: number;
}

export interface Hdyy01Quality {
  unmatched_organization_group_count: number;
  unmatched_organization_amount: number;
  unmatched_hierarchy_group_count: number;
  unmatched_hierarchy_amount: number;
  missing_grade_group_count: number;
  missing_grade_amount: number;
  unmatched_member_ticket_count: number;
}

export interface Hdyy01Response {
  dates: {
    start_date: string;
    end_date: string;
  };
  selected_store: string | null;
  selected_department: string | null;
  rows: Hdyy01Row[];
  total: Hdyy01Total;
  quality: Hdyy01Quality;
  generated_at: string;
}

export interface Hdyy01AuthorizedStore {
  store_id: string | number;
  store_code: string;
  store_name?: string | null;
}

export interface Hdyy01AuthorizedDepartment {
  store_code: string;
  department_code: string;
  department_name: string;
}

export type Hdyy01StoreOption = { value: string; label: string };

export type Hdyy01DepartmentOption = {
  value: string;
  label: string;
  storeCode: string;
};

export type Hdyy01DraftFilters = {
  start: string;
  end: string;
  storeId: string;
  departmentId: string;
};

export function buildHdyy01Params(
  start: string,
  end: string,
  storeId: string,
  departmentId: string = HDYY01_ALL_DEPARTMENTS,
): URLSearchParams {
  const params = new URLSearchParams({ start_date: start, end_date: end });
  const normalizedStore = storeId.trim();
  if (normalizedStore && normalizedStore !== HDYY01_ALL_STORES) {
    params.set("store_id", normalizedStore);
  }
  const normalizedDepartment = departmentId.trim();
  if (normalizedDepartment && normalizedDepartment !== HDYY01_ALL_DEPARTMENTS) {
    params.set("department_id", normalizedDepartment);
  }
  return params;
}

export function changeHdyy01Store<T extends Hdyy01DraftFilters>(draft: T, storeId: string): T {
  return { ...draft, storeId, departmentId: HDYY01_ALL_DEPARTMENTS };
}

function formatNumber(
  value: number | null | undefined,
  options: Intl.NumberFormatOptions,
): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("zh-CN", options);
}

export function formatHdyy01Money(value: number | null | undefined): string {
  return formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatHdyy01Area(value: number | null | undefined): string {
  return formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatHdyy01Quantity(value: number | null | undefined): string {
  return formatNumber(value, { maximumFractionDigits: 4 });
}

export function formatHdyy01Count(value: number | null | undefined): string {
  return formatNumber(value, { maximumFractionDigits: 0 });
}

export function formatHdyy01CodeName(
  code: string | null | undefined,
  name: string | null | undefined,
): string {
  const normalizedCode = code?.trim() || "";
  const normalizedName = name?.trim() || "";
  if (normalizedCode && normalizedName) return `${normalizedName}（${normalizedCode}）`;
  return normalizedName || normalizedCode || "—";
}

export function paginateRows<T>(rows: readonly T[], page: number, pageSize = 50): T[] {
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(totalPages, Math.max(1, Math.trunc(page) || 1));
  return rows.slice((safePage - 1) * pageSize, safePage * pageSize);
}

export function getHdyy01QueryMessage(state: {
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
  if (state.hasData && state.rowCount === 0) return "当前条件下无数据";
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

export function scheduleObjectUrlRevoke(
  url: string,
  revoke: (url: string) => void = URL.revokeObjectURL,
  schedule: (callback: () => void, delay: number) => unknown = setTimeout,
): void {
  schedule(() => revoke(url), 0);
}

export function syncHdyy01DraftFromGlobalStore<T extends Hdyy01DraftFilters>(
  draft: T,
  globalStoreId: string | number | null,
  dirty: boolean,
): T {
  if (dirty) return draft;
  return {
    ...draft,
    storeId: globalStoreId === null ? HDYY01_ALL_STORES : String(globalStoreId),
  };
}

export function normalizeHdyy01StoreOptions(
  permissionRows: readonly Hdyy01AuthorizedStore[],
): Hdyy01StoreOption[] {
  const options = new Map<string, string>();
  permissionRows.forEach((row) => {
    const value = row.store_code.trim();
    if (value) options.set(value, row.store_name?.trim() || value);
  });
  return Array.from(options, ([value, label]) => ({ value, label }));
}
