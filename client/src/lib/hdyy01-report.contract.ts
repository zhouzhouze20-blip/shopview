import type {
  Hdyy01DraftFilters,
  Hdyy01Quality,
  Hdyy01Response,
  Hdyy01Row,
  Hdyy01Total,
} from "./hdyy01-report.ts";
import {
  changeHdyy01Store,
  syncHdyy01DraftFromGlobalStore,
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
  store_name: "未匹配",
  department_code: null,
  department_name: "未匹配",
  group_code: null,
  group_name: "未匹配",
  floor_code: null,
  level1_code: null,
  level1_name: "未匹配",
  level2_code: null,
  level2_name: "未匹配",
  grade_label: "未匹配",
  average_ticket: null,
} satisfies Hdyy01Row;

const rowWithInvalidNullDisplay = {
  ...unmatchedRow,
  // @ts-expect-error normalize_row guarantees display fields are strings.
  store_name: null,
} satisfies Hdyy01Row;

void rowWithInvalidNullDisplay;

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
  unmatched_member_ticket_count: null,
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

const literalDraft = {
  start: "2026-07-01",
  end: "2026-07-12",
  storeId: "603",
  departmentId: "6030117",
} as const;

const changedLiteralDraft = changeHdyy01Store(literalDraft, "604");
const syncedLiteralDraft = syncHdyy01DraftFromGlobalStore(literalDraft, "604", false);

const changedDraftContract: Hdyy01DraftFilters = changedLiteralDraft;
const syncedDraftContract: Hdyy01DraftFilters = syncedLiteralDraft;

// @ts-expect-error changed store fields must not retain the input's old literal type.
const staleChangedStore: "603" = changedLiteralDraft.storeId;
// @ts-expect-error synchronized store fields must not retain the input's old literal type.
const staleSyncedStore: "603" = syncedLiteralDraft.storeId;
// @ts-expect-error synchronization accepts mapped ERP store codes, not internal numeric ids.
syncHdyy01DraftFromGlobalStore(literalDraft, 4, false);

void changedDraftContract;
void syncedDraftContract;
void staleChangedStore;
void staleSyncedStore;
