import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api";

export type MerchantCooperationMode = "LEASE" | "JOINT_OPERATION" | "OTHER";
export type MerchantOpportunityStatus = "TODO" | "NEGOTIATING" | "SIGNED" | "ABANDONED";
export type MerchantPriority = "P0" | "P1" | "P2";

export interface MerchantCalculationInput {
  cooperation_mode: MerchantCooperationMode;
  unit_area?: number | null;
  current_annual_revenue?: number | null;
  monthly_rent?: number | null;
  rent_unit_price?: number | null;
  commission_rate?: number | null;
  guaranteed_amount?: number | null;
  expected_monthly_sales?: number | null;
  manual_monthly_revenue?: number | null;
  decoration_days?: number;
  vacancy_days?: number;
  contract_start_date?: string | null;
  contract_end_date?: string | null;
}

export interface MerchantCalculationResult {
  effective_months: number;
  estimated_monthly_revenue: number;
  estimated_annual_revenue: number;
  estimated_lift_amount: number;
  snapshot: Record<string, unknown>;
}

export interface MerchantOpportunity {
  id: number;
  project_id?: number | null;
  source_type: "REVENUE_MAP" | "MANUAL" | "PROJECT";
  store_id?: string | null;
  floor_id?: number | null;
  unit_id?: number | null;
  unit_code?: string | null;
  unit_area?: number | null;
  current_brand?: string | null;
  current_contract_id?: string | null;
  current_annual_revenue: number;
  target_category?: string | null;
  target_brand?: string | null;
  owner_user_id?: number | null;
  status: MerchantOpportunityStatus;
  expected_sign_date?: string | null;
  priority: MerchantPriority;
  estimated_annual_revenue: number;
  estimated_lift_amount: number;
  remark?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MerchantOpportunityInput {
  project_id?: number | null;
  source_type?: "REVENUE_MAP" | "MANUAL" | "PROJECT";
  store_id?: string | null;
  floor_id?: number | null;
  unit_id?: number | null;
  unit_code?: string | null;
  unit_area?: number | null;
  current_brand?: string | null;
  current_contract_id?: string | null;
  current_annual_revenue?: number;
  target_category?: string | null;
  target_brand?: string | null;
  owner_user_id?: number | null;
  status?: MerchantOpportunityStatus;
  expected_sign_date?: string | null;
  priority?: MerchantPriority;
  remark?: string | null;
  calculation?: MerchantCalculationInput | null;
}

export interface MerchantPlanningProjectInput {
  name: string;
  store_id?: string | null;
  floor_ids?: number[];
  scope_type?: "FLOOR" | "MULTI_FLOOR" | "AREA";
  target_description?: string | null;
  owner_user_id?: number | null;
  opportunity_ids?: number[];
}

export interface MerchantCandidate {
  unit_id: number;
  unit_code?: string | null;
  floor_id?: number | null;
  store_id?: string | null;
  unit_area?: number | null;
  period_revenue?: number | null;
  current_contract_id?: string | null;
  current_brand?: string | null;
  contract_end_date?: string | null;
  candidate_type: "VACANT" | "LOW_EFFICIENCY" | "EXPIRING" | "NORMAL";
}

export interface MerchantOverview {
  by_status: Record<MerchantOpportunityStatus, number>;
  estimated_lift_amount: number;
  opportunity_count: number;
}

export function useMerchantOverview() {
  return useQuery({
    queryKey: ["merchant-planning", "overview"],
    queryFn: () => apiGet<MerchantOverview>("/api/merchant-planning/overview"),
  });
}

export function useMerchantCandidates(params: {
  storeId?: string | null;
  floorId?: number | null;
  candidateType?: string;
}) {
  return useQuery({
    queryKey: ["merchant-planning", "candidates", params],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params.storeId) q.set("store_id", params.storeId);
      if (params.floorId != null) q.set("floor_id", String(params.floorId));
      if (params.candidateType && params.candidateType !== "ALL") q.set("candidate_type", params.candidateType);
      return apiGet<{ items: MerchantCandidate[] }>(`/api/merchant-planning/candidates?${q.toString()}`);
    },
  });
}

export function useMerchantOpportunities(params?: { status?: string; storeId?: string | null; floorId?: number | null }) {
  return useQuery({
    queryKey: ["merchant-planning", "opportunities", params ?? {}],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params?.status && params.status !== "ALL") q.set("status", params.status);
      if (params?.storeId) q.set("store_id", params.storeId);
      if (params?.floorId != null) q.set("floor_id", String(params.floorId));
      return apiGet<MerchantOpportunity[]>(`/api/merchant-planning/opportunities?${q.toString()}`);
    },
  });
}

export function usePreviewMerchantCalculation() {
  return useMutation({
    mutationFn: (input: MerchantCalculationInput) =>
      apiPost<MerchantCalculationResult>("/api/merchant-planning/calculations/preview", input),
  });
}

export function useCreateMerchantOpportunity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: MerchantOpportunityInput) => apiPost<MerchantOpportunity>("/api/merchant-planning/opportunities", input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["merchant-planning"] });
    },
  });
}

export function useUpdateMerchantOpportunity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: MerchantOpportunityInput }) =>
      apiPut<MerchantOpportunity>(`/api/merchant-planning/opportunities/${id}`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["merchant-planning"] });
    },
  });
}

export function useCreateMerchantPlanningProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: MerchantPlanningProjectInput) => apiPost<{ id: number; message: string }>("/api/merchant-planning/projects", input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["merchant-planning"] });
    },
  });
}

export function useCreateMerchantFollowUp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: { content: string; follow_up_type?: string; next_action?: string } }) =>
      apiPost<{ id: number; message: string }>(`/api/merchant-planning/opportunities/${id}/follow-ups`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["merchant-planning"] });
    },
  });
}
