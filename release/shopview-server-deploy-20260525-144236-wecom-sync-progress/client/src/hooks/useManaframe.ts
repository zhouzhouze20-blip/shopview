import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export interface ManaframeItem {
  mfcode: string;
  mfcname?: string | null;
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

export function useManaframe(keyword: string, statusFilter: string) {
  return useQuery({
    queryKey: ["manaframe", keyword, statusFilter],
    queryFn: () => {
      const q = new URLSearchParams();
      if (keyword.trim()) q.set("keyword", keyword.trim());
      if (statusFilter && statusFilter !== "ALL") q.set("status_filter", statusFilter);
      return apiGet<ManaframeItem[]>(`/api/manaframe/?${q.toString()}`);
    },
  });
}
