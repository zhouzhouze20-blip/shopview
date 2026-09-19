import type { QueryClient } from "@tanstack/react-query";

/** 日期提交后页面回到门店层；旧层级/旧日期只失效，避免发出即将离开页面的请求。 */
export function refreshMobileSalesQueries(
  client: QueryClient,
  { level, datesChanged }: { level: string; datesChanged: boolean },
) {
  return Promise.all([
    client.invalidateQueries({
      predicate: ({ queryKey }) =>
        typeof queryKey[0] === "string" &&
        queryKey[0].startsWith("/api/sales/") &&
        queryKey[1] === "mobile",
      refetchType: level === "stores" && !datesChanged ? "active" : "none",
    }),
    client.invalidateQueries({
      queryKey: ["mobile-sales-financial-month"],
      // 月累计与筛选日期独立；停留门店层时也需要立即刷新。
      refetchType: level === "stores" ? "active" : "none",
    }),
  ]);
}
