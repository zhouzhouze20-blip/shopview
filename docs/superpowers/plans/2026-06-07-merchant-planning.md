# Merchant Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first MVP of the ShopView 招商规划 module with dual planning modes, contract-condition revenue estimation, and opportunity follow-up workflow.

**Architecture:** Add a dedicated `/api/merchant-planning` backend route backed by three planning tables and one follow-up table. Frontend adds one focused page with tabs for overview, single-unit fill, floor/area planning, and opportunity pool; it reuses existing API helpers, navigation patterns, permission checks, and revenue-map context.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, React, TypeScript, TanStack Query, shadcn/ui, lucide-react.

---

## File Structure

- Create `python_app/alembic/versions/6f7a8b9c0d1e_create_merchant_planning_tables.py`
  - Owns table creation, indexes, comments, and rollback for planning data.
- Modify `python_app/models/models.py`
  - Adds SQLAlchemy models for projects, opportunities, calculation scenarios, and follow-ups.
- Modify `python_app/schemas/schemas.py`
  - Adds Pydantic schemas for API input/output.
- Create `python_app/routers/merchant_planning.py`
  - Owns calculation helpers and `/api/merchant-planning` endpoints.
- Modify `python_app/main.py`
  - Includes the new router. In the clean committed baseline this follows `sales.router`; when the local revenue-map router is present in the working tree, keep `merchant_planning.router` after `revenue.router`.
- Modify `python_app/routers/authz.py`
  - Registers `merchant_planning.view` and `merchant_planning.manage`.
- Create `client/src/hooks/useMerchantPlanning.ts`
  - Owns frontend API types and query/mutation hooks.
- Create `client/src/pages/merchant-planning.tsx`
  - Owns the module UI and local form state.
- Modify `client/src/components/navigation-sidebar.tsx`
  - Adds 招商规划 navigation item beside 收益地图.
- Modify `client/src/pages/main-dashboard.tsx`
  - Imports and routes the new module.
- Modify `client/src/lib/module-permissions.ts`
  - Maps `merchant-planning` to `merchant_planning.view`.
- Modify `client/src/pages/revenue-map.tsx`
  - Adds selected-unit action that opens the merchant planning module with URL/query context.

## Task 1: Database Migration And Models

**Files:**
- Create: `python_app/alembic/versions/6f7a8b9c0d1e_create_merchant_planning_tables.py`
- Modify: `python_app/models/models.py`

- [ ] **Step 1: Create Alembic migration**

Create `python_app/alembic/versions/6f7a8b9c0d1e_create_merchant_planning_tables.py`:

```python
"""create merchant planning tables

Revision ID: 6f7a8b9c0d1e
Revises: c9d0e1f2a3b4
Create Date: 2026-06-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f7a8b9c0d1e"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchant_planning_projects",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("store_id", sa.String(20), nullable=True),
        sa.Column("floor_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("scope_type", sa.String(30), nullable=False, server_default="FLOOR"),
        sa.Column("target_description", sa.Text(), nullable=True),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("current_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_lift_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_lift_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("total_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("scope_type IN ('FLOOR','MULTI_FLOOR','AREA')", name="ck_mpp_scope_type"),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','COMPLETED','CANCELLED')", name="ck_mpp_status"),
    )
    op.create_index("idx_mpp_store_status", "merchant_planning_projects", ["store_id", "status"])

    op.create_table(
        "merchant_opportunities",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("merchant_planning_projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("store_id", sa.String(20), nullable=True),
        sa.Column("floor_id", sa.BigInteger(), nullable=True),
        sa.Column("unit_id", sa.BigInteger(), nullable=True),
        sa.Column("unit_code", sa.String(100), nullable=True),
        sa.Column("unit_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("current_brand", sa.String(200), nullable=True),
        sa.Column("current_contract_id", sa.String(100), nullable=True),
        sa.Column("current_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("target_category", sa.String(100), nullable=True),
        sa.Column("target_brand", sa.String(200), nullable=True),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="TODO"),
        sa.Column("expected_sign_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="P2"),
        sa.Column("estimated_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_lift_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("source_type IN ('REVENUE_MAP','MANUAL','PROJECT')", name="ck_mo_source_type"),
        sa.CheckConstraint("status IN ('TODO','NEGOTIATING','SIGNED','ABANDONED')", name="ck_mo_status"),
        sa.CheckConstraint("priority IN ('P0','P1','P2')", name="ck_mo_priority"),
    )
    op.create_index("idx_mo_project", "merchant_opportunities", ["project_id"])
    op.create_index("idx_mo_unit", "merchant_opportunities", ["unit_id"])
    op.create_index("idx_mo_store_floor_status", "merchant_opportunities", ["store_id", "floor_id", "status"])

    op.create_table(
        "merchant_calculation_scenarios",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("opportunity_id", sa.BigInteger(), sa.ForeignKey("merchant_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cooperation_mode", sa.String(30), nullable=False),
        sa.Column("monthly_rent", sa.Numeric(14, 2), nullable=True),
        sa.Column("rent_unit_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("commission_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("guaranteed_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("expected_monthly_sales", sa.Numeric(14, 2), nullable=True),
        sa.Column("manual_monthly_revenue", sa.Numeric(14, 2), nullable=True),
        sa.Column("decoration_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vacancy_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contract_start_date", sa.Date(), nullable=True),
        sa.Column("contract_end_date", sa.Date(), nullable=True),
        sa.Column("estimated_monthly_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_annual_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_lift_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("calculation_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("cooperation_mode IN ('LEASE','JOINT_OPERATION','OTHER')", name="ck_mcs_cooperation_mode"),
    )
    op.create_index("idx_mcs_opportunity", "merchant_calculation_scenarios", ["opportunity_id"])

    op.create_table(
        "merchant_follow_ups",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("opportunity_id", sa.BigInteger(), sa.ForeignKey("merchant_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("follow_up_type", sa.String(50), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_mfu_opportunity", "merchant_follow_ups", ["opportunity_id"])


def downgrade() -> None:
    op.drop_table("merchant_follow_ups")
    op.drop_table("merchant_calculation_scenarios")
    op.drop_table("merchant_opportunities")
    op.drop_table("merchant_planning_projects")
```

