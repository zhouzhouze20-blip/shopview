export const SALES_DASHBOARD_TIMEOUT_MS = 30_000;

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

type SalesDashboardRequester = <T>(endpoint: string, options?: RequestInit) => Promise<T>;

export async function getSalesDashboardData<T>(
  endpoint: string,
  request: SalesDashboardRequester,
  options: {
    timeoutMs?: number;
  } = {},
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? SALES_DASHBOARD_TIMEOUT_MS;
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
