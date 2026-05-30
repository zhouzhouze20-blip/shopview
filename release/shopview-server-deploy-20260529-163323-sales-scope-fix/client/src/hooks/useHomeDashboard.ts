import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { ContractListItem } from "@/hooks/useContracts";
import { buildHomeSalesFinancialMeta, localDateFromToday } from "@/lib/financialMonth";

export type ContractDashboardSummary = {
  active_in_operation: number;
  new_this_month: number;
  expiring_this_month: number;
  as_of_date: string;
  definitions?: Record<string, string>;
};

type StoreSummaryRow = {
  store_id: string;
  effective_sales: number;
  net_profit: number;
  ticket_count: number;
};

function fetchStoresRange(start: string, end: string) {
  const q = new URLSearchParams();
  q.set("start_date", start);
  q.set("end_date", end);
  return apiGet<StoreSummaryRow[]>(`/api/sales/summary/stores?${q.toString()}`);
}

/** 主页驾驶舱：按财务月累计至今日 + 上年同期区间，并行请求门店汇总 */
export function useSalesDashboardOverview(enabled = true) {
  const todayStr = localDateFromToday();
  const meta = useMemo(() => buildHomeSalesFinancialMeta(todayStr), [todayStr]);

  const results = useQueries({
    queries: [
      {
        queryKey: [
          "/api/sales/summary/stores",
          "home-dashboard",
          "fm-current",
          meta.periodStart,
          meta.periodEnd,
        ],
        queryFn: () => fetchStoresRange(meta.periodStart, meta.periodEnd),
        enabled,
        staleTime: 60_000,
      },
      {
        queryKey: [
          "/api/sales/summary/stores",
          "home-dashboard",
          "fm-prior",
          meta.priorPeriodStart,
          meta.priorPeriodEnd,
        ],
        queryFn: () => fetchStoresRange(meta.priorPeriodStart, meta.priorPeriodEnd),
        enabled,
        staleTime: 60_000,
      },
    ],
  });

  const [currentQuery, priorQuery] = results;

  return {
    meta,
    todayStr,
    currentQuery,
    priorQuery,
    isLoading: currentQuery.isLoading || priorQuery.isLoading,
    isError: currentQuery.isError && priorQuery.isError,
    currentError: currentQuery.isError,
    priorError: priorQuery.isError,
  };
}

export function useContractDashboardSummary(enabled = true) {
  return useQuery({
    queryKey: ["/api/contracts/dashboard-summary"],
    queryFn: () => apiGet<ContractDashboardSummary>("/api/contracts/dashboard-summary"),
    enabled,
    staleTime: 60_000,
  });
}

export type ExpiringContractsResponse = {
  items: ContractListItem[];
  count: number;
};

/** 本月即将到期合同明细（与驾驶舱计数口径一致），弹窗打开时再请求 */
export function useExpiringContractsThisMonth(open: boolean) {
  return useQuery({
    queryKey: ["/api/contracts/expiring-this-month"],
    queryFn: () => apiGet<ExpiringContractsResponse>("/api/contracts/expiring-this-month"),
    enabled: open,
    staleTime: 60_000,
  });
}

export function aggregateStoreSummaries(rows: StoreSummaryRow[] | undefined) {
  if (!rows?.length) {
    return { effective_sales: 0, net_profit: 0, ticket_count: 0, store_count: 0 };
  }
  let effective_sales = 0;
  let net_profit = 0;
  let ticket_count = 0;
  for (const r of rows) {
    effective_sales += Number(r.effective_sales) || 0;
    net_profit += Number(r.net_profit) || 0;
    ticket_count += Number(r.ticket_count) || 0;
  }
  return { effective_sales, net_profit, ticket_count, store_count: rows.length };
}
