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
