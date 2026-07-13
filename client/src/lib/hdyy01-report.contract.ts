import type {
  Hdyy01Quality,
  Hdyy01Response,
  Hdyy01Row,
  Hdyy01Total,
} from "./hdyy01-report.ts";

const row = {
  store_code: "603",
  store_name: "三店",
  department_code: "6030117",
  department_name: "女装部",
  group_code: "6030117001",
  group_name: "女装一组",
  area: 125.5,
  floor_code: "01",
  level1_code: "01",
  level1_name: "服饰",
  level2_code: "0101",
  level2_name: "女装",
  grade_label: "A",
  quantity: 12.25,
  sales_amount: 120000,
  tax_cost: 80000,
  profit: 40000,
  ticket_count: 100,
  average_ticket: 1200,
  member_sales: 90000,
  stored_card_sales: 30000,
} satisfies Hdyy01Row;

const unmatchedRow = {
  ...row,
  store_code: null,
  store_name: null,
  department_code: null,
  department_name: null,
  group_code: null,
  group_name: null,
  floor_code: null,
  level1_code: null,
  level1_name: null,
  level2_code: null,
  level2_name: null,
  grade_label: null,
  average_ticket: null,
} satisfies Hdyy01Row;

const total = {
  quantity: 12.25,
  sales_amount: 120000,
  tax_cost: 80000,
  profit: 40000,
  ticket_count: 100,
  average_ticket: 1200,
  member_sales: 90000,
  stored_card_sales: 30000,
} satisfies Hdyy01Total;

const quality = {
  unmatched_organization_group_count: 0,
  unmatched_organization_amount: 0,
  unmatched_hierarchy_group_count: 0,
  unmatched_hierarchy_amount: 0,
  missing_grade_group_count: 0,
  missing_grade_amount: 0,
  unmatched_member_ticket_count: 0,
} satisfies Hdyy01Quality;

export const hdyy01ResponseContract = {
  dates: { start_date: "2026-07-01", end_date: "2026-07-12" },
  selected_store: "603",
  selected_department: null,
  rows: [row, unmatchedRow],
  total,
  quality,
  generated_at: "2026-07-13T00:00:00+00:00",
} satisfies Hdyy01Response;

const qualityWithWrongKey = {
  ...quality,
  // @ts-expect-error HDYY01 quality uses unmatched_member_ticket_count, not this name.
  unmatched_member_sales_count: 0,
} satisfies Hdyy01Quality;

void qualityWithWrongKey;