- [ ] **Step 2: Add SQLAlchemy models**

Append these model classes after `BusinessUnitBinding` or near related business-unit models in `python_app/models/models.py`:

```python
class MerchantPlanningProject(Base):
    __tablename__ = "merchant_planning_projects"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    store_id = Column(String(20), nullable=True)
    floor_ids = Column(JSON, nullable=False, default=list)
    scope_type = Column(String(30), nullable=False, default="FLOOR")
    target_description = Column(Text, nullable=True)
    owner_user_id = Column(BigInteger, nullable=True)
    status = Column(String(30), nullable=False, default="DRAFT")
    current_annual_revenue = Column(Numeric(14, 2), nullable=False, default=0)
    estimated_annual_revenue = Column(Numeric(14, 2), nullable=False, default=0)
    estimated_lift_amount = Column(Numeric(14, 2), nullable=False, default=0)
    estimated_lift_rate = Column(Numeric(8, 4), nullable=True)
    total_area = Column(Numeric(12, 2), nullable=True)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    opportunities = relationship("MerchantOpportunity", back_populates="project")


class MerchantOpportunity(Base):
    __tablename__ = "merchant_opportunities"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, ForeignKey("merchant_planning_projects.id"), nullable=True)
    source_type = Column(String(30), nullable=False, default="MANUAL")
    store_id = Column(String(20), nullable=True)
    floor_id = Column(BigInteger, nullable=True)
    unit_id = Column(BigInteger, nullable=True)
    unit_code = Column(String(100), nullable=True)
    unit_area = Column(Numeric(12, 2), nullable=True)
    current_brand = Column(String(200), nullable=True)
    current_contract_id = Column(String(100), nullable=True)
    current_annual_revenue = Column(Numeric(14, 2), nullable=False, default=0)
    target_category = Column(String(100), nullable=True)
    target_brand = Column(String(200), nullable=True)
    owner_user_id = Column(BigInteger, nullable=True)
    status = Column(String(30), nullable=False, default="TODO")
    expected_sign_date = Column(Date, nullable=True)
    priority = Column(String(10), nullable=False, default="P2")
    estimated_annual_revenue = Column(Numeric(14, 2), nullable=False, default=0)
    estimated_lift_amount = Column(Numeric(14, 2), nullable=False, default=0)
    remark = Column(Text, nullable=True)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    project = relationship("MerchantPlanningProject", back_populates="opportunities")
    scenarios = relationship("MerchantCalculationScenario", cascade="all, delete-orphan")
    follow_ups = relationship("MerchantFollowUp", cascade="all, delete-orphan")


class MerchantCalculationScenario(Base):
    __tablename__ = "merchant_calculation_scenarios"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id = Column(BigInteger, ForeignKey("merchant_opportunities.id"), nullable=False)
    cooperation_mode = Column(String(30), nullable=False)
    monthly_rent = Column(Numeric(14, 2), nullable=True)
    rent_unit_price = Column(Numeric(14, 2), nullable=True)
    commission_rate = Column(Numeric(8, 4), nullable=True)
    guaranteed_amount = Column(Numeric(14, 2), nullable=True)
    expected_monthly_sales = Column(Numeric(14, 2), nullable=True)
    manual_monthly_revenue = Column(Numeric(14, 2), nullable=True)
    decoration_days = Column(Integer, nullable=False, default=0)
    vacancy_days = Column(Integer, nullable=False, default=0)
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    estimated_monthly_revenue = Column(Numeric(14, 2), nullable=False, default=0)
    estimated_annual_revenue = Column(Numeric(14, 2), nullable=False, default=0)
    estimated_lift_amount = Column(Numeric(14, 2), nullable=False, default=0)
    calculation_snapshot = Column(JSON, nullable=False, default=dict)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class MerchantFollowUp(Base):
    __tablename__ = "merchant_follow_ups"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id = Column(BigInteger, ForeignKey("merchant_opportunities.id"), nullable=False)
    follow_up_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    follow_up_type = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    next_action = Column(Text, nullable=True)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
```

- [ ] **Step 3: Verify Python syntax**

Run:

```bash
python3 -m py_compile python_app/models/models.py python_app/alembic/versions/6f7a8b9c0d1e_create_merchant_planning_tables.py
```

Expected: exits `0` with no output.

- [ ] **Step 4: Commit**

```bash
git add python_app/models/models.py python_app/alembic/versions/6f7a8b9c0d1e_create_merchant_planning_tables.py
git commit -m "feat: add merchant planning tables"
```

## Task 2: Schemas And Calculation Helper

**Files:**
- Modify: `python_app/schemas/schemas.py`
- Create: `python_app/routers/merchant_planning.py`

- [ ] **Step 1: Add schemas**

Append these schemas to `python_app/schemas/schemas.py`:

```python
class MerchantCalculationInput(BaseModel):
    cooperation_mode: str
    unit_area: Optional[Decimal] = None
    current_annual_revenue: Optional[Decimal] = Decimal("0")
    monthly_rent: Optional[Decimal] = None
    rent_unit_price: Optional[Decimal] = None
    commission_rate: Optional[Decimal] = None
    guaranteed_amount: Optional[Decimal] = None
    expected_monthly_sales: Optional[Decimal] = None
    manual_monthly_revenue: Optional[Decimal] = None
    decoration_days: int = 0
    vacancy_days: int = 0
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None


class MerchantCalculationResult(BaseModel):
    effective_months: int
    estimated_monthly_revenue: Decimal
    estimated_annual_revenue: Decimal
    estimated_lift_amount: Decimal
    snapshot: dict
```

