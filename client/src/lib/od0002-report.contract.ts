import type {
  Od0002Metric,
  Od0002Response,
  Od0002Row,
} from "./od0002-report.ts";

const metric = {
  ticket_count_current: 100,
  ticket_count_prior: 80,
  ticket_count_yoy: 0.25,
  average_ticket_current: 1200,
  average_ticket_prior: 1250,
  average_ticket_yoy: -0.04,
  sales_current: 120000,
  sales_prior: 100000,
  sales_yoy: 0.2,
  profit_current: 24000,
  profit_prior: 15000,
  profit_yoy: 0.6,
  margin_current: 0.2,
  margin_prior: 0.15,
  margin_change: 0.05,
} satisfies Od0002Metric;

const row = {
  store_code: "601",
  store_name: "一店",
  dimension_code: "601",
  dimension_name: "一店",
  metrics: metric,
  total: metric,
} satisfies Od0002Row;

const departmentCategoryRows = [
  {
    ...row,
    dimension_code: "C1",
    dimension_name: "中式女装",
    department_code: "6030102",
    department_name: "新世纪二部",
    area_code: "A1",
    area_name: "女装区",
    category_code: "C1",
    category_name: "中式女装",
    row_type: "category",
  },
  {
    ...row,
    dimension_code: "A1",
    dimension_name: "女装区小计",
    department_code: "6030102",
    department_name: "新世纪二部",
    area_code: "A1",
    area_name: "女装区",
    category_code: null,
    category_name: null,
    row_type: "area_subtotal",
  },
  {
    ...row,
    dimension_code: "6030102",
    dimension_name: "新世纪二部小计",
    department_code: "6030102",
    department_name: "新世纪二部",
    area_code: null,
    area_name: null,
    category_code: null,
    category_name: null,
    row_type: "department_subtotal",
  },
] satisfies Od0002Row[];

const specialSaleRow = {
  ...row,
  dimension_code: "6010101999",
  dimension_name: "一楼特卖厅",
  department_code: "6010101",
  department_name: "一店一部(化妆)",
  brand_code: "00310",
  brand_name: "Christian dior迪奥",
} satisfies Od0002Row;

export const od0002ResponseContract = {
  dates: {
    start_date: "2026-01-01",
    end_date: "2026-01-31",
    prior_start_date: "2025-01-01",
    prior_end_date: "2025-01-31",
  },
  selected_store: null,
  dimensions: {
    stores: [row],
    departments: [row],
    department_categories: departmentCategoryRows,
    areas: [row],
    categories: [row],
    groups: [row],
    special_sales: [specialSaleRow],
    floors: [row],
  },
  totals: {
    stores: metric,
    departments: metric,
    department_categories: metric,
    areas: metric,
    categories: metric,
    groups: metric,
    special_sales: metric,
    floors: metric,
  },
  quality: {
    unmatched_area_category_group_count: 0,
    unmatched_floor_group_count: 0,
    unmatched_area_category_sales_current: 0,
    unmatched_floor_sales_current: 0,
  },
  generated_at: "2026-07-10T00:00:00+00:00",
} satisfies Od0002Response;
