"""Shared definitions for the New Century (market 603) campaign dashboard."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any


MARKET_CODE = "603"
STORE_ID = "3"
STORE_NAME = "常州新世纪商城"
PERMISSION_CODE = "activity_analysis.new_century_campaign.view"
MAX_RANGE_DAYS = 366


def validate_period(start_date: date, end_date: date, *, label: str) -> None:
    if start_date > end_date:
        raise ValueError(f"{label}开始日期不能晚于结束日期")
    if (end_date - start_date).days + 1 > MAX_RANGE_DAYS:
        raise ValueError(f"{label}最多查询 {MAX_RANGE_DAYS} 天")


def previous_year_period(start_date: date, end_date: date) -> tuple[date, date]:
    """Return a stable prior-year period, including leap-day handling."""
    try:
        return start_date.replace(year=start_date.year - 1), end_date.replace(year=end_date.year - 1)
    except ValueError:
        # 29 February has no direct peer in a non-leap prior year.
        duration = end_date - start_date
        adjusted_start = start_date - timedelta(days=365)
        return adjusted_start, adjusted_start + duration


def safe_change_percent(current: Any, comparison: Any) -> float | None:
    current_value = Decimal(str(current or 0))
    comparison_value = Decimal(str(comparison or 0))
    if comparison_value == 0:
        return None
    return float((current_value - comparison_value) / abs(comparison_value) * Decimal("100"))


def safe_ratio(numerator: Any, denominator: Any, *, percent: bool = False) -> float | None:
    denominator_value = Decimal(str(denominator or 0))
    if denominator_value == 0:
        return None
    result = Decimal(str(numerator or 0)) / denominator_value
    if percent:
        result *= Decimal("100")
    return float(result)


def mask_member_no(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "未匹配"
    if len(text) <= 4:
        return text[:1] + "*" * max(len(text) - 1, 1)
    return f"{text[:2]}{'*' * (len(text) - 4)}{text[-2:]}"


def mask_mobile(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        return "未提供"
    if len(digits) < 7:
        return digits[:2] + "*" * max(len(digits) - 2, 1)
    return f"{digits[:3]}****{digits[-4:]}"


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date,)):
        return value.isoformat()
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