If `BaseModel`, `Decimal`, or `date` is not imported at the top of the file, extend the existing imports:

```python
from datetime import date
from decimal import Decimal
from pydantic import BaseModel
```

- [ ] **Step 2: Create calculation helper route module**

Create the top of `python_app/routers/merchant_planning.py`:

```python
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import require_permission
from schemas.schemas import MerchantCalculationInput, MerchantCalculationResult


router = APIRouter(prefix="/api/merchant-planning", tags=["merchant-planning"])


def _money(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_merchant_revenue(input: MerchantCalculationInput) -> MerchantCalculationResult:
    decoration_days = max(0, int(input.decoration_days or 0))
    vacancy_days = max(0, int(input.vacancy_days or 0))
    effective_months = max(0, min(12, 12 - ceil((decoration_days + vacancy_days) / 30)))
    mode = (input.cooperation_mode or "").upper()

    if mode == "LEASE":
        monthly = input.monthly_rent
        if monthly is None:
            monthly = _money(input.rent_unit_price) * _money(input.unit_area)
    elif mode == "JOINT_OPERATION":
        sales_share = _money(input.expected_monthly_sales) * _money(input.commission_rate)
        monthly = max(sales_share, _money(input.guaranteed_amount))
    elif mode == "OTHER":
        monthly = input.manual_monthly_revenue
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
```

- [ ] **Step 3: Verify helper manually**

Run from `python_app` so the existing absolute imports resolve:

```bash
cd python_app
python3 - <<'PY'
from decimal import Decimal
from schemas.schemas import MerchantCalculationInput
from routers.merchant_planning import calculate_merchant_revenue

result = calculate_merchant_revenue(MerchantCalculationInput(
    cooperation_mode="JOINT_OPERATION",
    expected_monthly_sales=Decimal("100000"),
    commission_rate=Decimal("0.15"),
    guaranteed_amount=Decimal("12000"),
    decoration_days=30,
    vacancy_days=0,
    current_annual_revenue=Decimal("100000"),
))
assert result.effective_months == 11
assert result.estimated_monthly_revenue == Decimal("15000.00")
assert result.estimated_annual_revenue == Decimal("165000.00")
assert result.estimated_lift_amount == Decimal("65000.00")
print("ok")
PY
```

Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add python_app/schemas/schemas.py python_app/routers/merchant_planning.py
git commit -m "feat: add merchant planning calculation preview"
```

## Task 3: Backend API And Permissions

**Files:**
- Modify: `python_app/routers/merchant_planning.py`
- Modify: `python_app/main.py`
- Modify: `python_app/routers/authz.py`

- [ ] **Step 1: Register core permissions**

In `python_app/routers/authz.py`, add to `CORE_PERMISSION_DEFINITIONS` near the revenue permission:

```python
("merchant_planning.view", "查看招商规划", "merchant_planning", "view"),
("merchant_planning.manage", "管理招商规划", "merchant_planning", "manage"),
```

- [ ] **Step 2: Include router**

In `python_app/main.py`, add `merchant_planning` to the routers import list. In the clean committed baseline, include it after `sales.router`; if the local revenue-map router is present in the working tree, keep it after `revenue.router`:

```python
app.include_router(revenue.router)
app.include_router(merchant_planning.router)
```

- [ ] **Step 3: Add CRUD schemas**

Append to `python_app/schemas/schemas.py`:

```python
class MerchantOpportunityCreate(BaseModel):
    project_id: Optional[int] = None
    source_type: str = "MANUAL"
    store_id: Optional[str] = None
    floor_id: Optional[int] = None
    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    unit_area: Optional[Decimal] = None
    current_brand: Optional[str] = None
    current_contract_id: Optional[str] = None
    current_annual_revenue: Decimal = Decimal("0")
    target_category: Optional[str] = None
    target_brand: Optional[str] = None
    owner_user_id: Optional[int] = None
    expected_sign_date: Optional[date] = None
    priority: str = "P2"
    remark: Optional[str] = None
    calculation: Optional[MerchantCalculationInput] = None


class MerchantOpportunityUpdate(BaseModel):
    target_category: Optional[str] = None
    target_brand: Optional[str] = None
    owner_user_id: Optional[int] = None
    status: Optional[str] = None
    expected_sign_date: Optional[date] = None
    priority: Optional[str] = None
    remark: Optional[str] = None
    calculation: Optional[MerchantCalculationInput] = None


class MerchantFollowUpCreate(BaseModel):
    follow_up_type: Optional[str] = None
    content: str
    next_action: Optional[str] = None
    next_follow_up_at: Optional[datetime] = None


class MerchantPlanningProjectCreate(BaseModel):
    name: str
    store_id: Optional[str] = None
    floor_ids: list[int] = []
    scope_type: str = "FLOOR"
    target_description: Optional[str] = None
    owner_user_id: Optional[int] = None
    opportunity_ids: list[int] = []


class MerchantOpportunityOut(BaseModel):
    id: int
    project_id: Optional[int] = None
    source_type: str
    store_id: Optional[str] = None
    floor_id: Optional[int] = None
    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    unit_area: Optional[Decimal] = None
    current_brand: Optional[str] = None
    current_contract_id: Optional[str] = None
    current_annual_revenue: Decimal
    target_category: Optional[str] = None
    target_brand: Optional[str] = None
    owner_user_id: Optional[int] = None
    status: str
    expected_sign_date: Optional[date] = None
    priority: str
    estimated_annual_revenue: Decimal
    estimated_lift_amount: Decimal
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

Also ensure `datetime` is imported from `datetime`.

- [ ] **Step 4: Add opportunity list/create/update endpoints**

