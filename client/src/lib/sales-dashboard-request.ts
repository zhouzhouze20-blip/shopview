export const SALES_DASHBOARD_TIMEOUT_MS = 30_000;
// Database long-range work is capped at 90s and the gateway at 100s.
// The browser waits a little longer so a gateway response is surfaced instead of a client abort.
export const SALES_DASHBOARD_LONG_RANGE_TIMEOUT_MS = 105_000;

export class SalesDashboardTimeoutError extends Error {
  constructor(message = "销售看板数据请求超时") {
    super(message);
    this.name = "SalesDashboardTimeoutError";
  }
}

export function isSalesDashboardTimeoutError(error: unknown): boolean {
  if (error instanceof SalesDashboardTimeoutError) return true;
  if (!(error instanceof Error)) return false;
  return error.name === "AbortError" || /(?:^|\D)504(?:\D|$)|timeout|timed out|超时/i.test(error.message);
}

export type SalesDashboardDateRanges = {
  currentStartDate: string;
  currentEndDate: string;
  priorStartDate: string;
  priorEndDate: string;
};

export function validateSalesDashboardDateRanges(ranges: SalesDashboardDateRanges): string | null {
  const { currentStartDate, currentEndDate, priorStartDate, priorEndDate } = ranges;
  if (![currentStartDate, currentEndDate, priorStartDate, priorEndDate].every((value) => value.trim())) {
    return "请完整选择本期和同期日期。";
  }
  if (currentStartDate > currentEndDate) return "本期开始日期不能晚于结束日期。";
  if (priorStartDate > priorEndDate) return "同期开始日期不能晚于结束日期。";
  return null;
}

export function salesDashboardRangeDays(startDate: string, endDate: string): number {
  if (!startDate || !endDate || startDate > endDate) return 0;
  const start = Date.parse(`${startDate}T00:00:00Z`);
  const end = Date.parse(`${endDate}T00:00:00Z`);
  if (!Number.isFinite(start) || !Number.isFinite(end)) return 0;
  return Math.floor((end - start) / 86_400_000) + 1;
}

export function salesDashboardRequestTimeoutMs(endpoint: string): number {
  try {
    const url = new URL(endpoint, "http://shopview.local");
    const startDate = url.searchParams.get("start_date") ?? "";
    const endDate = url.searchParams.get("end_date") ?? "";
    const rangeDays = salesDashboardRangeDays(startDate, endDate);
    if (
      url.pathname.startsWith("/api/sales/summary/") &&
      rangeDays > 0 &&
      startDate.slice(0, 7) !== endDate.slice(0, 7)
    ) {
      return SALES_DASHBOARD_LONG_RANGE_TIMEOUT_MS;
    }
  } catch {
    // Malformed/opaque endpoints retain the conservative default timeout.
  }
  return SALES_DASHBOARD_TIMEOUT_MS;
}

type SalesDashboardRequester = <T>(endpoint: string, options?: RequestInit) => Promise<T>;

export async function getSalesDashboardData<T>(
  endpoint: string,
  request: SalesDashboardRequester,
  options: {
    timeoutMs?: number;
  } = {},
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? salesDashboardRequestTimeoutMs(endpoint);
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await request<T>(endpoint, { signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted || isSalesDashboardTimeoutError(error)) {
      throw new SalesDashboardTimeoutError(`销售看板数据请求超过 ${Math.round(timeoutMs / 1000)} 秒`);
    }
    throw error;
  } finally {
    globalThis.clearTimeout(timeoutId);
  }
}
