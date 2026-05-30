import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";

export interface UnitMapVersionItem {
  id: number;
  floor_id: number;
  base_map_id: number;
  version_code: string;
  is_active: boolean;
  change_note?: string | null;
  created_at?: string | null;
}

export interface CreateUnitMapVersionInput {
  floor_id: number;
  base_map_id: number;
  version_code: string;
  is_active?: boolean;
  change_note?: string;
}

export interface UpdateUnitMapVersionInput {
  base_map_id?: number;
  version_code?: string;
  is_active?: boolean;
  change_note?: string | null;
}

export interface AlignTransform {
  version_id: number;
  dx: number;
  dy: number;
  sx: number;
  sy: number;
  rotate: number;
  updated_at?: string | null;
}

export function useUnitMapVersions(floorId?: number, baseMapId?: number, storeId?: number | null) {
  return useQuery({
    queryKey: ["unit-map-versions", storeId ?? "all", floorId ?? "all", baseMapId ?? "all"],
    queryFn: () =>
      apiGet<UnitMapVersionItem[]>(
        `/api/unit-map-versions?${[
          storeId != null ? `store_id=${encodeURIComponent(String(storeId))}` : "",
          floorId != null ? `floor_id=${encodeURIComponent(String(floorId))}` : "",
          baseMapId != null ? `base_map_id=${encodeURIComponent(String(baseMapId))}` : "",
        ]
          .filter(Boolean)
          .join("&")}`,
      ),
  });
}

export function useCreateUnitMapVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateUnitMapVersionInput) =>
      apiPost<UnitMapVersionItem>("/api/unit-map-versions/", input),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["unit-map-versions"] });
      qc.invalidateQueries({
        queryKey: ["unit-map-versions", data.floor_id, "all"],
      });
    },
  });
}

export function useActivateUnitMapVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiPost<{ message: string; id: number }>(`/api/unit-map-versions/${id}/activate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["unit-map-versions"] });
    },
  });
}

export function useAlignTransform(versionId?: number) {
  return useQuery({
    queryKey: ["unit-map-align-transform", versionId ?? "none"],
    enabled: versionId != null,
    queryFn: () => apiGet<AlignTransform>(`/api/unit-map-versions/${versionId}/align-transform`),
  });
}

export function useSaveAlignTransform() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: Omit<AlignTransform, "updated_at">) =>
      apiPut<AlignTransform>(`/api/unit-map-versions/${input.version_id}/align-transform`, {
        dx: input.dx,
        dy: input.dy,
        sx: input.sx,
        sy: input.sy,
        rotate: input.rotate,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["unit-map-align-transform", data.version_id] });
    },
  });
}

export function useUpdateUnitMapVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateUnitMapVersionInput }) =>
      apiPut<UnitMapVersionItem>(`/api/unit-map-versions/${id}`, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["unit-map-versions"] });
    },
  });
}

export function useDeleteUnitMapVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiDelete<{ message: string; id: number }>(`/api/unit-map-versions/${id}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["unit-map-versions"] });
      await qc.invalidateQueries({ queryKey: ["geo-elements"] });
      await qc.refetchQueries({ queryKey: ["unit-map-versions"], type: "active" });
      await qc.refetchQueries({ queryKey: ["geo-elements"], type: "active" });
    },
  });
}