In `python_app/routers/merchant_planning.py`, import the models and schemas:

```python
from models.models import (
    MerchantCalculationScenario,
    MerchantFollowUp,
    MerchantOpportunity,
    MerchantPlanningProject,
    User,
)
from schemas.schemas import (
    MerchantCalculationInput,
    MerchantCalculationResult,
    MerchantFollowUpCreate,
    MerchantOpportunityCreate,
    MerchantOpportunityOut,
    MerchantOpportunityUpdate,
    MerchantPlanningProjectCreate,
)
```

Add helper:

```python
def _apply_calculation(db: Session, opportunity: MerchantOpportunity, payload: MerchantCalculationInput) -> None:
    payload.current_annual_revenue = opportunity.current_annual_revenue
    payload.unit_area = payload.unit_area or opportunity.unit_area
    result = calculate_merchant_revenue(payload)
    opportunity.estimated_annual_revenue = result.estimated_annual_revenue
    opportunity.estimated_lift_amount = result.estimated_lift_amount
    db.add(MerchantCalculationScenario(
        opportunity_id=opportunity.id,
        cooperation_mode=payload.cooperation_mode.upper(),
        monthly_rent=payload.monthly_rent,
        rent_unit_price=payload.rent_unit_price,
        commission_rate=payload.commission_rate,
        guaranteed_amount=payload.guaranteed_amount,
        expected_monthly_sales=payload.expected_monthly_sales,
        manual_monthly_revenue=payload.manual_monthly_revenue,
        decoration_days=payload.decoration_days,
        vacancy_days=payload.vacancy_days,
        contract_start_date=payload.contract_start_date,
        contract_end_date=payload.contract_end_date,
        estimated_monthly_revenue=result.estimated_monthly_revenue,
        estimated_annual_revenue=result.estimated_annual_revenue,
        estimated_lift_amount=result.estimated_lift_amount,
        calculation_snapshot=result.snapshot,
    ))
```

Add endpoints:

```python
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
        **payload.model_dump(exclude={"calculation"}),
        created_by=current_user.id,
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
    data = payload.model_dump(exclude_unset=True, exclude={"calculation"})
    for key, value in data.items():
        setattr(opportunity, key, value)
    if payload.calculation:
        _apply_calculation(db, opportunity, payload.calculation)
    db.commit()
    db.refresh(opportunity)
    return opportunity
```

- [ ] **Step 5: Add overview/project/follow-up endpoints**

In `python_app/routers/merchant_planning.py`, add:

```python
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
    return {"by_status": by_status, "estimated_lift_amount": _money(estimated_lift), "opportunity_count": len(rows)}


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
        created_by=current_user.id,
    )
    db.add(project)
    db.flush()
    if payload.opportunity_ids:
        db.query(MerchantOpportunity).filter(MerchantOpportunity.id.in_(payload.opportunity_ids)).update(
            {MerchantOpportunity.project_id: project.id},
            synchronize_session=False,
        )
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
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "message": "created"}
```

- [ ] **Step 6: Add candidate endpoint with simple v1口径**

Add a first-pass endpoint that returns business units with revenue and contract flags. Use conservative SQL, preserve `unit_id` as the key:

```python
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
        is_vacant = row["current_contract_id"] is None
        tag = "VACANT" if is_vacant else "NORMAL"
        if candidate_type and candidate_type != "ALL" and tag != candidate_type:
            continue
        result.append({**dict(row), "candidate_type": tag})
    return {"items": result}
```

Add `from sqlalchemy import text` at the top. Later tasks can expand LOW_EFFICIENCY and EXPIRING once UI is working.

- [ ] **Step 7: Verify backend compiles**

Run:

```bash
python3 -m py_compile python_app/routers/merchant_planning.py python_app/main.py python_app/routers/authz.py python_app/schemas/schemas.py
```

Expected: exits `0` with no output.

- [ ] **Step 8: Commit**

```bash
git add python_app/routers/merchant_planning.py python_app/main.py python_app/routers/authz.py python_app/schemas/schemas.py
git commit -m "feat: add merchant planning api"
```

## Task 4: Frontend Hooks And Module Routing

**Files:**
- Create: `client/src/hooks/useMerchantPlanning.ts`
- Modify: `client/src/components/navigation-sidebar.tsx`
- Modify: `client/src/pages/main-dashboard.tsx`
- Modify: `client/src/lib/module-permissions.ts`

- [ ] **Step 1: Add frontend hook**

