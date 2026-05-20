import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";

export interface FloorDictItem {
  id: number;
  store_id?: string | null;
  building_code: string;
  floor_code: string;
  name: string;
  building_area?: number | null;
  sort_no: number;
  created_at?: string | null;
}

export interface BaseMapItem {
  id: number;
  floor_id: number;
  store_id?: string | null;
  building_code?: string | null;
  floor_code?: string | null;
  floor_name?: string | null;
  base_map_code: string;
  file_url: string;
  svg_viewbox?: string | null;
  svg_width?: number | null;
  svg_height?: number | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface CreateBaseMapInput {
  floor_id: number;
  base_map_code: string;
  file_url: string;
  svg_viewbox?: string;
  svg_width?: number;
  svg_height?: number;
  is_active?: boolean;
}

export interface UpdateBaseMapInput {
  base_map_code?: string;
  svg_viewbox?: string | null;
  svg_width?: number | null;
  svg_height?: number | null;
  is_active?: boolean;
}

export function useFloorDictList() {
  return useQuery({
    queryKey: ["floors-dict"],
    queryFn: () => apiGet<FloorDictItem[]>("/api/floors/"),
  });
}

export function useBaseMapFloorOptions() {
  return useQuery({
    queryKey: ["base-map-floor-options"],
    queryFn: () => apiGet<FloorDictItem[]>("/api/base-maps/floor-options"),
  });
}

export function useBaseMapsList(floorId?: number) {
  return useQuery({
    queryKey: ["base-maps", floorId ?? "all"],
    queryFn: () =>
      apiGet<BaseMapItem[]>(
        floorId ? `/api/base-maps/?floor_id=${encodeURIComponent(String(floorId))}` : "/api/base-maps/"
      ),
  });
}

export function useCreateBaseMap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateBaseMapInput) => apiPost<BaseMapItem>("/api/base-maps/", input),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["base-maps"] });
      qc.invalidateQueries({ queryKey: ["base-maps", data.floor_id] });
    },
  });
}

export function useActivateBaseMap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (baseMapId: number) => apiPost<{ message: string; id: number }>(`/api/base-maps/${baseMapId}/activate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["base-maps"] });
    },
  });
}

export function useUpdateBaseMap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateBaseMapInput }) =>
      apiPut<BaseMapItem>(`/api/base-maps/${id}`, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["base-maps"] });
    },
  });
}

export function useDeleteBaseMap() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiDelete<{ message: string; id: number }>(`/api/base-maps/${id}`),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["base-maps"] });
      await qc.refetchQueries({ queryKey: ["base-maps"], type: "active" });
    },
  });
}
