"""品类主管实时绩效的纯计算规则。"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_SCALE = Decimal("0.0001")
SCORE_SCALE = Decimal("0.01")


@dataclass(frozen=True)
class PeriodWindow:
    period_month: date
    start_date: date
    end_date: date


def parse_period_month(value: str) -> PeriodWindow:
    """Parse YYYY-MM and return the inclusive calendar-month window."""
    normalized = str(value or "").strip()
    try:
        year_text, month_text = normalized.split("-", 1)
        year = int(year_text)
        month = int(month_text)
        start = date(year, month, 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("月份格式必须为 YYYY-MM") from exc
    end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    return PeriodWindow(period_month=start, start_date=start, end_date=end)


def decimal_value(value: object, default: Decimal = Decimal("0")) -> Decimal:
    if value in (None, ""):
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def completion_rate(actual: object, target: object) -> Decimal | None:
    target_value = decimal_value(target)
    if target_value <= 0:
        return None
    return decimal_value(actual) / target_value


def weighted_score(actual: object, target: object, weight: object) -> Decimal | None:
    rate = completion_rate(actual, target)
    if rate is None:
        return None
    return (rate * decimal_value(weight)).quantize(SCORE_SCALE, rounding=ROUND_HALF_UP)


def performance_coefficient(total_score: object | None) -> Decimal | None:
    if total_score is None:
        return None
    score = decimal_value(total_score)
    if score >= Decimal("100"):
        return Decimal("1.2")
    if score >= Decimal("90"):
        return Decimal("1.0")
    if score >= Decimal("80"):
        return Decimal("0.9")
    return Decimal("0.8")


def build_score_row(
    *,
    area_target: object,
    area_actual: object,
    area_weight: object,
    key_target: object,
    key_actual: object,
    key_weight: object,
    self_score: object | None,
) -> dict[str, Decimal | None | bool]:
    area_target_value = decimal_value(area_target).quantize(MONEY_SCALE)
    area_actual_value = decimal_value(area_actual).quantize(MONEY_SCALE)
    key_target_value = decimal_value(key_target).quantize(MONEY_SCALE)
    key_actual_value = decimal_value(key_actual).quantize(MONEY_SCALE)
    area_score = weighted_score(area_actual_value, area_target_value, area_weight)

    key_weight_value = decimal_value(key_weight)
    if key_weight_value == 0:
        key_rate = None
        key_score = Decimal("0.00")
    else:
        key_rate = completion_rate(key_actual_value, key_target_value)
        key_score = weighted_score(key_actual_value, key_target_value, key_weight_value)

    self_score_value = None if self_score is None else decimal_value(self_score)
    score_complete = (
        area_score is not None
        and key_score is not None
        and self_score_value is not None
    )
    total_score = None
    if score_complete:
        total_score = (
            area_score + key_score + self_score_value
        ).quantize(SCORE_SCALE, rounding=ROUND_HALF_UP)

    return {
        "area_target": area_target_value,
        "area_actual": area_actual_value,
        "area_rate": completion_rate(area_actual_value, area_target_value),
        "area_score": area_score,
        "key_target": key_target_value,
        "key_actual": key_actual_value,
        "key_rate": key_rate,
        "key_score": key_score,
        "self_score": self_score_value,
        "score_complete": score_complete,
        "total_score": total_score,
        "coefficient": performance_coefficient(total_score),
    }