Create `client/src/hooks/useMerchantPlanning.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut } from "@/lib/api";

export type MerchantOpportunityStatus = "TODO" | "NEGOTIATING" | "SIGNED" | "ABANDONED";
export type MerchantCooperationMode = "LEASE" | "JOINT_OPERATION" | "OTHER";

export interface MerchantCalculationInput {
  cooperation_mode: MerchantCooperationMode;
  unit_area?: number | null;
  current_annual_revenue?: number | null;
  monthly_rent?: number | null;
  rent_unit_price?: number | null;
  commission_rate?: number | null;
  guaranteed_amount?: number | null;
  expected_monthly_sales?: number | null;
  manual_monthly_revenue?: number | null;
  decoration_days?: number;
  vacancy_days?: number;
  contract_start_date?: string | null;
  contract_end_date?: string | null;
}

export interface MerchantCalculationResult {
  effective_months: number;
  estimated_monthly_revenue: number;
  estimated_annual_revenue: number;
  estimated_lift_amount: number;
  snapshot: Record<string, unknown>;
}

export interface MerchantOpportunity {
  id: number;
  project_id?: number | null;
  source_type: string;
  store_id?: string | null;
  floor_id?: number | null;
  unit_id?: number | null;
  unit_code?: string | null;
  unit_area?: number | null;
  current_brand?: string | null;
  current_contract_id?: string | null;
  current_annual_revenue: number;
  target_category?: string | null;
  target_brand?: string | null;
  owner_user_id?: number | null;
  status: MerchantOpportunityStatus;
  expected_sign_date?: string | null;
  priority: "P0" | "P1" | "P2";
  estimated_annual_revenue: number;
  estimated_lift_amount: number;
  remark?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MerchantOpportunityInput {
  project_id?: number | null;
  source_type?: string;
  store_id?: string | null;
  floor_id?: number | null;
  unit_id?: number | null;
  unit_code?: string | null;
  unit_area?: number | null;
  current_brand?: string | null;
  current_contract_id?: string | null;
  current_annual_revenue?: number;
  target_category?: string | null;
  target_brand?: string | null;
  owner_user_id?: number | null;
  status?: MerchantOpportunityStatus;
  expected_sign_date?: string | null;
  priority?: "P0" | "P1" | "P2";
  remark?: string | null;
  calculation?: MerchantCalculationInput | null;
}

export interface MerchantCandidate {
  unit_id: number;
  unit_code?: string | null;
  floor_id?: number | null;
  store_id?: string | null;
  unit_area?: number | null;
  period_revenue?: number | null;
  current_contract_id?: string | null;
  current_brand?: string | null;
  contract_end_date?: string | null;
  candidate_type: string;
}

export function useMerchantOverview() {
  return useQuery({
    queryKey: ["merchant-planning", "overview"],
    queryFn: () => apiGet<{ by_status: Record<string, number>; estimated_lift_amount: number; opportunity_count: number }>("/api/merchant-planning/overview"),
  });
}

export function useMerchantCandidates(params: { storeId?: string; floorId?: number | null; candidateType?: string }) {
  return useQuery({
    queryKey: ["merchant-planning", "candidates", params],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params.storeId) q.set("store_id", params.storeId);
      if (params.floorId) q.set("floor_id", String(params.floorId));
      if (params.candidateType && params.candidateType !== "ALL") q.set("candidate_type", params.candidateType);
      return apiGet<{ items: MerchantCandidate[] }>(`/api/merchant-planning/candidates?${q.toString()}`);
    },
  });
}

export function useMerchantOpportunities(params?: { status?: string }) {
  return useQuery({
    queryKey: ["merchant-planning", "opportunities", params ?? {}],
    queryFn: () => {
      const q = new URLSearchParams();
      if (params?.status && params.status !== "ALL") q.set("status", params.status);
      return apiGet<MerchantOpportunity[]>(`/api/merchant-planning/opportunities?${q.toString()}`);
    },
  });
}

export function usePreviewMerchantCalculation() {
  return useMutation({
    mutationFn: (input: MerchantCalculationInput) =>
      apiPost<MerchantCalculationResult>("/api/merchant-planning/calculations/preview", input),
  });
}

export function useCreateMerchantOpportunity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: MerchantOpportunityInput) => apiPost<MerchantOpportunity>("/api/merchant-planning/opportunities", input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["merchant-planning"] });
    },
  });
}

export function useUpdateMerchantOpportunity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: MerchantOpportunityInput }) =>
      apiPut<MerchantOpportunity>(`/api/merchant-planning/opportunities/${id}`, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["merchant-planning"] });
    },
  });
}

export function useCreateMerchantFollowUp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: { content: string; follow_up_type?: string; next_action?: string } }) =>
      apiPost<{ id: number; message: string }>(`/api/merchant-planning/opportunities/${id}/follow-ups`, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["merchant-planning"] });
    },
  });
}
```

- [ ] **Step 2: Add permission mapping**

In `client/src/lib/module-permissions.ts`, add:

```typescript
"merchant-planning": ["merchant_planning.view"],
```

- [ ] **Step 3: Add navigation item**

In `client/src/components/navigation-sidebar.tsx`, import `Target` from `lucide-react` and add under `financial-management` before `revenue-map`:

```typescript
{ id: "merchant-planning", name: "招商规划", icon: Target },
```

- [ ] **Step 4: Add main dashboard route**

In `client/src/pages/main-dashboard.tsx`, import the page:

```typescript
import MerchantPlanningPage from "./merchant-planning";
```

Add label:

```typescript
"merchant-planning": "招商规划",
```

Add switch case before revenue map:

```tsx
case "merchant-planning":
  return <MerchantPlanningPage />;
```

- [ ] **Step 5: Run frontend type/build check**

Run:

```bash
npm run build --prefix client
```

Expected: TypeScript and Vite build complete successfully.

- [ ] **Step 6: Commit**

```bash
git add client/src/hooks/useMerchantPlanning.ts client/src/lib/module-permissions.ts client/src/components/navigation-sidebar.tsx client/src/pages/main-dashboard.tsx
git commit -m "feat: wire merchant planning module"
```

## Task 5: Merchant Planning Page MVP

**Files:**
- Create: `client/src/pages/merchant-planning.tsx`

- [ ] **Step 1: Create page skeleton with tabs**

Create `client/src/pages/merchant-planning.tsx`:

