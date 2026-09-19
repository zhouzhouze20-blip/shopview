import { useQuery } from "@tanstack/react-query";
import { apiGet, apiRequest } from "@/lib/api";

export type RentalReceivableItem = {
  bill_no: string;
  supplier_id: string | null;
  supplier_name: string | null;
  store_code: string | null;
  store_name: string | null;
  department_code: string | null;
  department_name: string | null;
  group_code: string | null;
  group_name: string | null;
  contract_no: string | null;
  settle_from: string | null;
  settle_to: string | null;
  original_amount: number;
  original_receivable_amount: number;
  receivable_amount: number;
  sales_refund_amount: number;
  aging_days: number;
  outstanding_status: "FULL" | "PARTIAL" | "EXCEEDS_ORIGINAL";
};

export type RentalReceivablesResponse = {
  items: RentalReceivableItem[];
  total: number;
  page: number;
  page_size: number;
  summary: {
    bill_count: number;
    receivable_amount: number;
    original_amount: number;
    sales_refund_amount: number;
    partial_count: number;
    anomaly_count: number;
    over_90_amount: number;
  };
  source: { id?: number; name?: string; type?: string };
  source_loaded_at: string;
  queried_at: string;
  scope_note: string;
};

export type RentalReceivableParams = {
  settle_from: string;
  settle_to: string;
  page: number;
  page_size: number;
  mkt?: string;
  department_code?: string;
  group_code?: string;
  group_prefix?: string;
  keyword?: string;
};

function queryString(params: RentalReceivableParams) {
  const q = new URLSearchParams({
    settle_from: params.settle_from,
    settle_to: params.settle_to,
    page: String(params.page),
    page_size: String(params.page_size),
  });
  if (params.mkt?.trim()) q.set("mkt", params.mkt.trim());
  if (params.department_code?.trim()) q.set("department_code", params.department_code.trim());
  if (params.group_code?.trim()) q.set("group_code", params.group_code.trim());
  if (params.group_prefix?.trim()) q.set("group_prefix", params.group_prefix.trim());
  if (params.keyword?.trim()) q.set("keyword", params.keyword.trim());
  return q.toString();
}

function exportQueryString(params: RentalReceivableParams) {
  const q = new URLSearchParams({
    settle_from: params.settle_from,
    settle_to: params.settle_to,
  });
  if (params.mkt?.trim()) q.set("mkt", params.mkt.trim());
  if (params.department_code?.trim()) q.set("department_code", params.department_code.trim());
  if (params.group_prefix?.trim()) q.set("group_prefix", params.group_prefix.trim());
  if (params.keyword?.trim()) q.set("keyword", params.keyword.trim());
  return q.toString();
}

export async function downloadRentalReceivableExpenseDetails(params: RentalReceivableParams) {
  const response = await apiRequest(
    `/api/rental-receivables/export/expense-details?${exportQueryString(params)}`,
  );
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const filename = `租赁应收未收_费用明细_${params.settle_from}_${params.settle_to}.xlsx`;
  try {
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
  return filename;
}

export type RentalReceivableOptions = {
  stores: Array<{ store_code: string; store_name: string }>;
  departments: Array<{ department_code: string; department_name: string; store_code: string | null }>;
};

export type RentalReceivableDetail = {
  bill: {
    bill_no: string;
    supplier_id: string | null;
    supplier_name: string | null;
    store_code: string | null;
    store_name: string | null;
    department_code: string | null;
    department_name: string | null;
    group_code: string | null;
    group_name: string | null;
    contract_no: string | null;
    settle_from: string | null;
    settle_to: string | null;
  };
  items: Array<{
    row_no: number;
    status: string | null;
    item_code: string | null;
    item_name: string;
    period_from: string | null;
    period_to: string | null;
    finance_month: string | null;
    amount: number;
    checked_amount: number;
    paid_amount: number;
    deducted_amount: number;
    balance_amount: number;
    receivable_component: number;
    is_sales_refund: boolean;
    is_receivable_line: boolean;
    adjustment_amount: number;
    sales_reference_amount: number;
    tax_rate: number;
    no_tax_amount: number;
    memo: string | null;
    calculation_source: string | null;
    is_advance: string | null;
    area: number;
    rental_area: number;
  }>;
  totals: {
    original_amount: number;
    checked_amount: number;
    paid_amount: number;
    deducted_amount: number;
    balance_amount: number;
    receivable_amount: number;
    sales_refund_amount: number;
    sales_reference_amount: number;
  };
  detail_count: number;
  nonzero_count: number;
  source_loaded_at: string;
};

export function useRentalReceivableOptions() {
  return useQuery({
    queryKey: ["/api/rental-receivables/options"],
    queryFn: () => apiGet<RentalReceivableOptions>("/api/rental-receivables/options"),
    staleTime: 5 * 60_000,
  });
}

export function useRentalReceivableDetail(billNo: string | null) {
  return useQuery({
    queryKey: ["/api/rental-receivables/detail", billNo],
    queryFn: () => apiGet<RentalReceivableDetail>(`/api/rental-receivables/${encodeURIComponent(billNo || "")}/details`),
    enabled: Boolean(billNo),
    staleTime: 30_000,
  });
}

export function useRentalReceivables(params: RentalReceivableParams, enabled = true) {
  const qs = queryString(params);
  return useQuery({
    queryKey: ["/api/rental-receivables", qs],
    queryFn: () => apiGet<RentalReceivablesResponse>(`/api/rental-receivables?${qs}`),
    enabled,
    staleTime: 30_000,
  });
}
