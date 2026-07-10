from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any


EXCLUDED_DEPARTMENT_CODES = frozenset(
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

FLOOR_NAMES = {
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


def _previous_year(value: date) -> date:
    previous_year = value.year - 1
    last_day = monthrange(previous_year, value.month)[1]
    return date(previous_year, value.month, min(value.day, last_day))


def compare_period(start: date, end: date) -> tuple[date, date]:
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    return _previous_year(start), _previous_year(end)


def _number(value: Any) -> float:
    return float(value or Decimal("0"))


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def metric_triplet(
    sales_current: Any,
    profit_current: Any,
    sales_prior: Any,
    profit_prior: Any,
) -> dict[str, float | None]:
    sc, pc, sp, pp = map(
        _number, (sales_current, profit_current, sales_prior, profit_prior)
    )
    margin_current = _ratio(pc, sc)
    margin_prior = _ratio(pp, sp)
    margin_change = (
        round(margin_current - margin_prior, 12)
        if margin_current is not None and margin_prior is not None
        else None
    )
    return {
        "sales_current": sc,
        "sales_prior": sp,
        "sales_yoy": _ratio(sc - sp, sp),
        "profit_current": pc,
        "profit_prior": pp,
        "profit_yoy": _ratio(pc - pp, pp),
        "margin_current": margin_current,
        "margin_prior": margin_prior,
        "margin_change": margin_change,
    }
