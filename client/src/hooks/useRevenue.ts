import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api";

export interface RevenueMonthlyItem {
  unit_id: number;
  unit_code: string;
  store_id?: number | null;
  floor_id?: number | null;
  unit_status?: string | null;
  sales_gross_profit_amount: number;
  fee_amount: number;
  extra_amount: number;
  total_amount: number;
  metric_amount: number;
  sales_detail_count: number;
  fee_detail_count: number;
  extra_detail_count: number;
}

export interface RevenueMonthlyResponse {
  revenue_month: string;
  revenue_date?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  metric: "total" | "sales" | "fee" | "extra";
  items: RevenueMonthlyItem[];
  unmatched: {
    item_count: number;
    amount: number;
  };
}

export interface RevenueExtraReceipt {
  id: number;
  store_id?: number | null;
  floor_id?: number | null;
  unit_id?: number | null;
  unit_code?: string | null;
  revenue_date: string;
  revenue_month?: string | null;
  extra_type: string;
  amount: number;
  receipt_date?: string | null;
  voucher_no?: string | null;
  contract_code?: string | null;
  supplier_code?: string | null;
  supplier_name?: string | null;
  source_group_code?: string | null;
  source_group_name?: string | null;
  remark?: string | null;
  attachment_url?: string | null;
  status: "DRAFT" | "CONFIRMED" | "VOID";
  created_at?: string | null;
  confirmed_at?: string | null;
  voided_at?: string | null;
}

export interface RevenueUnitDetail {
  unit: {
    id: number;
    floor_id: number;
    unit_code: string;
    status: string;
  };
  daily_summary: Array<{
    revenue_date: string;
    revenue_month: string;
    sales_gross_profit_amount: number;
    fee_amount: number;
    extra_amount: number;
    total_amount: number;
    sales_detail_count: number;
    fee_detail_count: number;
    extra_detail_count: number;
  }>;
  sales_details: Array<Record<string, any>>;
  fee_details: Array<Record<string, any>>;
  extra_receipts: RevenueExtraReceipt[];
}

export interface CreateRevenueExtraReceiptInput {
  unit_id?: number | null;
  unit_code?: string;
  store_id?: number | null;
  floor_id?: number | null;
  revenue_date: string;
  extra_type: string;
  amount: number;
  receipt_date?: string | null;
  voucher_no?: string;
  supplier_name?: string;
  remark?: string;
}

export function useRevenueMonthly(params: {
  revenueDate?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  revenueMonth?: string | null;
  storeId?: number | null;
  floorId?: number | null;
  metric?: "total" | "sales" | "fee" | "extra";
}) {
  return useQuery({
    queryKey: [
      "revenue-monthly",
      params.startDate && params.endDate
        ? `${params.startDate}:${params.endDate}`
        : params.revenueDate ?? params.revenueMonth ?? "",
      params.storeId ?? "all",
      params.floorId ?? "all",
      params.metric ?? "total",
    ],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params.startDate && params.endDate) {
        q.set("start_date", params.startDate);
        q.set("end_date", params.endDate);
      } else if (params.revenueDate) q.set("revenue_date", params.revenueDate);
      else if (params.revenueMonth) q.set("revenue_month", params.revenueMonth);
      q.set("metric", params.metric ?? "total");
      if (params.storeId != null) q.set("store_id", String(params.storeId));
      if (params.floorId != null) q.set("floor_id", String(params.floorId));
      return apiGet<RevenueMonthlyResponse>(`/api/revenue-map/monthly?${q.toString()}`);
    },
    staleTime: 0,
    refetchOnMount: "always",
  });
}

export function useRevenueUnitDetail(params: {
  unitId?: number | null;
  revenueDate?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  revenueMonth?: string | null;
}) {
  return useQuery({
    queryKey: [
      "revenue-unit-detail",
      params.unitId ?? "none",
      params.startDate && params.endDate
        ? `${params.startDate}:${params.endDate}`
        : params.revenueDate ?? params.revenueMonth ?? "",
    ],
    enabled: Boolean(params.unitId && ((params.startDate && params.endDate) || params.revenueDate || params.revenueMonth)),
    queryFn: () => {
      const q = new URLSearchParams();
      if (params.startDate && params.endDate) {
        q.set("start_date", params.startDate);
        q.set("end_date", params.endDate);
      } else if (params.revenueDate) {
        q.set("start_date", params.revenueDate);
        q.set("end_date", params.revenueDate);
      } else if (params.revenueMonth) {
        q.set("revenue_month", params.revenueMonth);
      }
      return apiGet<RevenueUnitDetail>(`/api/revenue-map/units/${params.unitId}/detail?${q.toString()}`);
    },
    staleTime: 0,
    refetchOnMount: "always",
  });
}

