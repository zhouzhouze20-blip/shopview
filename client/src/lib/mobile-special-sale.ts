export const MOBILE_SPECIAL_SALE_UNIT_CODE = "流动特卖";

export function isMobileSpecialSaleUnit(unitCode?: string | null) {
  return (unitCode || "").trim() === MOBILE_SPECIAL_SALE_UNIT_CODE;
}
