/** Exact decimal arithmetic: never round the one-yuan acceptance boundary. */
export function matchingTotals(invoices: string[], receipts: string[]) {
  const values = [...invoices, ...receipts];
  if (values.some(value => !/^[+-]?\d+(\.\d+)?$/.test(value))) throw new Error("单据金额无效");
  const scale = Math.max(2, ...values.map(value => value.split(".")[1]?.length ?? 0));
  const unit = BigInt("1" + "0".repeat(scale));
  const parse = (value: string) => {
    const negative = value.startsWith("-");
    const [whole, fraction = ""] = value.replace(/^[+-]/, "").split(".");
    return (negative ? -BigInt(1) : BigInt(1)) * (BigInt(whole) * unit + BigInt(fraction.padEnd(scale, "0")));
  };
  const format = (value: bigint) => `${value < 0 ? "-" : ""}${(value < 0 ? -value : value) / unit}.${((value < 0 ? -value : value) % unit).toString().padStart(scale, "0")}`;
  const left = invoices.reduce((sum, value) => sum + parse(value), BigInt(0));
  const right = receipts.reduce((sum, value) => sum + parse(value), BigInt(0));
  const difference = left - right;
  return { invoiceAmount: format(left), receiptAmount: format(right), difference: format(difference),
    eligible: invoices.length > 0 && receipts.length > 0 && left > 0 && right > 0 && difference >= -unit && difference <= unit };
}