```tsx
import { useMemo, useState } from "react";
import { BarChart3, Building2, ClipboardList, Loader2, Plus, Save, Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  MerchantCandidate,
  MerchantCalculationInput,
  MerchantOpportunity,
  useCreateMerchantOpportunity,
  useMerchantCandidates,
  useMerchantOpportunities,
  useMerchantOverview,
  usePreviewMerchantCalculation,
} from "@/hooks/useMerchantPlanning";

const money = (value?: number | string | null) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value ?? 0));

const statusText: Record<string, string> = {
  TODO: "待招商",
  NEGOTIATING: "洽谈中",
  SIGNED: "已签约",
  ABANDONED: "放弃",
};

export default function MerchantPlanningPage() {
  const [tab, setTab] = useState("overview");
  const overview = useMerchantOverview();
  const opportunities = useMerchantOpportunities();

  return (
    <div className="container mx-auto space-y-4 p-4" data-testid="merchant-planning-page">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">招商规划</h1>
          <p className="text-xs text-muted-foreground">基于收益地图识别机会，按合同条件测算招商收益。</p>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="overview">规划总览</TabsTrigger>
          <TabsTrigger value="single">铺位补位</TabsTrigger>
          <TabsTrigger value="floor">整层/片区规划</TabsTrigger>
          <TabsTrigger value="pool">招商机会池</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <OverviewSection loading={overview.isLoading} data={overview.data} opportunities={opportunities.data ?? []} />
        </TabsContent>
        <TabsContent value="single">
          <SingleUnitSection />
        </TabsContent>
        <TabsContent value="floor">
          <FloorPlanningSection />
        </TabsContent>
        <TabsContent value="pool">
          <OpportunityPool opportunities={opportunities.data ?? []} loading={opportunities.isLoading} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

- [ ] **Step 2: Add overview component**

Append:

```tsx
function OverviewSection({
  loading,
  data,
  opportunities,
}: {
  loading: boolean;
  data?: { by_status: Record<string, number>; estimated_lift_amount: number; opportunity_count: number };
  opportunities: MerchantOpportunity[];
}) {
  const counts = data?.by_status ?? {};
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-5">
        <MetricCard title="机会总数" value={loading ? "加载中" : String(data?.opportunity_count ?? 0)} icon={<ClipboardList className="h-4 w-4" />} />
        <MetricCard title="待招商" value={String(counts.TODO ?? 0)} icon={<Target className="h-4 w-4" />} />
        <MetricCard title="洽谈中" value={String(counts.NEGOTIATING ?? 0)} icon={<BarChart3 className="h-4 w-4" />} />
        <MetricCard title="已签约" value={String(counts.SIGNED ?? 0)} icon={<Save className="h-4 w-4" />} />
        <MetricCard title="预计提升" value={money(data?.estimated_lift_amount)} icon={<Plus className="h-4 w-4" />} />
      </div>
      <OpportunityPool opportunities={opportunities.slice(0, 8)} loading={loading} compact />
    </div>
  );
}

function MetricCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <Card className="rounded-md">
      <CardContent className="flex items-center justify-between px-4 py-3">
        <div>
          <div className="text-xs text-muted-foreground">{title}</div>
          <div className="mt-1 text-xl font-semibold">{value}</div>
        </div>
        <div className="text-muted-foreground">{icon}</div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Add single-unit fill section**

Append:

```tsx
function SingleUnitSection() {
  const [candidateType, setCandidateType] = useState("ALL");
  const [selected, setSelected] = useState<MerchantCandidate | null>(null);
  const candidates = useMerchantCandidates({ candidateType });

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <Card className="rounded-md">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>候选铺位</CardTitle>
            <Select value={candidateType} onValueChange={setCandidateType}>
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部</SelectItem>
                <SelectItem value="VACANT">空置</SelectItem>
                <SelectItem value="LOW_EFFICIENCY">低效</SelectItem>
                <SelectItem value="EXPIRING">到期</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <CandidateTable items={candidates.data?.items ?? []} loading={candidates.isLoading} onSelect={setSelected} selectedId={selected?.unit_id} />
        </CardContent>
      </Card>
      <OpportunityForm candidate={selected} />
    </div>
  );
}
```

- [ ] **Step 4: Add candidate table and opportunity form**

Append:

