export const MULTI_BUSINESS_UNIT_CODE = "多经";

export function isMultiBusinessUnit(unitCode?: string | null) {
  return (unitCode || "").trim() === MULTI_BUSINESS_UNIT_CODE;
}
