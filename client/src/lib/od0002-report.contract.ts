import type {
  Od0002Metric,
  Od0002Response,
  Od0002Row,
} from "./od0002-report.ts";

const metric = {
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
    areas: [row],
    categories: [row],
    groups: [row],
    floors: [row],
  },
  totals: {
    stores: metric,
    departments: metric,
    areas: metric,
    categories: metric,
    groups: metric,
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