```tsx
function CandidateTable({
  items,
  loading,
  selectedId,
  onSelect,
}: {
  items: MerchantCandidate[];
  loading: boolean;
  selectedId?: number;
  onSelect: (row: MerchantCandidate) => void;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>铺位</TableHead>
          <TableHead>楼层</TableHead>
          <TableHead>面积</TableHead>
          <TableHead>当前合同</TableHead>
          <TableHead className="text-right">周期收益</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {loading ? (
          <TableRow><TableCell colSpan={5} className="py-8 text-center text-muted-foreground">加载中</TableCell></TableRow>
        ) : items.length ? items.map((row) => (
          <TableRow key={row.unit_id} className={selectedId === row.unit_id ? "bg-cyan-50" : "cursor-pointer"} onClick={() => onSelect(row)}>
            <TableCell className="font-medium">{row.unit_code || row.unit_id}</TableCell>
            <TableCell>{row.floor_id ?? "—"}</TableCell>
            <TableCell>{row.unit_area ?? "—"}</TableCell>
            <TableCell>{row.current_contract_id || <Badge variant="secondary">空置</Badge>}</TableCell>
            <TableCell className="text-right">{money(row.period_revenue)}</TableCell>
          </TableRow>
        )) : (
          <TableRow><TableCell colSpan={5} className="py-8 text-center text-muted-foreground">暂无候选铺位</TableCell></TableRow>
        )}
      </TableBody>
    </Table>
  );
}

function OpportunityForm({ candidate }: { candidate: MerchantCandidate | null }) {
  const { toast } = useToast();
  const preview = usePreviewMerchantCalculation();
  const createOpportunity = useCreateMerchantOpportunity();
  const [form, setForm] = useState({
    target_category: "",
    target_brand: "",
    cooperation_mode: "LEASE",
    monthly_rent: "",
    rent_unit_price: "",
    commission_rate: "",
    guaranteed_amount: "",
    expected_monthly_sales: "",
    manual_monthly_revenue: "",
    decoration_days: "0",
    vacancy_days: "0",
    expected_sign_date: "",
    remark: "",
  });

  const calculationInput = useMemo<MerchantCalculationInput>(() => ({
    cooperation_mode: form.cooperation_mode as MerchantCalculationInput["cooperation_mode"],
    unit_area: Number(candidate?.unit_area ?? 0),
    current_annual_revenue: Number(candidate?.period_revenue ?? 0),
    monthly_rent: form.monthly_rent ? Number(form.monthly_rent) : null,
    rent_unit_price: form.rent_unit_price ? Number(form.rent_unit_price) : null,
    commission_rate: form.commission_rate ? Number(form.commission_rate) : null,
    guaranteed_amount: form.guaranteed_amount ? Number(form.guaranteed_amount) : null,
    expected_monthly_sales: form.expected_monthly_sales ? Number(form.expected_monthly_sales) : null,
    manual_monthly_revenue: form.manual_monthly_revenue ? Number(form.manual_monthly_revenue) : null,
    decoration_days: Number(form.decoration_days || 0),
    vacancy_days: Number(form.vacancy_days || 0),
  }), [candidate, form]);

  const submit = async () => {
    if (!candidate) return;
    await createOpportunity.mutateAsync({
      source_type: "MANUAL",
      store_id: candidate.store_id ?? null,
      floor_id: candidate.floor_id ?? null,
      unit_id: candidate.unit_id,
      unit_code: candidate.unit_code ?? null,
      unit_area: candidate.unit_area ?? null,
      current_brand: candidate.current_brand ?? null,
      current_contract_id: candidate.current_contract_id ?? null,
      current_annual_revenue: Number(candidate.period_revenue ?? 0),
      target_category: form.target_category || null,
      target_brand: form.target_brand || null,
      expected_sign_date: form.expected_sign_date || null,
      remark: form.remark || null,
      calculation: calculationInput,
    });
    toast({ title: "招商机会已创建" });
  };

  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle>合同测算</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {!candidate ? <div className="py-8 text-center text-sm text-muted-foreground">先选择一个候选铺位</div> : null}
        <div className="grid grid-cols-2 gap-3">
          <Field label="目标业态" value={form.target_category} onChange={(v) => setForm({ ...form, target_category: v })} />
          <Field label="目标品牌" value={form.target_brand} onChange={(v) => setForm({ ...form, target_brand: v })} />
        </div>
        <Label>合作模式</Label>
        <Select value={form.cooperation_mode} onValueChange={(v) => setForm({ ...form, cooperation_mode: v })}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="LEASE">租赁</SelectItem>
            <SelectItem value="JOINT_OPERATION">联营</SelectItem>
            <SelectItem value="OTHER">其他</SelectItem>
          </SelectContent>
        </Select>
        <div className="grid grid-cols-2 gap-3">
          <Field label="月租金" value={form.monthly_rent} onChange={(v) => setForm({ ...form, monthly_rent: v })} />
          <Field label="租金单价" value={form.rent_unit_price} onChange={(v) => setForm({ ...form, rent_unit_price: v })} />
          <Field label="扣点" value={form.commission_rate} onChange={(v) => setForm({ ...form, commission_rate: v })} />
          <Field label="保底金额" value={form.guaranteed_amount} onChange={(v) => setForm({ ...form, guaranteed_amount: v })} />
          <Field label="预计月销售额" value={form.expected_monthly_sales} onChange={(v) => setForm({ ...form, expected_monthly_sales: v })} />
          <Field label="手填月收益" value={form.manual_monthly_revenue} onChange={(v) => setForm({ ...form, manual_monthly_revenue: v })} />
          <Field label="装修期天数" value={form.decoration_days} onChange={(v) => setForm({ ...form, decoration_days: v })} />
          <Field label="空置期天数" value={form.vacancy_days} onChange={(v) => setForm({ ...form, vacancy_days: v })} />
        </div>
        <Field label="预计签约日期" type="date" value={form.expected_sign_date} onChange={(v) => setForm({ ...form, expected_sign_date: v })} />
        <Textarea placeholder="备注" value={form.remark} onChange={(e) => setForm({ ...form, remark: e.target.value })} />
        <div className="flex gap-2">
          <Button variant="outline" disabled={!candidate || preview.isPending} onClick={() => preview.mutate(calculationInput)}>
            {preview.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            预览测算
          </Button>
          <Button disabled={!candidate || createOpportunity.isPending} onClick={submit}>创建机会</Button>
        </div>
        {preview.data ? (
          <div className="rounded-md border bg-slate-50 p-3 text-sm">
            年收益 {money(preview.data.estimated_annual_revenue)}，提升 {money(preview.data.estimated_lift_amount)}，有效月数 {preview.data.effective_months}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Input type={type} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
```

- [ ] **Step 5: Add floor planning and pool sections**

Append:

