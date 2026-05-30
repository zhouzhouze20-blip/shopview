import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";

export interface SupplierItem {
  sbid: string;
  sbcname: string;
  sbaddr?: string | null;
  sbstatus?: string | null;
  sbflag?: string | null;
  sbcatcode?: string | null;
  sbregcode?: string | null;
  sbfrdb?: string | null;
  sbbank?: string | null;
  sbaccntno?: string | null;
  sbtaxno?: string | null;
  sblrrq?: string | null;
  sbxgrq?: string | null;
}

export interface SupplierDetail extends SupplierItem {
  sbtaxpayer?: string | null;
  sblxr?: string | null;
  sblxfs?: string | null;
  sbtel?: string | null;
  sbemail?: string | null;
  sbsname?: string | null;
  sbbank?: string | null;
  sbaccntno?: string | null;
  sbaddr?: string | null;
  sbtaxno?: string | null;
  sbfrdb?: string | null;
  sbyjcgy?: string | null;
  grade?: string | null;
  sbnbtype?: string | null;
  sbiftt?: string | null;
  sbcomname?: string | null;
  sbcomename?: string | null;
  sbyt?: string | null;
  sbxfdx?: string | null;
  sbyxmf?: string | null;
  sbyxrent?: number | null;
  sbyxmon?: number | null;
  sbyxmj?: number | null;
  sbopendesc?: string | null;
  sbppdesc?: string | null;
  sbjfyq?: string | null;
  sbmemo?: string | null;
  sbwmid1?: string | null;
  sbwmid2?: string | null;
  sbwmid3?: string | null;
  sbwmid4?: string | null;
  sbwmid5?: string | null;
  sbjszq?: number | null;
  sbdhzq?: number | null;
  sbdbsend?: string | null;
  sblry?: string | null;
  sbljsrq?: string | null;
  sbxgr?: string | null;
}

export interface SupplierMutationInput {
  sbid: string;
  sbcname: string;
  sbsname?: string | null;
  sbstatus?: string;
  sbflag?: string;
  sbregcode?: string;
  sbcatcode?: string;
  sbtaxpayer?: string;
  sblxr?: string | null;
  sblxfs?: string | null;
  sbtel?: string | null;
  sbemail?: string | null;
  sbbank?: string | null;
  sbaccntno?: string | null;
  sbaddr?: string | null;
  sbtaxno?: string | null;
  sbfrdb?: string | null;
  sbyjcgy?: string | null;
  grade?: string | null;
  sbnbtype?: string | null;
  sbiftt?: string | null;
  sbcomname?: string | null;
  sbcomename?: string | null;
  sbyt?: string | null;
  sbxfdx?: string | null;
  sbyxmf?: string | null;
  sbyxrent?: number | null;
  sbyxmon?: number | null;
  sbyxmj?: number | null;
  sbopendesc?: string | null;
  sbppdesc?: string | null;
  sbjfyq?: string | null;
  sbmemo?: string | null;
  sbwmid1?: string;
  sbwmid2?: string;
  sbwmid3?: string;
  sbwmid4?: string;
  sbwmid5?: string;
  sbjszq?: number;
  sbdhzq?: number;
  sbdbsend?: string;
  sblry?: string;
  sbxgr?: string | null;
}

export interface SupplierUpdateInput extends Omit<SupplierMutationInput, "sbid"> {
  sbid?: string;
}

export function useSuppliers(supplierCode?: string, supplierName?: string, status?: string) {
  return useQuery({
    queryKey: ["suppliers", supplierCode ?? "", supplierName ?? "", status ?? ""],
    queryFn: () => {
      const params = new URLSearchParams();
      if (supplierCode?.trim()) params.set("supplier_code", supplierCode.trim());
      if (supplierName?.trim()) params.set("supplier_name", supplierName.trim());
      if (status?.trim()) params.set("status", status.trim());
      const query = params.toString();
      return apiGet<SupplierItem[]>(`/api/suppliers/${query ? `?${query}` : ""}`);
    },
  });
}

export function useSupplierDetail(supplierId?: string) {
  return useQuery({
    queryKey: ["supplier-detail", supplierId ?? ""],
    enabled: Boolean(supplierId?.trim()),
    queryFn: () => apiGet<SupplierDetail>(`/api/suppliers/${encodeURIComponent(supplierId!.trim())}`),
  });
}

export function useCreateSupplier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: SupplierMutationInput) => apiPost<SupplierDetail>("/api/suppliers/", input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
  });
}

export function useUpdateSupplier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ supplierId, input }: { supplierId: string; input: SupplierUpdateInput }) =>
      apiPut<SupplierDetail>(`/api/suppliers/${encodeURIComponent(supplierId)}`, input),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      qc.invalidateQueries({ queryKey: ["supplier-detail", variables.supplierId] });
    },
  });
}

export function useDeleteSupplier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (supplierId: string) =>
      apiDelete<{ message: string; id: string }>(`/api/suppliers/${encodeURIComponent(supplierId)}`),
    onSuccess: async (_, supplierId) => {
      await qc.invalidateQueries({ queryKey: ["suppliers"] });
      await qc.invalidateQueries({ queryKey: ["supplier-detail", supplierId] });
      await qc.refetchQueries({ queryKey: ["suppliers"], type: "active" });
    },
  });
}
