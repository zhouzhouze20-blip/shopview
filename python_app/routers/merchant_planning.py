from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import require_permission
from schemas.schemas import MerchantCalculationInput, MerchantCalculationResult


router = APIRouter(prefix="/api/merchant-planning", tags=["merchant-planning"])


def _money(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return _decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _decimal(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _require_non_negative(value: Decimal | int | float | None, field_name: str) -> Decimal:
    if value is None:
        raise HTTPException(status_code=400, detail=f"{field_name} is required")
    decimal_value = _decimal(value)
    if decimal_value < 0:
        raise HTTPException(status_code=400, detail=f"{field_name} must be non-negative")
    return decimal_value


def _require_positive(value: Decimal | int | float | None, field_name: str) -> Decimal:
    decimal_value = _require_non_negative(value, field_name)
    if decimal_value <= 0:
        raise HTTPException(status_code=400, detail=f"{field_name} must be positive")
    return decimal_value


def calculate_merchant_revenue(input: MerchantCalculationInput) -> MerchantCalculationResult:
    decoration_days = max(0, int(input.decoration_days or 0))
    vacancy_days = max(0, int(input.vacancy_days or 0))
    effective_months = max(0, min(12, 12 - ceil((decoration_days + vacancy_days) / 30)))
    mode = (input.cooperation_mode or "").upper()

    if mode == "LEASE":
        if input.monthly_rent is not None:
            monthly = _require_positive(input.monthly_rent, "monthly_rent")
        else:
            rent_unit_price = _require_positive(input.rent_unit_price, "rent_unit_price")
            unit_area = _require_positive(input.unit_area, "unit_area")
            monthly = rent_unit_price * unit_area
    elif mode == "JOINT_OPERATION":
        expected_monthly_sales = _require_non_negative(input.expected_monthly_sales, "expected_monthly_sales")
        commission_rate = _require_non_negative(input.commission_rate, "commission_rate")
        guaranteed_amount = _require_non_negative(input.guaranteed_amount, "guaranteed_amount")
        sales_share = expected_monthly_sales * commission_rate
        monthly = max(sales_share, guaranteed_amount)
    elif mode == "OTHER":
        monthly = _require_non_negative(input.manual_monthly_revenue, "manual_monthly_revenue")
    else:
        raise HTTPException(status_code=400, detail="Unsupported cooperation_mode")

    monthly_revenue = _money(monthly)
    annual_revenue = _money(monthly_revenue * Decimal(effective_months))
    current = _money(input.current_annual_revenue)
    lift = _money(annual_revenue - current)
    return MerchantCalculationResult(
        effective_months=effective_months,
        estimated_monthly_revenue=monthly_revenue,
        estimated_annual_revenue=annual_revenue,
        estimated_lift_amount=lift,
        snapshot={
            "cooperation_mode": mode,
            "decoration_days": decoration_days,
            "vacancy_days": vacancy_days,
            "effective_months": effective_months,
            "current_annual_revenue": str(current),
        },
    )


@router.post("/calculations/preview", response_model=MerchantCalculationResult)
def preview_calculation(
    payload: MerchantCalculationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.view")
    return calculate_merchant_revenue(payload)