```tsx
function FloorPlanningSection() {
  return (
    <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <Card className="rounded-md">
        <CardHeader><CardTitle>规划范围</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Field label="规划名称" value="" onChange={() => {}} />
          <Field label="门店编码" value="" onChange={() => {}} />
          <Field label="楼层ID，多个用逗号分隔" value="" onChange={() => {}} />
          <Textarea placeholder="规划目标，例如降低空置、引入运动潮流业态" />
          <Button className="w-full" disabled>整层项目创建将在下一任务接入</Button>
        </CardContent>
      </Card>
      <Card className="rounded-md">
        <CardHeader><CardTitle>整层测算汇总</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          第一版先通过“铺位补位”创建机会，再在机会池中汇总；项目创建接口已预留。
        </CardContent>
      </Card>
    </div>
  );
}

function OpportunityPool({ opportunities, loading, compact = false }: { opportunities: MerchantOpportunity[]; loading: boolean; compact?: boolean }) {
  return (
    <Card className="rounded-md">
      <CardHeader><CardTitle>{compact ? "最近机会" : "招商机会池"}</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>铺位</TableHead>
              <TableHead>目标</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>优先级</TableHead>
              <TableHead className="text-right">预计年收益</TableHead>
              <TableHead className="text-right">提升</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">加载中</TableCell></TableRow>
            ) : opportunities.length ? opportunities.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="font-medium">{row.unit_code || row.unit_id || "—"}</TableCell>
                <TableCell>{[row.target_category, row.target_brand].filter(Boolean).join(" / ") || "—"}</TableCell>
                <TableCell><Badge variant="secondary">{statusText[row.status] || row.status}</Badge></TableCell>
                <TableCell>{row.priority}</TableCell>
                <TableCell className="text-right">{money(row.estimated_annual_revenue)}</TableCell>
                <TableCell className="text-right">{money(row.estimated_lift_amount)}</TableCell>
              </TableRow>
            )) : (
              <TableRow><TableCell colSpan={6} className="py-8 text-center text-muted-foreground">暂无招商机会</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 6: Run frontend build**

Run:

```bash
npm run build --prefix client
```

Expected: build succeeds. If TypeScript complains about missing React namespace for `React.ReactNode`, add `import type { ReactNode } from "react";` and change `React.ReactNode` to `ReactNode`.

- [ ] **Step 7: Commit**

```bash
git add client/src/pages/merchant-planning.tsx
git commit -m "feat: add merchant planning page"
```

## Task 6: Revenue Map Entry Point

**Files:**
- Modify: `client/src/pages/revenue-map.tsx`

- [ ] **Step 1: Add module navigation prop if needed**

If `RevenueMapPage` cannot access module switching, update `main-dashboard.tsx` case to pass a callback:

```tsx
case "revenue-map":
  return <RevenueMapPage onOpenMerchantPlanning={() => void handleModuleChange("merchant-planning")} />;
```

Then update `RevenueMapPage` signature:

```tsx
export default function RevenueMapPage({ onOpenMerchantPlanning }: { onOpenMerchantPlanning?: () => void }) {
```

- [ ] **Step 2: Add selected-unit action**

In the selected unit detail panel of `client/src/pages/revenue-map.tsx`, add a button near existing selected-unit actions:

```tsx
<Button
  type="button"
  className="w-full"
  onClick={() => {
    const params = new URLSearchParams();
    if (selectedUnit?.unit_id) params.set("unit_id", String(selectedUnit.unit_id));
    if (selectedUnit?.unit_code) params.set("unit_code", selectedUnit.unit_code);
    if (floorId) params.set("floor_id", String(floorId));
    if (storeFilter) params.set("store_id", storeFilter);
    params.set("source", "revenue-map");
    window.history.replaceState(null, "", `${window.location.pathname}?module=merchant-planning&${params.toString()}`);
    onOpenMerchantPlanning?.();
  }}
  disabled={!selectedUnit}
>
  创建招商机会
</Button>
```

- [ ] **Step 3: Read URL context in merchant planning page**

In `client/src/pages/merchant-planning.tsx`, inside `MerchantPlanningPage`, initialize selected tab:

```tsx
const initialTab = new URLSearchParams(window.location.search).get("source") === "revenue-map" ? "single" : "overview";
const [tab, setTab] = useState(initialTab);
```

- [ ] **Step 4: Run frontend build**

Run:

```bash
npm run build --prefix client
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add client/src/pages/revenue-map.tsx client/src/pages/main-dashboard.tsx client/src/pages/merchant-planning.tsx
git commit -m "feat: link revenue map to merchant planning"
```

## Task 7: End-To-End Verification

**Files:**
- No new files unless fixing issues found by verification.

- [ ] **Step 1: Run backend syntax verification**

Run:

```bash
python3 -m py_compile python_app/routers/merchant_planning.py python_app/main.py python_app/models/models.py python_app/schemas/schemas.py python_app/routers/authz.py
```

Expected: exits `0`.

- [ ] **Step 2: Run frontend build**

Run:

```bash
npm run build --prefix client
```

Expected: build succeeds.

- [ ] **Step 3: Start backend**

Run:

```bash
.venv/bin/uvicorn main:app --app-dir python_app --host 0.0.0.0 --port 8000 --reload
```

Expected: server starts on port `8000`.

- [ ] **Step 4: Start frontend**

Run:

```bash
npm run dev --prefix client -- --host 0.0.0.0 --port 5174
```

Expected: Vite serves on `http://localhost:5174`.

- [ ] **Step 5: Browser smoke test**

Open `http://localhost:5174`, log in if needed, then verify:

- Left navigation shows `招商规划` for an authorized user.
- 招商规划 opens without blank screen.
- 规划总览 loads cards.
- 铺位补位 can load candidates.
- Selecting a candidate enables the contract calculation form.
- Preview calculation returns expected values for lease and joint-operation inputs.
- Creating an opportunity adds it to 招商机会池.
- 收益地图 selected unit shows `创建招商机会` and can switch to 招商规划.

- [ ] **Step 6: Commit any verification fixes**

If verification required fixes:

```bash
git add <fixed-files>
git commit -m "fix: stabilize merchant planning mvp"
```

If no fixes were needed, do not create an empty commit.

## Self-Review

- Spec coverage:
  - Independent 招商规划 module: Tasks 4 and 5.
  - Dual planning modes: Task 5.
  - Contract-condition calculation: Tasks 2 and 5.
  - Opportunity workflow and follow-ups: Tasks 1, 3, and 5.
  - Revenue-map linkage: Task 6.
  - Permissions: Tasks 3 and 4.
  - Verification: Task 7.
- Placeholder scan:
  - The plan intentionally contains `TODO` only as the opportunity status enum meaning 待招商. It does not contain unfinished placeholders.
- Type consistency:
  - Backend enum values match frontend union types: `TODO`, `NEGOTIATING`, `SIGNED`, `ABANDONED`; `LEASE`, `JOINT_OPERATION`, `OTHER`.
  - API route prefix is consistently `/api/merchant-planning`.
  - Module id is consistently `merchant-planning`.