export function useRevenueExtraReceipts(params: {
  revenueDate?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  revenueMonth?: string | null;
  storeId?: number | null;
  floorId?: number | null;
}) {
  return useQuery({
    queryKey: [
      "revenue-extra-receipts",
      params.startDate && params.endDate
        ? `${params.startDate}:${params.endDate}`
        : params.revenueDate ?? params.revenueMonth ?? "",
      params.storeId ?? "all",
      params.floorId ?? "all",
    ],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params.startDate && params.endDate) {
        q.set("start_date", params.startDate);
        q.set("end_date", params.endDate);
      } else if (params.revenueDate) q.set("revenue_date", params.revenueDate);
      else if (params.revenueMonth) q.set("revenue_month", params.revenueMonth);
      if (params.storeId != null) q.set("store_id", String(params.storeId));
      if (params.floorId != null) q.set("floor_id", String(params.floorId));
      return apiGet<RevenueExtraReceipt[]>(`/api/revenue-map/extra-receipts?${q.toString()}`);
    },
    staleTime: 0,
    refetchOnMount: "always",
  });
}

export function useCreateRevenueExtraReceipt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateRevenueExtraReceiptInput) =>
      apiPost<RevenueExtraReceipt>("/api/revenue-map/extra-receipts", input),
    onSuccess: async (_, input) => {
      const month = input.revenue_date.slice(0, 7);
      await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts", input.revenue_date] });
      await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts", month] });
      await qc.invalidateQueries({ queryKey: ["revenue-monthly", input.revenue_date] });
      await qc.invalidateQueries({ queryKey: ["revenue-monthly", month] });
      await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts"] });
      await qc.invalidateQueries({ queryKey: ["revenue-monthly"] });
    },
  });
}

export function useConfirmRevenueExtraReceipt(revenueMonth: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost<RevenueExtraReceipt>(`/api/revenue-map/extra-receipts/${id}/confirm`),
    onSuccess: async (data) => {
      const revenueDate = data.revenue_date?.slice(0, 10);
      if (revenueDate) {
        await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts", revenueDate] });
        await qc.invalidateQueries({ queryKey: ["revenue-monthly", revenueDate] });
      }
      await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts", revenueMonth] });
      await qc.invalidateQueries({ queryKey: ["revenue-monthly", revenueMonth] });
      await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts"] });
      await qc.invalidateQueries({ queryKey: ["revenue-monthly"] });
    },
  });
}

export function useVoidRevenueExtraReceipt(revenueMonth: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost<RevenueExtraReceipt>(`/api/revenue-map/extra-receipts/${id}/void`),
    onSuccess: async (data) => {
      const revenueDate = data.revenue_date?.slice(0, 10);
      if (revenueDate) {
        await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts", revenueDate] });
        await qc.invalidateQueries({ queryKey: ["revenue-monthly", revenueDate] });
      }
      await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts", revenueMonth] });
      await qc.invalidateQueries({ queryKey: ["revenue-monthly", revenueMonth] });
      await qc.invalidateQueries({ queryKey: ["revenue-extra-receipts"] });
      await qc.invalidateQueries({ queryKey: ["revenue-monthly"] });
    },
  });
}

export function useRecalculateRevenue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { start_date: string; end_date: string }) =>
      apiPost<{ message: string; summary_rows: number }>("/api/revenue-map/recalculate", input),
    onSuccess: async (_, input) => {
      if (input.start_date === input.end_date) {
        await qc.invalidateQueries({ queryKey: ["revenue-monthly", input.start_date] });
      }
      await qc.invalidateQueries({ queryKey: ["revenue-monthly", input.start_date.slice(0, 7)] });
      await qc.invalidateQueries({ queryKey: ["revenue-monthly"] });
    },
  });
}
