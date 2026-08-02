export const BACKOFFICE_REVENUE_UNIT_CODE = "后台部门收益";

export function isBackofficeRevenueUnit(unitCode?: string | null) {
  return (unitCode || "").trim() === BACKOFFICE_REVENUE_UNIT_CODE;
}
