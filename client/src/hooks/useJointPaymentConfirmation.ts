import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export type JointPaymentSummary = {
  total_generated_count?: number;
  total_generated_supplier_count?: number;
  total_generated_amount?: number;
  supplier_confirmation_available?: boolean;
  supplier_confirmed_count?: number | null;
  supplier_confirmed_supplier_count?: number | null;
  supplier_confirmed_amount?: number | null;
  supplier_unreported_count?: number | null;
  supplier_unreported_supplier_count?: number | null;
  supplier_unreported_amount?: number | null;
  generated_count: number;
  generated_supplier_count: number;
  generated_amount: number;
  audited_count: number;
  audited_supplier_count: number;
  audited_amount: number;
  current_financial_month_audited_amount: number;
  current_financial_month_start: string | null;
  current_financial_month_end: string | null;
  latest_status_date: string | null;
};

export type JointPaymentItem = {
  payment_bill_no: string;
  status: "M" | "Y" | string;
  status_label: string;
  supplier_confirmed?: boolean | null;
  market_code: string | null;
  supplier_code: string | null;
  supplier_name: string | null;
  payment_amount: number;
  detail_row_count: number;
  settlement_count: number;
  department_count: number;
  department_codes: string | null;
  department_names: string | null;
  group_count: number;
  payment_date: string | null;
  inputor: string | null;
  inputdate: string | null;
  auditor: string | null;
  auditdate: string | null;
  status_date: string | null;
};

export type JointPaymentListResponse = {
  summary: JointPaymentSummary;
  items: JointPaymentItem[];
  total: number;
  page: number;
  page_size: number;
};

export type JointPaymentDetailResponse = {
  head: JointPaymentItem & {
    memo?: string | null;
    sales_revenue?: number;
    invoiced_amount?: number;
    fee_amount?: number;
    ticket_reduction_amount?: number;
    expense_amount?: number;
    ticket_reduction_detail_amount?: number;
    expense_detail_amount?: number;
    ticket_reduction_detail_matches?: boolean;
    expense_detail_matches?: boolean;
  };
  lines: Array<Record<string, unknown>>;
  charges: Array<Record<string, unknown>>;
};

export type JointPaymentParams = {
  page: number;
  page_size: number;
  payment_status?: string;
  date_from?: string;
  date_to?: string;
  market?: string;
  department_code?: string;
  group_prefix?: string;
  keyword?: string;
};

export type JointPaymentDepartmentOption = {
  department_code: string;
  department_name: string;
};

function queryString(params: JointPaymentParams) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || String(value).trim() === "") return;
    query.set(key, String(value).trim());
  });
  return query.toString();
}

export function useJointPaymentConfirmation(params: JointPaymentParams) {
  const query = queryString(params);
  return useQuery({
    queryKey: ["/api/erp-settlements/joint-payment-confirmation", query],
    queryFn: () =>
      apiGet<JointPaymentListResponse>(`/api/erp-settlements/joint-payment-confirmation?${query}`),
    staleTime: 30_000,
  });
}

export function useJointPaymentConfirmationDetail(paymentBillNo: string | null) {
  return useQuery({
    queryKey: ["/api/erp-settlements/joint-payment-confirmation/detail", paymentBillNo],
    queryFn: () =>
      apiGet<JointPaymentDetailResponse>(
        `/api/erp-settlements/joint-payment-confirmation/${encodeURIComponent(paymentBillNo as string)}`,
      ),
    enabled: Boolean(paymentBillNo),
    staleTime: 60_000,
  });
}

export function useJointPaymentDepartmentOptions() {
  return useQuery({
    queryKey: ["/api/erp-settlements/joint-payment-confirmation/options"],
    queryFn: () =>
      apiGet<{ departments: JointPaymentDepartmentOption[] }>(
        "/api/erp-settlements/joint-payment-confirmation/options",
      ),
    staleTime: 5 * 60_000,
  });
}
