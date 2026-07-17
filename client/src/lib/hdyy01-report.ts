export const HDYY01_ALL_STORES = "all";
export const HDYY01_ALL_DEPARTMENTS = "all";
export const HDYY01_REPORT_STALE_TIME = 0;

export interface Hdyy01Row {
  store_code: string | null;
  store_name: string;
  department_code: string | null;
  department_name: string;
  group_code: string | null;
  group_name: string;
  area: number;
  floor_code: string | null;
  floor_name: string;
  level1_code: string | null;
  level1_name: string;
  level2_code: string | null;
  level2_name: string;
  grade_label: string;
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
  unmatched_member_ticket_count: number | null;
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

export type Hdyy01QuerySnapshot = {
  filters: Readonly<Hdyy01DraftFilters>;
  queryString: string;
};

function localDateString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function defaultHdyy01DateRange(now: Date = new Date()): Pick<Hdyy01DraftFilters, "start" | "end"> {
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  end.setDate(end.getDate() - 1);
  const start = new Date(end.getFullYear(), end.getMonth(), 1);
  return { start: localDateString(start), end: localDateString(end) };
}

export function resolveHdyy01GlobalStoreCode(
  permissionRows: readonly Hdyy01AuthorizedStore[],
  selectedStoreId: string | number | null,
): string | null {
  if (selectedStoreId === null) return null;
  const storeCode = permissionRows.find(
    (store) => String(store.store_id) === String(selectedStoreId),
  )?.store_code.trim();
  return storeCode || null;
}

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

export function createHdyy01QuerySnapshot(
  draft: Hdyy01DraftFilters,
): Hdyy01QuerySnapshot {
  const filters = { ...draft };
  return {
    filters,
    queryString: buildHdyy01Params(
      filters.start,
      filters.end,
      filters.storeId,
      filters.departmentId,
    ).toString(),
  };
}

export function shouldRefetchHdyy01Query(
  current: Hdyy01QuerySnapshot | null,
  next: Hdyy01QuerySnapshot,
): boolean {
  return current?.queryString === next.queryString;
}

export function changeHdyy01Store(
  draft: Hdyy01DraftFilters,
  storeId: string,
): Hdyy01DraftFilters {
  return { ...draft, storeId, departmentId: HDYY01_ALL_DEPARTMENTS };
}

function formatNumber(
  value: number | null | undefined,
  options: Intl.NumberFormatOptions,
): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const normalizedValue = Object.is(value, -0) ? 0 : value;
  return normalizedValue.toLocaleString("zh-CN", options);
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
  const safePageSize = Number.isFinite(pageSize) && Number.isInteger(pageSize) && pageSize > 0
    ? pageSize
    : 50;
  const totalPages = Math.max(1, Math.ceil(rows.length / safePageSize));
  const safePage = Math.min(totalPages, Math.max(1, Math.trunc(page) || 1));
  return rows.slice((safePage - 1) * safePageSize, safePage * safePageSize);
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
    const normalizedMessage = message.trim();
    const isPermissionError = /^(?:API请求失败:\s*403\b|HTTP\s*403\b)/i.test(normalizedMessage)
      || ["无功能权限", "无该门店数据权限", "无权限", "无权限查看此报表"].includes(
        normalizedMessage,
      );
    return isPermissionError
      ? "无权限查看此报表"
      : "报表加载失败，请稍后重试";
  }
  if (state.hasData && state.rowCount === 0) return "当前条件下无数据";
  return null;
}

function sanitizeContentDispositionFilename(value: string | undefined): string | null {
  const normalized = value?.trim();
  if (!normalized || /[\u0000-\u001f\u007f]/.test(normalized)) return null;
  const filename = normalized.split(/[\\/]/).pop()?.trim();
  if (!filename || filename === "." || filename === "..") return null;
  return filename;
}

export function contentDispositionFilename(header: string | null): string | null {
  if (!header) return null;
  const encoded = /filename\*\s*=\s*UTF-8'[^']*'([^;]+)/i.exec(header)?.[1];
  if (encoded) {
    try {
      const filename = sanitizeContentDispositionFilename(decodeURIComponent(encoded.trim()));
      if (filename) return filename;
    } catch {
      // Fall through to the plain filename when the extended value is malformed.
    }
  }
  const plain = /filename\s*=\s*(?:"([^"]+)"|([^;]+))/i.exec(header);
  return sanitizeContentDispositionFilename(plain?.[1] ?? plain?.[2]);
}

export function scheduleObjectUrlRevoke(
  url: string,
  revoke: (url: string) => void = URL.revokeObjectURL,
  schedule: (callback: () => void, delay: number) => unknown = setTimeout,
): void {
  schedule(() => revoke(url), 0);
}

export function syncHdyy01DraftFromGlobalStore(
  draft: Hdyy01DraftFilters,
  globalStoreCode: string | null,
  dirty: boolean,
): Hdyy01DraftFilters {
  if (dirty) return draft;
  const storeId = globalStoreCode === null ? HDYY01_ALL_STORES : globalStoreCode;
  if (storeId === draft.storeId) return draft;
  return {
    ...draft,
    storeId,
    departmentId: HDYY01_ALL_DEPARTMENTS,
  };
}

export function normalizeHdyy01StoreOptions(
  permissionRows: readonly Hdyy01AuthorizedStore[],
): Hdyy01StoreOption[] {
  const options = new Map<string, string>();
  permissionRows.forEach((row) => {
    const value = row.store_code.trim();
    if (!value) return;
    const label = row.store_name?.trim();
    if (label) {
      options.set(value, label);
    } else if (!options.has(value)) {
      options.set(value, value);
    }
  });
  return Array.from(options, ([value, label]) => ({ value, label }));
}
