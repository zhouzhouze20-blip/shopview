import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export interface GeoElementItem {
  id: number;
  version_id: number;
  unit_id: number;
  svg_element_id?: string | null;
  path_data: string;
  centroid_x?: number | null;
  centroid_y?: number | null;
  bbox_minx?: number | null;
  bbox_miny?: number | null;
  bbox_maxx?: number | null;
  bbox_maxy?: number | null;
  area_svg?: number | null;
  created_at?: string | null;
}

export function useGeoElements(versionId?: number) {
  return useQuery({
    queryKey: ["geo-elements", versionId ?? "none"],
    queryFn: () =>
      apiGet<GeoElementItem[]>(
        `/api/geo-elements/?version_id=${encodeURIComponent(String(versionId))}`,
      ),
    enabled: typeof versionId === "number" && Number.isFinite(versionId),
  });
}

