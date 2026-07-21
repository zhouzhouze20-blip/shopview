import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_app"))

from routers.floor_area_report import _summary_sql


def _compact(sql: str) -> str:
    return " ".join(sql.split())


def test_floor_area_summary_sql_groups_active_and_vacant_separately():
    sql = _compact(_summary_sql("store_code", True))

    assert "LEFT JOIN business_units bu ON bu.floor_id = f.id" in sql
    assert sql.count("= 'ACTIVE'") == 3
    assert sql.count("= 'VACANT'") == 3
    assert "SUM(bu.manual_area) FILTER" in sql
    assert "bu.manual_area IS NULL" in sql
    assert "NOT IN ('ACTIVE', 'VACANT')" in sql


def test_floor_area_summary_sql_filters_the_selected_store_and_keeps_empty_floors():
    sql = _compact(_summary_sql("store_code", True))

    assert ":store_code = '' OR" in sql
    assert "UPPER(TRIM((f.store_code)::text)) = UPPER(TRIM(:store_code))" in sql
    assert "f.building_area AS building_area" in sql
    assert "ORDER BY f.sort_no ASC, f.id ASC" in sql


def test_floor_area_summary_sql_supports_legacy_floor_schema_without_store_or_area():
    sql = _compact(_summary_sql(None, False))

    assert "NULL::text AS store_code" in sql
    assert "NULL::numeric AS building_area" in sql
    assert ":store_code" not in sql
