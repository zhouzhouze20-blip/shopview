import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";

export type BusinessUnitStatus = "ACTIVE" | "VACANT" | "FITOUT" | "INACTIVE";
export type BusinessUnitContractMode = "EXCLUSIVE" | "SHARED";

export interface BusinessUnitItem {
  id: number;
  floor_id: number;
  unit_code: string;
  status: BusinessUnitStatus;
  contract_mode: BusinessUnitContractMode;
  manual_area?: number | null;
  parent_unit_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CreateBusinessUnitInput {
  floor_id: number;
  unit_code: string;
  status?: BusinessUnitStatus;
  contract_mode?: BusinessUnitContractMode;
  manual_area?: number | null;
  parent_unit_id?: number | null;
}

export interface UpdateBusinessUnitInput {
  unit_code?: string;
  status?: BusinessUnitStatus;
  contract_mode?: BusinessUnitContractMode;
  manual_area?: number | null;
  parent_unit_id?: number | null;
}

export function useBusinessUnits(params?: { storeId?: number | null; floorId?: number; status?: string; keyword?: string }) {
  return useQuery({
    queryKey: [
      "business-units",
      params?.storeId ?? "all",
      params?.floorId ?? "all",
      params?.status ?? "all",
      params?.keyword ?? "",
    ],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params?.storeId != null) q.set("store_id", String(params.storeId));
      if (params?.floorId != null) q.set("floor_id", String(params.floorId));
      if (params?.status) q.set("status", params.status);
      if (params?.keyword) q.set("keyword", params.keyword);
      return apiGet<BusinessUnitItem[]>(`/api/business-units/?${q.toString()}`);
    },
  });
}

export function useCreateBusinessUnit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateBusinessUnitInput) => apiPost<BusinessUnitItem>("/api/business-units/", input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["business-units"] });
    },
  });
}

export function useUpdateBusinessUnit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateBusinessUnitInput }) =>
      apiPut<BusinessUnitItem>(`/api/business-units/${id}`, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["business-units"] });
    },
  });
}

export function useDeleteBusinessUnit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiDelete<{
        message: string;
        id: number;
        deleted_geo_elements?: number;
        detached_bindings?: number;
      }>(`/api/business-units/${id}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["business-units"] });
      await qc.invalidateQueries({ queryKey: ["geo-elements"] });
      await qc.refetchQueries({ queryKey: ["business-units"], type: "active" });
      await qc.refetchQueries({ queryKey: ["geo-elements"], type: "active" });
    },
  });
}
