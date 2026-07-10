from datetime import date

import pytest

from python_app.services.od0002_report import (
    EXCLUDED_DEPARTMENT_CODES,
    FLOOR_NAMES,
    build_report_query,
    compare_period,
    metric_triplet,
    normalize_rows,
)


def test_compare_period_uses_same_dates_in_previous_year():
    assert compare_period(date(2026, 5, 29), date(2026, 6, 28)) == (
        date(2025, 5, 29),
        date(2025, 6, 28),
    )


def test_compare_period_clamps_leap_day():
    assert compare_period(date(2024, 2, 29), date(2024, 3, 1)) == (
        date(2023, 2, 28),
        date(2023, 3, 1),
    )


def test_compare_period_rejects_end_before_start():
    with pytest.raises(ValueError):
        compare_period(date(2026, 6, 28), date(2026, 5, 29))


def test_metric_triplet_calculates_weighted_margin_and_yoy():
    assert metric_triplet(120, 24, 100, 15) == {
        "sales_current": 120.0,
        "sales_prior": 100.0,
        "sales_yoy": 0.2,
        "profit_current": 24.0,
        "profit_prior": 15.0,
        "profit_yoy": 0.6,
        "margin_current": 0.2,
        "margin_prior": 0.15,
        "margin_change": 0.05,
    }


def test_metric_triplet_returns_none_when_denominator_is_zero():
    result = metric_triplet(0, 0, 0, 0)

    assert result["sales_yoy"] is None
    assert result["profit_yoy"] is None
    assert result["margin_current"] is None
    assert result["margin_prior"] is None
    assert result["margin_change"] is None


def test_report_constants_match_the_design():
    assert EXCLUDED_DEPARTMENT_CODES == frozenset(
        {
            "6010115",
            "6010108",
            "6010109",
            "6010110",
            "6010202",
            "6010205",
            "6020105",
            "6020107",
            "6020109",
            "6020202",
            "6020205",
            "6030108",
            "6030109",
            "6030111",
            "6030202",
            "6030205",
        }
    )
    assert FLOOR_NAMES == {
        "01": "BF",
        "02": "1F",
        "03": "2F",
        "04": "3F",
        "05": "4F",
        "06": "5F",
        "07": "6F",
        "08": "7F",
        "09": "8F",
        "10": "9F",
        "11": "10F",
        "12": "11F",
        "13": "12F",
        "14": "13F",
        "15": "14F",
        "16": "特卖",
        "17": "微商城",
        "18": "15F",
        "19": "16F",
    }


def test_build_report_query_uses_od0002_sources_filters_and_bound_params():
    scope_sql = " AND NOT (s.sglmarket::text = ANY(:scope_deny_store))"
    sql, params = build_report_query(
        date(2026, 5, 29),
        date(2026, 6, 28),
        date(2025, 5, 29),
        date(2025, 6, 28),
        scope_sql,
        {"scope_deny_store": ["602"]},
        selected_store="601",
    )
    compact = " ".join(sql.split()).lower()

    assert "from salegoodslist s" in compact
    assert "sum(case when s.sglhsrq" in compact
    assert "s.sglxssr" in compact
    assert "s.sgln2" in compact
    assert "join manaframe mf" in compact
    assert "join manaframe dept" in compact
    assert "join area_category ac" in compact
    assert "join stores st" in compact
    assert "s.sglmfid" in compact and "mf.mfcode" in compact
    assert "mf.mfpcode" in compact and "dept.mfcode" in compact
    assert "mf.mfchr1" in compact and "ac.category_code" in compact
    assert "s.sglwmid <> '5'" in compact
    assert "mf.mflc <> '00'" in compact
    assert "trim(both from coalesce(ac.area_name, '')) <> '其他类别区域'" in compact
    assert "replace(coalesce(ac.area_name" not in compact
    assert scope_sql in sql
    assert "s.sglmarket::text = :selected_store" in sql
    assert "s.sglmarket::text as store_code" in compact
    assert "st.store_name as store_name" in compact
    assert "substring(trim(both from coalesce(mf.mfcode" not in compact
    assert set(EXCLUDED_DEPARTMENT_CODES).issubset(set(params["excluded_department_codes"]))
    assert params["scope_deny_store"] == ["602"]
    assert params["selected_store"] == "601"


def test_build_report_query_contains_six_dimensions_and_store_grouping():
    sql, _ = build_report_query(
        date(2026, 1, 1),
        date(2026, 1, 31),
        date(2025, 1, 1),
        date(2025, 1, 31),
        "",
        {},
    )

    for dimension in ("stores", "departments", "areas", "categories", "groups", "floors"):
        assert f"'{dimension}' AS dimension_type" in sql
    for cte in ("departments", "areas", "categories", "groups", "floors"):
        section = sql.split(f"{cte} AS (", 1)[1].split("),", 1)[0]
        assert "store_code" in section.split("GROUP BY", 1)[1]


def test_normalize_rows_keeps_same_department_separate_by_store_and_builds_metrics():
    rows = [
        {
            "dimension_type": "departments", "store_code": "601", "store_name": "一店",
            "dimension_code": "D01", "dimension_name": "女装", "sales_current": 120,
            "profit_current": 24, "sales_prior": 100, "profit_prior": 15,
        },
        FakeMapping({
            "dimension_type": "departments", "store_code": "602", "store_name": "二店",
            "dimension_code": "D01", "dimension_name": "女装", "sales_current": 80,
            "profit_current": 8, "sales_prior": 100, "profit_prior": 10,
        }),
    ]

    dimensions, quality = normalize_rows(rows)

    assert [(row["store_code"], row["dimension_name"]) for row in dimensions["departments"]] == [
        ("601", "女装"), ("602", "女装")
    ]
    assert dimensions["departments"][0]["metrics"] == metric_triplet(120, 24, 100, 15)
    assert quality == {"unmatched_areas": 0, "unmatched_floors": 0}


def test_normalize_rows_reports_unmatched_area_and_floor_counts():
    rows = [
        {"dimension_type": "areas", "store_code": "601", "store_name": "一店",
         "dimension_code": None, "dimension_name": "未匹配", "sales_current": 1,
         "profit_current": 0, "sales_prior": 0, "profit_prior": 0},
        {"dimension_type": "floors", "store_code": "601", "store_name": "一店",
         "dimension_code": "99", "dimension_name": "未匹配", "sales_current": 2,
         "profit_current": 0, "sales_prior": 0, "profit_prior": 0},
    ]

    dimensions, quality = normalize_rows(rows)

    assert dimensions["areas"][0]["dimension_name"] == "未匹配"
    assert dimensions["floors"][0]["dimension_name"] == "未匹配"
    assert quality == {"unmatched_areas": 1, "unmatched_floors": 1}


class FakeMapping:
    """Minimal SQLAlchemy RowMapping-like object (Mapping protocol without dict type)."""

    def __init__(self, values):
        self._values = values

    def keys(self):
        return self._values.keys()

    def __getitem__(self, key):
        return self._values[key]
