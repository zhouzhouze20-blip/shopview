from decimal import Decimal


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
    normalized = normalize_period_month(period_month)
    year = int(normalized[:4])
    month = int(normalized[5:7])
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month + 1:02d}-01"
    return start_date, end_date


def previous_period_month(period_month: str) -> str:
    normalized = normalize_period_month(period_month)
    year = int(normalized[:4])
    month = int(normalized[5:7])
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"


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
