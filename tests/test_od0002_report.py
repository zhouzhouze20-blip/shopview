from datetime import date

import pytest

from python_app.services.od0002_report import (
    EXCLUDED_DEPARTMENT_CODES,
    FLOOR_NAMES,
    compare_period,
    metric_triplet,
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
