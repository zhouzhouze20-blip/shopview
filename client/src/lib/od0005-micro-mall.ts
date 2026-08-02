export const OD0005_ALL_DEPARTMENTS = "__all__";

export type Od0005Row = {
  store_code: string;
  store_name: string;
  department_code: string;
  department_name: string;
  group_code: string;
  group_name: string;
  sales_quantity: number;
  price_amount: number;
  sales_before_discount: number;
  sales_revenue: number;
  gross_profit: number;
  gross_margin: number | null;
  yzq_amount: number;
  other_payment_amount: number;
  nzd_amount: number;
};

export type Od0005Totals = Pick<
  Od0005Row,
  | "sales_quantity"
  | "price_amount"
  | "sales_before_discount"
  | "sales_revenue"
  | "gross_profit"
  | "gross_margin"
  | "yzq_amount"
  | "other_payment_amount"
  | "nzd_amount"
>;

export type Od0005Response = {
  report_code: "OD0005";
  title: string;
  start_date: string;
  end_date: string;
  store_code: string;
  store_name: string;
  department_code: string;
  cashier_code: string;
  scope_description?: string;
  rows: Od0005Row[];
  totals: Od0005Totals;
};

export function buildOd0005Params(filters: {
  startDate: string;
  endDate: string;
  storeId: string;
  departmentId: string;
}): URLSearchParams {
  const params = new URLSearchParams({
    start_date: filters.startDate,
    end_date: filters.endDate,
    store_id: filters.storeId,
  });
  if (filters.departmentId && filters.departmentId !== OD0005_ALL_DEPARTMENTS) {
    params.set("department_id", filters.departmentId);
  }
  return params;
}

export function formatOd0005Number(value: number | null | undefined, kind: "qty" | "amount" | "rate"): string {
  if (value === null || value === undefined) return "—";
  if (kind === "rate") {
    return new Intl.NumberFormat("zh-CN", {
      style: "percent",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  }
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: kind === "amount" ? 2 : 0,
    maximumFractionDigits: kind === "amount" ? 2 : 4,
  }).format(value);
}
