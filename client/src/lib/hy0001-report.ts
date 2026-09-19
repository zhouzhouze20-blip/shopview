export const HY0001_ALL_DEPARTMENTS = "all";

export type Hy0001Store = {
  store_id: number | string;
  store_code: string;
  store_name: string;
};

export type Hy0001Department = {
  store_code: string;
  department_code: string;
  department_name: string;
};

export type Hy0001Level = {
  level_code: string;
  level_label: string;
  current_sales: number;
  prior_sales: number;
  sales_yoy: number | null;
  current_buyers: number;
  prior_buyers: number;
  buyer_yoy: number | null;
};

export type Hy0001Row = {
  store_code: string;
  store_name: string;
  department_code: string | null;
  department_name: string | null;
  group_code: string;
  group_name: string;
  manager_name: string;
  levels: Hy0001Level[];
};

export type Hy0001Response = {
  report_code: "HY0001";
  report_name: string;
  dates: {
    current_start: string;
    current_end: string;
    prior_start: string;
    prior_end: string;
  };
  levels: Array<{ level_code: string; level_label: string }>;
  rows: Hy0001Row[];
  manager_summary: Array<{
    manager_name: string;
    key_brand_count: number;
    current_premium_buyers: number;
    prior_premium_buyers: number;
    premium_buyer_yoy: number | null;
    current_premium_sales: number;
    prior_premium_sales: number;
    premium_sales_yoy: number | null;
  }>;
  quality: {
    key_brand_count: number;
    unassigned_manager_count: number;
    no_current_member_sales_count: number;
  };
};

function dateInputValue(value: Date): string {
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${value.getFullYear()}-${month}-${day}`;
}

export function defaultHy0001DateRange(now = new Date()): { start: string; end: string } {
  const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const end = new Date(now.getFullYear(), now.getMonth(), 0);
  return { start: dateInputValue(start), end: dateInputValue(end) };
}

export function buildHy0001Params(
  startDate: string,
  endDate: string,
  storeCode: string,
  departmentCode = HY0001_ALL_DEPARTMENTS,
): URLSearchParams {
  const params = new URLSearchParams({
    start_date: startDate.trim(),
    end_date: endDate.trim(),
    store_id: storeCode.trim(),
  });
  if (departmentCode && departmentCode !== HY0001_ALL_DEPARTMENTS) {
    params.set("department_id", departmentCode.trim());
  }
  return params;
}

export function hy0001Level(row: Hy0001Row, levelCode: string): Hy0001Level | undefined {
  return row.levels.find((level) => level.level_code === levelCode);
}

export function formatHy0001Money(value: number | null | undefined): string {
  return Number(value ?? 0).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatHy0001Count(value: number | null | undefined): string {
  return Math.trunc(Number(value ?? 0)).toLocaleString("zh-CN");
}

export function formatHy0001Yoy(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

export function hy0001YoyClass(value: number | null | undefined): string {
  if (value == null || value === 0) return "text-slate-500";
  return value > 0 ? "text-red-600" : "text-emerald-600";
}

export function contentDispositionFilename(value: string | null): string | null {
  if (!value) return null;
  const encoded = value.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded).replace(/[\r\n]/g, "");
    } catch {
      // Fall through to the plain filename.
    }
  }
  const plain = value.match(/filename="?([^";]+)"?/i)?.[1]?.trim();
  return plain?.replace(/[\r\n]/g, "") || null;
}
