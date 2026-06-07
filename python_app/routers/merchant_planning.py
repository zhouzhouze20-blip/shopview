from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import (
    MerchantCalculationScenario,
    MerchantFollowUp,
    MerchantOpportunity,
    MerchantPlanningProject,
    User,
)
from routers.auth import get_current_user
from routers.authz import require_permission
from schemas.schemas import (
    MerchantCalculationInput,
    MerchantCalculationResult,
    MerchantFollowUpCreate,
    MerchantOpportunityCreate,
    MerchantOpportunityOut,
    MerchantOpportunityUpdate,
    MerchantPlanningProjectCreate,
)


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


def _model_dump(model, **kwargs) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(**kwargs)
    return model.dict(**kwargs)


def _apply_calculation(db: Session, opportunity: MerchantOpportunity, payload: MerchantCalculationInput) -> None:
    calculation_data = _model_dump(payload)
    calculation_data["current_annual_revenue"] = opportunity.current_annual_revenue
    calculation_data["unit_area"] = calculation_data.get("unit_area") or opportunity.unit_area
    calculation = MerchantCalculationInput(**calculation_data)
    result = calculate_merchant_revenue(calculation)
    opportunity.estimated_annual_revenue = result.estimated_annual_revenue
    opportunity.estimated_lift_amount = result.estimated_lift_amount
    db.add(
        MerchantCalculationScenario(
            opportunity_id=opportunity.id,
            cooperation_mode=calculation.cooperation_mode.upper(),
            monthly_rent=calculation.monthly_rent,
            rent_unit_price=calculation.rent_unit_price,
            commission_rate=calculation.commission_rate,
            guaranteed_amount=calculation.guaranteed_amount,
            expected_monthly_sales=calculation.expected_monthly_sales,
            manual_monthly_revenue=calculation.manual_monthly_revenue,
            decoration_days=calculation.decoration_days,
            vacancy_days=calculation.vacancy_days,
            contract_start_date=calculation.contract_start_date,
            contract_end_date=calculation.contract_end_date,
            estimated_monthly_revenue=result.estimated_monthly_revenue,
            estimated_annual_revenue=result.estimated_annual_revenue,
            estimated_lift_amount=result.estimated_lift_amount,
            calculation_snapshot=result.snapshot,
            created_by=getattr(opportunity, "created_by", None),
        )
    )


@router.post("/calculations/preview", response_model=MerchantCalculationResult)
def preview_calculation(
    payload: MerchantCalculationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.view")
    return calculate_merchant_revenue(payload)


@router.get("/opportunities", response_model=list[MerchantOpportunityOut])
def list_opportunities(
    status: str | None = None,
    store_id: str | None = None,
    floor_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.view")
    query = db.query(MerchantOpportunity).order_by(MerchantOpportunity.created_at.desc())
    if status and status != "ALL":
        query = query.filter(MerchantOpportunity.status == status)
    if store_id:
        query = query.filter(MerchantOpportunity.store_id == store_id)
    if floor_id:
        query = query.filter(MerchantOpportunity.floor_id == floor_id)
    return query.limit(500).all()


@router.post("/opportunities", response_model=MerchantOpportunityOut)
def create_opportunity(
    payload: MerchantOpportunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.manage")
    opportunity = MerchantOpportunity(
        **_model_dump(payload, exclude={"calculation"}),
        created_by=current_user.user_id,
    )
    db.add(opportunity)
    db.flush()
    if payload.calculation:
        _apply_calculation(db, opportunity, payload.calculation)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.put("/opportunities/{opportunity_id}", response_model=MerchantOpportunityOut)
def update_opportunity(
    opportunity_id: int,
    payload: MerchantOpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.manage")
    opportunity = db.get(MerchantOpportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    data = _model_dump(payload, exclude_unset=True, exclude={"calculation"})
    for key, value in data.items():
        setattr(opportunity, key, value)
    if payload.calculation:
        _apply_calculation(db, opportunity, payload.calculation)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.view")
    rows = db.query(MerchantOpportunity).all()
    by_status = {"TODO": 0, "NEGOTIATING": 0, "SIGNED": 0, "ABANDONED": 0}
    estimated_lift = Decimal("0")
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        estimated_lift += _money(row.estimated_lift_amount)
    return {
        "by_status": by_status,
        "estimated_lift_amount": _money(estimated_lift),
        "opportunity_count": len(rows),
    }


@router.post("/projects")
def create_project(
    payload: MerchantPlanningProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.manage")
    project = MerchantPlanningProject(
        name=payload.name,
        store_id=payload.store_id,
        floor_ids=payload.floor_ids,
        scope_type=payload.scope_type,
        target_description=payload.target_description,
        owner_user_id=payload.owner_user_id,
        created_by=current_user.user_id,
    )
    db.add(project)
    db.flush()
    if payload.opportunity_ids:
        opportunities = db.query(MerchantOpportunity).filter(MerchantOpportunity.id.in_(payload.opportunity_ids)).all()
        for opportunity in opportunities:
            opportunity.project_id = project.id
    db.commit()
    return {"id": project.id, "message": "created"}


@router.get("/projects")
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.view")
    return db.query(MerchantPlanningProject).order_by(MerchantPlanningProject.created_at.desc()).limit(200).all()


@router.post("/opportunities/{opportunity_id}/follow-ups")
def create_follow_up(
    opportunity_id: int,
    payload: MerchantFollowUpCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.manage")
    opportunity = db.get(MerchantOpportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    row = MerchantFollowUp(
        opportunity_id=opportunity_id,
        follow_up_type=payload.follow_up_type,
        content=payload.content,
        next_action=payload.next_action,
        next_follow_up_at=payload.next_follow_up_at,
        created_by=current_user.user_id,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "message": "created"}


@router.get("/candidates")
def list_candidates(
    store_id: str | None = None,
    floor_id: int | None = None,
    candidate_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "merchant_planning.view")
    sql = """
        SELECT
          bu.id AS unit_id,
          bu.unit_code,
          bu.floor_id,
          f.store_code AS store_id,
          bu.manual_area AS unit_area,
          COALESCE(SUM(uds.total_amount), 0) AS period_revenue,
          MAX(bub.contract_id) AS current_contract_id,
          MAX(bub.brand_id) AS current_brand,
          MAX(bub.end_date) AS contract_end_date
        FROM business_units bu
        LEFT JOIN floors f ON f.id = bu.floor_id
        LEFT JOIN unit_daily_revenue_summary uds ON uds.unit_id = bu.id
        LEFT JOIN business_unit_binding bub
          ON bub.shop_unit_id = bu.id
         AND bub.status = 'ACTIVE'
        WHERE (:store_id IS NULL OR f.store_code = :store_id)
          AND (:floor_id IS NULL OR bu.floor_id = :floor_id)
        GROUP BY bu.id, bu.unit_code, bu.floor_id, f.store_code, bu.manual_area
        ORDER BY bu.floor_id, bu.unit_code
        LIMIT 500
    """
    rows = db.execute(text(sql), {"store_id": store_id, "floor_id": floor_id}).mappings().all()
    result = []
    for row in rows:
        item = dict(row)
        tag = "VACANT" if item["current_contract_id"] is None else "NORMAL"
        if candidate_type and candidate_type != "ALL" and tag != candidate_type:
            continue
        result.append({**item, "candidate_type": tag})
    return {"items": result}
