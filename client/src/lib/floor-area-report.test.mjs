import assert from "node:assert/strict";
import test from "node:test";

import {
  floorAreaSummaryPath,
  floorDisplayCode,
  floorTotalArea,
  floorVacancyRate,
  formatFloorArea,
  formatFloorAreaCount,
  formatFloorVacancyRate,
  totalFloorAreaRows,
} from "./floor-area-report.ts";

const row = {
  floor_id: 1,
  store_code: "601",
  store_name: "常州购物中心",
  building_code: "DEFAULT",
  floor_code: "1F",
  name: "一楼",
  active_unit_count: 10,
  active_area_total: 1234.5,
  active_area_missing_count: 2,
  vacant_unit_count: 3,
  vacant_area_total: 456.75,
  vacant_area_missing_count: 1,
  other_unit_count: 4,
  building_area: 3000,
};

test("floor area report sends the selected store as its only query condition", () => {
  assert.equal(
    floorAreaSummaryPath(" 601 "),
    "/api/reports/floor-area-summary?store_code=601",
  );
  assert.equal(floorAreaSummaryPath(" "), "/api/reports/floor-area-summary");
});

test("floor area report totals all four requested measures and quality counts", () => {
  assert.deepEqual(totalFloorAreaRows([row, { ...row, floor_id: 2 }]), {
    activeUnitCount: 20,
    activeAreaTotal: 2469,
    activeAreaMissingCount: 4,
    vacantUnitCount: 6,
    vacantAreaTotal: 913.5,
    vacantAreaMissingCount: 2,
    otherUnitCount: 8,
    totalArea: 3382.5,
  });
});

test("floor area report calculates total area and vacancy rate", () => {
  const totalArea = floorTotalArea(row);

  assert.equal(totalArea, 1691.25);
  assert.equal(floorVacancyRate(row.vacant_area_total, totalArea), 456.75 / 1691.25);
  assert.equal(floorVacancyRate(0, 0), null);
});

test("floor area report formats counts, areas, vacancy rate, and default building codes", () => {
  assert.equal(formatFloorAreaCount(1234), "1,234");
  assert.equal(formatFloorArea(1234.5), "1,234.50");
  assert.equal(formatFloorVacancyRate(0.12345), "12.35%");
  assert.equal(formatFloorVacancyRate(null), "—");
  assert.equal(floorDisplayCode(row), "1F");
  assert.equal(floorDisplayCode({ building_code: "A", floor_code: "2F" }), "A-2F");
});
