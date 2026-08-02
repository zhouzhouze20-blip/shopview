from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from routers.sales import (
    _business_scope_filter_sql,
    _load_report_department_options,
    _load_report_store_options,
    _od0002_scope_description,
    _od0002_store_id_for_code,
    _scope_explicitly_rejects_store,
)
from services.non_rental_monthly_revenue_excel import (
    build_non_rental_monthly_revenue_workbook_file,
)
from services.non_rental_monthly_revenue_report import (
    load_non_rental_monthly_revenue_report,
)
from services.od0002_report import TrustedScopeSql


router = APIRouter(prefix="/api/sales", tags=["sales"])
PERMISSION_CODE = "sales.non_rental_monthly_revenue.view"


def _load_report_for_request(
    *,
    financial_year: int,
    store_id: str,
    department_id: str | None,
    db: Session,
    current_user: User,
) -> tuple[dict[str, Any], str]:
    selected_store = store_id.strip()
    selected_department = (department_id or "").strip() or None
    if not selected_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择门店",
        )

    require_permission(db, current_user, PERMISSION_CODE)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_explicit_store_scope = bool(
        scope.deny.get("store", set())
        or (not scope.all_access and scope.allow.get("store", set()))
    )
    selected_scope_store_id = (
        _od0002_store_id_for_code(db, selected_store)
        if has_explicit_store_scope
        else None
    )
    if has_explicit_store_scope and (
        selected_scope_store_id is None
        or _scope_explicitly_rejects_store(scope, selected_scope_store_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无该门店数据权限",
        )

    scope_params: dict[str, Any] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="non_rental_monthly_revenue",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    report = load_non_rental_monthly_revenue_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        financial_year=financial_year,
        selected_store=selected_store,
        selected_department=selected_department,
    )
    scope_description = _od0002_scope_description(scope)
    report["scope_description"] = scope_description
    return report, scope_description


@router.get("/reports/non-rental-monthly-revenue/stores")
async def non_rental_monthly_revenue_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_store_options(
        db,
        current_user,
        permission_code=PERMISSION_CODE,
        prefix="non_rental_monthly_revenue_stores",
    )


@router.get("/reports/non-rental-monthly-revenue/departments")
async def non_rental_monthly_revenue_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_department_options(
        db,
        current_user,
        store_id,
        permission_code=PERMISSION_CODE,
        prefix="non_rental_monthly_revenue_departments",
    )


@router.get("/reports/non-rental-monthly-revenue")
async def non_rental_monthly_revenue_report(
    financial_year: int = Query(..., ge=2000, le=2100),
    store_id: str = Query(..., min_length=1),
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report, _ = _load_report_for_request(
        financial_year=financial_year,
        store_id=store_id,
        department_id=department_id,
        db=db,
        current_user=current_user,
    )
    return report


@router.get("/reports/non-rental-monthly-revenue/export")
async def export_non_rental_monthly_revenue_report(
    financial_year: int = Query(..., ge=2000, le=2100),
    store_id: str = Query(..., min_length=1),
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report, _ = _load_report_for_request(
        financial_year=financial_year,
        store_id=store_id,
        department_id=department_id,
        db=db,
        current_user=current_user,
    )
    workbook_file = build_non_rental_monthly_revenue_workbook_file(report)
    store_label = report.get("grand_total", {}).get("store_name") or store_id
    filename = f"{store_label}非租赁品牌月度收益_{financial_year}年.xlsx"
    encoded_filename = quote(filename)
    headers = {
        "Content-Disposition": (
            f"attachment; filename*=UTF-8''{encoded_filename}"
        ),
        "X-Report-Generated-At": datetime.now().isoformat(timespec="seconds"),
    }
    return StreamingResponse(
        workbook_file,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers=headers,
    )
