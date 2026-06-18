import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";

export type ContractUnitBindingStatus = "ACTIVE" | "INACTIVE" | "HISTORY";

export interface ContractUnitBindingItem {
  id: number;
  shop_unit_id?: number | null;
  unit_code?: string | null;
  floor_id?: number | null;
  store_code?: string | null;
  building_code?: string | null;
  floor_code?: string | null;
  floor_name?: string | null;
  contract_id: string;
  contract_title?: string | null;
  contract_status?: string | null;
  contract_start_date?: string | null;
  contract_end_date?: string | null;
  supplier_code?: string | null;
  supplier_name?: string | null;
  brand_name?: string | null;
  brand_id?: string | null;
  business_type?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_primary: boolean;
  status: ContractUnitBindingStatus;
  remark?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ContractUnitBindingListResponse {
  items: ContractUnitBindingItem[];
  count: number;
  skip: number;
  limit: number;
}

export interface ContractUnitBindingInput {
  shop_unit_id: number;
  contract_id: string;
  business_type?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_primary?: boolean;
  status?: ContractUnitBindingStatus;
  remark?: string | null;
}

export function useContractUnitBindings(params?: {
  keyword?: string;
  contractId?: string;
  unitCode?: string;
  status?: string;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["contract-unit-bindings", params ?? {}],
    queryFn: () => {
      const searchParams = new URLSearchParams();
      const keyword = params?.keyword?.trim();
      const contractId = params?.contractId?.trim();
      const unitCode = params?.unitCode?.trim();
      const status = params?.status?.trim();
      if (keyword) searchParams.set("keyword", keyword);
      if (contractId) searchParams.set("contract_id", contractId);
      if (unitCode) searchParams.set("unit_code", unitCode);
      if (status && status !== "ALL") searchParams.set("status", status);
      searchParams.set("skip", String(params?.skip ?? 0));
      searchParams.set("limit", String(params?.limit ?? 100));
      return apiGet<ContractUnitBindingListResponse>(`/api/contract-unit-bindings/?${searchParams.toString()}`);
    },
  });
}

export function useCreateContractUnitBinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ContractUnitBindingInput) => apiPost<{ message: string; id: number }>("/api/contract-unit-bindings/", input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contract-unit-bindings"] });
      qc.invalidateQueries({ queryKey: ["unit-contracts"] });
    },
  });
}

export function useUpdateContractUnitBinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<ContractUnitBindingInput> }) =>
      apiPut<{ message: string; id: number }>(`/api/contract-unit-bindings/${id}`, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contract-unit-bindings"] });
      qc.invalidateQueries({ queryKey: ["unit-contracts"] });
    },
  });
}

export function useDisableContractUnitBinding() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete<{ message: string; id: number }>(`/api/contract-unit-bindings/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contract-unit-bindings"] });
      qc.invalidateQueries({ queryKey: ["unit-contracts"] });
    },
  });
}
