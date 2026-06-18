import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export interface ManaframeItem {
  mfcode: string;
  mfcname?: string | null;
  store_code?: string | null;
  store_id?: number | null;
  mfstatus?: string | null;
  mfjyfs?: string | null;
  mfjywz?: string | null;
  mfjyqy?: string | null;
  mfclass?: number | null;
  mffcode?: string | null;
  mfpcode?: string | null;
  mfflag?: string | null;
  mfcatcode?: string | null;
  mfsubject?: string | null;
  mfmemo?: string | null;
}

export interface ManaframeFilters {
  storeId: string;
  groupCode: string;
  groupName: string;
}

export function useManaframe(filters: ManaframeFilters) {
  return useQuery({
    queryKey: ["manaframe", filters],
    queryFn: () => {
      const q = new URLSearchParams();
      if (filters.storeId && filters.storeId !== "ALL") q.set("store_id", filters.storeId);
      if (filters.groupCode.trim()) q.set("group_code", filters.groupCode.trim());
      if (filters.groupName.trim()) q.set("group_name", filters.groupName.trim());
      return apiGet<ManaframeItem[]>(`/api/manaframe/?${q.toString()}`);
    },
  });
}
