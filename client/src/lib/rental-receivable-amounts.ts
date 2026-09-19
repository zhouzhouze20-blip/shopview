function currencyCents(value?: number | null): number {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.round(value * 100)
    : 0;
}

export function supplierActualReceivableAmount(
  receivableAmount?: number | null,
  salesRefundAmount?: number | null,
): number {
  return (currencyCents(receivableAmount) - currencyCents(salesRefundAmount)) / 100;
}
