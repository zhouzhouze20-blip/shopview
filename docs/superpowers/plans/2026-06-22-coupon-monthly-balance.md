# Coupon Monthly Balance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a ShopView coupon monthly balance workflow where confirmed voucher matches create coupon revenue movements, finance manually records NC carryovers, and monthly balances can be rebuilt and confirmed.

**Architecture:** Add three PostgreSQL tables with Alembic, implement focused helper functions and endpoints inside `python_app/routers/activity_analysis.py`, then add a compact React page beside the existing voucher matching page. The backend owns all monthly calculation rules and confirmation guards; the frontend only triggers rebuilds, records NC carryovers, and displays status.

**Tech Stack:** FastAPI, SQLAlchemy text SQL, Alembic migrations, PostgreSQL, React, TanStack Query, TypeScript, shadcn-style UI components.

---

### Task 1: Database Tables

**Files:**
- Create: `python_app/alembic/versions/c3d4e5f6a7b8_create_coupon_monthly_balance_tables.py`

- [ ] **Step 1: Create migration with three tables**

Create a migration with:

```python
revision = "c3d4e5f6a7b8"
down_revision = "c2d3e4f5a6b7"
```

The migration must create:

- `activity_coupon_revenue_movement`
- `activity_coupon_nc_carryover`
- `activity_coupon_monthly_balance`

Use `CREATE TABLE IF NOT EXISTS`, comments, and indexes for `(period_month, market_code, coupon_type)`.

- [ ] **Step 2: Validate migration syntax**

Run:

```bash
python -m py_compile python_app/alembic/versions/c3d4e5f6a7b8_create_coupon_monthly_balance_tables.py
```

Expected: command exits with code 0.

### Task 2: Backend Schemas And Helpers

**Files:**
- Modify: `python_app/routers/activity_analysis.py`

- [ ] **Step 1: Add request models**

Add Pydantic models near existing voucher match models:

```python
class CouponRevenueMovementRebuildRequest(BaseModel):
    period_month: str
    market_code: str | None = None


class CouponMonthlyBalanceQuery(BaseModel):
    period_month: str
    market_code: str | None = None
    coupon_type: str | None = None
    status: str | None = None


class CouponNcCarryoverRequest(BaseModel):
    period_month: str
    market_code: str
    coupon_type: str
    coupon_name: str | None = None
    nc_voucher_no: str
    carryover_amount: float
    carryover_date: str | None = None
    remark: str | None = None


class CouponMonthlyBalanceConfirmRequest(BaseModel):
    period_month: str
    market_code: str | None = None
```

- [ ] **Step 2: Add validation helpers**

Add helpers:

```python
def _normalize_period_month(period_month: str) -> str:
    value = period_month.strip()
    if len(value) == 7 and value[4] == "-":
        return value
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_month 必须是 YYYY-MM")


def _month_bounds(period_month: str) -> tuple[str, str]:
    year = int(period_month[:4])
    month = int(period_month[5:7])
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month + 1:02d}-01"
    return start_date, end_date


def _ensure_coupon_monthly_tables(db: Session) -> None:
    required = [
        "activity_coupon_revenue_movement",
        "activity_coupon_nc_carryover",
        "activity_coupon_monthly_balance",
    ]
    missing = [name for name in required if not _table_exists(db, name)]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"卡券月结表尚未创建: {', '.join(missing)}")
```

### Task 3: Backend Rebuild And Carryover APIs

**Files:**
- Modify: `python_app/routers/activity_analysis.py`

- [ ] **Step 1: Implement movement rebuild endpoint**

Add `POST /coupon-revenue-movements/rebuild`.

Rules:

- Reject rebuild when the target month/store has confirmed monthly rows.
- Upsert movements from confirmed `activity_coupon_voucher_match`.
- Join `activity_coupon_revenue_rate_snapshot` by business date, market code, coupon type.
- Set `rate_status` to `OK` or `MISSING_RATE`.

- [ ] **Step 2: Implement NC carryover endpoint**

Add `POST /coupon-nc-carryovers`.

Rules:

- Reject if matching monthly balance is confirmed.
- Insert one carryover row.
- Return inserted row count.

- [ ] **Step 3: Run backend syntax check**

Run:

```bash
python -m py_compile python_app/routers/activity_analysis.py
```

Expected: command exits with code 0.

### Task 4: Backend Monthly Balance APIs

**Files:**
- Modify: `python_app/routers/activity_analysis.py`

- [ ] **Step 1: Implement monthly balance rebuild endpoint**

Add `POST /coupon-monthly-balances/rebuild`.

Rules:

- Reject rebuild for confirmed rows.
- Load opening balance from previous period `activity_coupon_monthly_balance`.
- Aggregate `CREDIT_BUY` as increase and `DEBIT_USE` as decrease.
- Aggregate manual NC carryovers.
- Upsert `DRAFT` monthly balance rows.

- [ ] **Step 2: Implement monthly balance query endpoint**

Add `GET /coupon-monthly-balances`.

Return rows ordered by month, store, coupon type.

- [ ] **Step 3: Implement confirm endpoint**

Add `POST /coupon-monthly-balances/confirm`.

Rules:

- Reject if no draft rows exist.
- Reject if any row has `missing_rate_count > 0`.
- Mark selected draft rows as `CONFIRMED`.

### Task 5: Frontend Page And Navigation

**Files:**
- Create: `client/src/pages/activity-analysis/coupon-monthly-balance.tsx`
- Modify: `client/src/pages/main-dashboard.tsx`
- Modify: `client/src/components/navigation-sidebar.tsx`
- Modify: `client/src/lib/module-permissions.ts`

- [ ] **Step 1: Build page**

Create a page with:

- Month input.
- Store select.
- Refresh movements button.
- Rebuild balance button.
- NC carryover dialog.
- Confirm month button.
- Balance table.

- [ ] **Step 2: Register module**

Add module id `coupon-monthly-balance`, label `卡券月结`, permission `activity_analysis.view`, sidebar item under activity analysis, and render branch in `main-dashboard.tsx`.

- [ ] **Step 3: Run frontend type check**

Run:

```bash
npm run check
```

Expected: TypeScript exits with code 0.

### Task 6: Verification

**Files:**
- Verify changed files only.

- [ ] **Step 1: Backend syntax**

Run:

```bash
python -m py_compile python_app/routers/activity_analysis.py python_app/alembic/versions/c3d4e5f6a7b8_create_coupon_monthly_balance_tables.py
```

- [ ] **Step 2: Frontend build/type check**

Run:

```bash
npm run check
```

- [ ] **Step 3: Review diff**

Run:

```bash
git diff --stat
git diff -- python_app/routers/activity_analysis.py client/src/pages/activity-analysis/coupon-monthly-balance.tsx
```

Confirm the diff only contains the coupon monthly balance feature.
