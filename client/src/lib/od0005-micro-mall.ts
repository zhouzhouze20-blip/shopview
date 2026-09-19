export const OD0005_ALL_DEPARTMENTS = "__all__";

export const OD0005_SHEETS = [
  { value: "brand", label: "微商城品牌销售统计" },
  { value: "department", label: "部门销售统计" },
  { value: "daily", label: "逐日销售" },
  { value: "daily_yoy", label: "逐日同期同比" },
  { value: "brand_yoy", label: "品牌同比" },
] as const;

export type Od0005Sheet = (typeof OD0005_SHEETS)[number]["value"];

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

export type Od0005DailyValue = {
  date: string;
  prior_date: string;
  sales_current: number;
  sales_prior: number;
  sales_yoy: number | null;
};

export type Od0005DailyRow = Pick<
  Od0005Row,
  | "store_code"
  | "store_name"
  | "department_code"
  | "department_name"
  | "group_code"
  | "group_name"
> & { daily: Od0005DailyValue[] };

export type Od0005DailyReport = {
  prior_start_date: string;
  prior_end_date: string;
  days: Array<Pick<Od0005DailyValue, "date" | "prior_date">>;
  rows: Od0005DailyRow[];
  totals: Od0005DailyValue[];
};

export type Od0005BrandYoyRow = Pick<
  Od0005Row,
  | "store_code"
  | "store_name"
  | "department_code"
  | "department_name"
  | "group_code"
  | "group_name"
> & {
  sales_two_year_prior: number;
  sales_prior: number;
  sales_current: number;
  difference: number;
  yoy: number | null;
};

export type Od0005BrandYoyReport = {
  periods: {
    two_year_prior: { year: number; start_date: string; end_date: string };
    prior: { year: number; start_date: string; end_date: string };
    current: { year: number; start_date: string; end_date: string };
  };
  rows: Od0005BrandYoyRow[];
  totals: Pick<
    Od0005BrandYoyRow,
    "sales_two_year_prior" | "sales_prior" | "sales_current" | "difference" | "yoy"
  >;
};

export type Od0005Response = {
  report_code: "OD0005";
  title: string;
  start_date: string;
  end_date: string;
  store_code: string;
  store_name: string;
  department_code: string;
  payment_code: string;
  scope_description?: string;
  rows: Od0005Row[];
  totals: Od0005Totals;
  daily: Od0005DailyReport;
  brand_yoy: Od0005BrandYoyReport;
};

export function buildOd0005Params(filters: {
  startDate: string;
  endDate: string;
  storeId: string;
  departmentId: string;
  sheet?: Od0005Sheet;
}): URLSearchParams {
  const params = new URLSearchParams({
    start_date: filters.startDate,
    end_date: filters.endDate,
    store_id: filters.storeId,
  });
  if (filters.sheet) params.set("sheet", filters.sheet);
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
