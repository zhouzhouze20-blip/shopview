from decimal import Decimal


COUPON_MONTHLY_INITIAL_PERIOD = "2026-07"


def normalize_period_month(period_month: str) -> str:
    value = period_month.strip()
    if len(value) != 7 or value[4] != "-":
        raise ValueError("period_month must be YYYY-MM")
    year_text, month_text = value.split("-", 1)
    if not year_text.isdigit() or not month_text.isdigit():
        raise ValueError("period_month must be YYYY-MM")
    month = int(month_text)
    if month < 1 or month > 12:
        raise ValueError("period_month month must be between 01 and 12")
    return f"{int(year_text):04d}-{month:02d}"


def month_bounds(period_month: str) -> tuple[str, str]:
    """Return the half-open ShopView financial month: prior 29th to current 29th."""
    normalized = normalize_period_month(period_month)
    return f"{previous_period_month(normalized)}-29", f"{normalized}-29"


def previous_period_month(period_month: str) -> str:
    normalized = normalize_period_month(period_month)
    year = int(normalized[:4])
    month = int(normalized[5:7])
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"


def opening_balance_source_period(
    period_month: str,
    initial_period: str = COUPON_MONTHLY_INITIAL_PERIOD,
) -> str | None:
    normalized_period = normalize_period_month(period_month)
    normalized_initial_period = normalize_period_month(initial_period)
    if normalized_period <= normalized_initial_period:
        return None
    return previous_period_month(normalized_period)


def coupon_recharge_source_key(business_date: str, market_code: str, coupon_type: str) -> str:
    return f"coupon_recharge:{business_date}:{market_code.strip()}:{coupon_type.strip().upper()}"


def calculate_ending_balance(
    opening_balance: Decimal | int | float | str,
    current_month_increase: Decimal | int | float | str,
    current_month_decrease: Decimal | int | float | str,
    nc_carryover_amount: Decimal | int | float | str,
) -> Decimal:
    return (
        Decimal(str(opening_balance))
        + Decimal(str(current_month_increase))
        - Decimal(str(current_month_decrease))
        - Decimal(str(nc_carryover_amount))
    )
