export interface FloorAreaRow {
  floor_id: number;
  store_code?: string | null;
  store_name?: string | null;
  building_code: string;
  floor_code: string;
  name: string;
  active_unit_count: number;
  active_area_total: number;
  active_area_missing_count: number;
  vacant_unit_count: number;
  vacant_area_total: number;
  vacant_area_missing_count: number;
  other_unit_count: number;
  building_area: number;
}

export interface FloorAreaTotals {
  activeUnitCount: number;
  activeAreaTotal: number;
  activeAreaMissingCount: number;
  vacantUnitCount: number;
  vacantAreaTotal: number;
  vacantAreaMissingCount: number;
  otherUnitCount: number;
  totalArea: number;
}

export function floorAreaSummaryPath(storeCode: string): string {
  const params = new URLSearchParams();
  const normalizedStoreCode = storeCode.trim();
  if (normalizedStoreCode) params.set("store_code", normalizedStoreCode);
  const query = params.toString();
  return `/api/reports/floor-area-summary${query ? `?${query}` : ""}`;
}

export function totalFloorAreaRows(rows: readonly FloorAreaRow[]): FloorAreaTotals {
  return rows.reduce<FloorAreaTotals>(
    (total, row) => ({
      activeUnitCount: total.activeUnitCount + Number(row.active_unit_count || 0),
      activeAreaTotal: total.activeAreaTotal + Number(row.active_area_total || 0),
      activeAreaMissingCount:
        total.activeAreaMissingCount + Number(row.active_area_missing_count || 0),
      vacantUnitCount: total.vacantUnitCount + Number(row.vacant_unit_count || 0),
      vacantAreaTotal: total.vacantAreaTotal + Number(row.vacant_area_total || 0),
      vacantAreaMissingCount:
        total.vacantAreaMissingCount + Number(row.vacant_area_missing_count || 0),
      otherUnitCount: total.otherUnitCount + Number(row.other_unit_count || 0),
      totalArea:
        total.totalArea +
        Number(row.active_area_total || 0) +
        Number(row.vacant_area_total || 0),
    }),
    {
      activeUnitCount: 0,
      activeAreaTotal: 0,
      activeAreaMissingCount: 0,
      vacantUnitCount: 0,
      vacantAreaTotal: 0,
      vacantAreaMissingCount: 0,
      otherUnitCount: 0,
      totalArea: 0,
    },
  );
}

export function floorTotalArea(
  row: Pick<FloorAreaRow, "active_area_total" | "vacant_area_total">,
): number {
  return Number(row.active_area_total || 0) + Number(row.vacant_area_total || 0);
}

export function floorVacancyRate(vacantArea: number, totalArea: number): number | null {
  const normalizedTotalArea = Number(totalArea || 0);
  if (normalizedTotalArea <= 0) return null;
  return Number(vacantArea || 0) / normalizedTotalArea;
}

export function formatFloorAreaCount(value: number): string {
  return Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 0 });
}

export function formatFloorArea(value: number): string {
  return Number(value || 0).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatFloorVacancyRate(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("zh-CN", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function floorDisplayCode(row: Pick<FloorAreaRow, "building_code" | "floor_code">): string {
  const buildingCode = String(row.building_code || "").trim();
  const floorCode = String(row.floor_code || "").trim();
  return buildingCode && buildingCode.toUpperCase() !== "DEFAULT"
    ? `${buildingCode}-${floorCode}`
    : floorCode || "—";
}
