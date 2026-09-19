import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  buildMobileFinancialMonthDates,
  buildMobileFinancialMonthRequest,
  financialMonthRowKey,
} from "./mobile-sales-financial-month.ts";

test("month-to-date includes today and compares to the same calendar day last year", () => {
  assert.deepEqual(buildMobileFinancialMonthDates("2026-08-30"), {
    start_date: "2026-08-29", end_date: "2026-08-30",
    prior_start_date: "2025-08-29", prior_end_date: "2025-08-30",
  });
});

test("financial month switches on the 29th, including the first day", () => {
  assert.equal(buildMobileFinancialMonthDates("2026-08-28").start_date, "2026-07-29");
  assert.deepEqual(buildMobileFinancialMonthDates("2026-08-29"), {
    start_date: "2026-08-29", end_date: "2026-08-29",
    prior_start_date: "2025-08-29", prior_end_date: "2025-08-29",
  });
});

test("first and final fiscal periods retain their special year boundaries", () => {
  assert.equal(buildMobileFinancialMonthDates("2026-01-01").start_date, "2026-01-01");
  assert.equal(buildMobileFinancialMonthDates("2026-01-29").start_date, "2026-01-29");
  assert.deepEqual(buildMobileFinancialMonthDates("2026-12-31"), {
    start_date: "2026-11-29", end_date: "2026-12-31",
    prior_start_date: "2025-11-29", prior_end_date: "2025-12-31",
  });
});

test("leap years use each year's fiscal start without shifting the cutoff by elapsed days", () => {
  assert.deepEqual(buildMobileFinancialMonthDates("2025-03-01"), {
    start_date: "2025-03-01", end_date: "2025-03-01",
    prior_start_date: "2024-02-29", prior_end_date: "2024-03-01",
  });
  assert.deepEqual(buildMobileFinancialMonthDates("2024-03-01"), {
    start_date: "2024-02-29", end_date: "2024-03-01",
    prior_start_date: "2023-03-01", prior_end_date: "2023-03-01",
  });
});

const base = { endDate: "2026-08-30", includeRentalAndBackofficeSales: false };
const request = (options) => new URL(buildMobileFinancialMonthRequest({ ...base, ...options }), "http://test.local");

test("September 7 today and September 6 cutoff update both sales and prior-year dates", () => {
  for (const level of ["stores", "departments", "groups"]) {
    const scope = { level, storeId: "1", departmentCode: "D1" };
    const today = request({ ...scope, endDate: "2026-09-07" });
    const yesterday = request({ ...scope, endDate: "2026-09-06" });
    assert.equal(today.searchParams.get("start_date"), "2026-08-29");
    assert.equal(today.searchParams.get("end_date"), "2026-09-07");
    assert.equal(today.searchParams.get("prior_end_date"), "2025-09-07");
    assert.equal(yesterday.searchParams.get("start_date"), "2026-08-29");
    assert.equal(yesterday.searchParams.get("end_date"), "2026-09-06");
    assert.equal(yesterday.searchParams.get("prior_start_date"), "2025-08-29");
    assert.equal(yesterday.searchParams.get("prior_end_date"), "2025-09-06");
    assert.notEqual(today.href, yesterday.href);
  }
});

test("dashboard and self-operated monthly queries use the applied end date", () => {
  const dashboard = readFileSync(new URL("../pages/mobile-sales-dashboard.tsx", import.meta.url), "utf8");
  const selfOperated = readFileSync(new URL("../components/mobile-self-operated-sales.tsx", import.meta.url), "utf8");
  assert.match(dashboard, /buildMobileFinancialMonthDates\(endDate\)/);
  assert.match(dashboard, /buildMobileFinancialMonthRequest\(\{\s*endDate,/);
  assert.match(dashboard, /queryKey: \["mobile-sales-financial-month", financialMonthEndpoint\]/);
  assert.doesNotMatch(dashboard, /不随筛选日期变化/);
  assert.match(selfOperated, /buildMobileFinancialMonthDates\(endDate\)/);
});

test("store month request uses fiscal dates through the selected cutoff and excludes rental/backoffice by default", () => {
  const url = request({ level: "stores", storeId: "stale-store", departmentCode: "stale-dept" });
  assert.equal(url.pathname, "/api/sales/summary/stores");
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    start_date: "2026-08-29", end_date: "2026-08-30",
    prior_start_date: "2025-08-29", prior_end_date: "2025-08-30",
    exclude_rental: "true", exclude_backoffice_departments: "true", limit: "1000",
  });
});

test("department and group requests preserve drilldown scope and business filters", () => {
  const department = request({ level: "departments", storeId: "3", includeRentalAndBackofficeSales: true });
  assert.equal(department.pathname, "/api/sales/summary/departments");
  assert.equal(department.searchParams.get("store_id"), "3");
  assert.equal(department.searchParams.get("exclude_rental"), "false");
  assert.equal(department.searchParams.get("exclude_backoffice_departments"), "false");
  const group = request({ level: "groups", storeId: "1", departmentCode: "D1", keyword: "女装 & A" });
  assert.equal(group.pathname, "/api/sales/summary/groups");
  assert.equal(group.searchParams.get("store_id"), "1");
  assert.equal(group.searchParams.get("department_code"), "D1");
  assert.equal(group.searchParams.get("keyword"), "女装 & A");
  assert.equal(group.searchParams.has("unassigned_department"), false);
});

test("unassigned department does not accidentally request every department", () => {
  const url = request({ level: "groups", storeId: "1", departmentCode: "" });
  assert.equal(url.searchParams.get("unassigned_department"), "true");
  assert.equal(url.searchParams.has("department_code"), false);
});

test("missing scope, deeper pages and an empty prior fiscal period do not issue requests", () => {
  for (const options of [
    { level: "departments" }, { level: "groups", storeId: "1" },
    { level: "tickets" }, { level: "department-products" },
    { level: "stores", endDate: "2024-02-29" },
  ]) assert.equal(buildMobileFinancialMonthRequest({ ...base, ...options }), null);
});

test("monthly rows match identity, not sales rank; named unassigned buckets remain separate", () => {
  const rows = [
    { department_code: "", department_name: "未归属部门", effective_sales: 100 },
    { department_code: "", department_name: "历史部门", effective_sales: 200 },
    { department_code: "D1", department_name: "女装", effective_sales: 300 },
  ];
  const mapped = new Map(rows.map((row) => [financialMonthRowKey("departments", row), row]));
  assert.equal(mapped.get(financialMonthRowKey("departments", rows[2])).effective_sales, 300);
  assert.equal(mapped.size, 3);
  assert.equal(mapped.get("D2:无月销售"), undefined);
  assert.equal(financialMonthRowKey("stores", { store_id: "3", effective_sales: 10 }), "3");
  assert.equal(financialMonthRowKey("groups", { group_code: "G1", effective_sales: 10 }), "G1");
});
