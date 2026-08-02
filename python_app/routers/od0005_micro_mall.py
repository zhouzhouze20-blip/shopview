from __future__ import annotations

from datetime import date, datetime
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
from services.od0002_report import TrustedScopeSql
from services.od0005_micro_mall_excel import build_od0005_workbook_file
from services.od0005_micro_mall_report import MICRO_MALL_CASHIER_BY_STORE, load_od0005_report


router = APIRouter(prefix="/api/sales", tags=["sales"])
PERMISSION_CODE = "sales.od0005.view"


def _load_report_for_request(
    *,
    start_date: date,
    end_date: date,
    store_id: str,
    department_id: str | None,
    db: Session,
    current_user: User,
) -> dict[str, Any]:
    selected_store = str(store_id or "").strip()
    selected_department = str(department_id or "").strip() or None
    if not selected_store:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择门店")
    if selected_store not in MICRO_MALL_CASHIER_BY_STORE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OD0005仅支持购物中心、百货大楼和新世纪三店",
        )
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="结束日期不能早于开始日期",
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
        prefix="od0005_micro_mall",
        store_expr="st.store_id::text",
        department_code_expr="dept.mfcode",
        department_name_expr="dept.mfcname",
        group_expr="mf.mfcode",
        category_code_expr="ac.category_code",
        category_name_expr="ac.category_name",
        floor_expr="mf.mflc",
    )
    report = load_od0005_report(
        db,
        start_date=start_date,
        end_date=end_date,
        selected_store=selected_store,
        selected_department=selected_department,
        scope_filter_sql=TrustedScopeSql(scope_filter_sql),
        scope_params=scope_params,
    )
    report["scope_description"] = _od0002_scope_description(scope)
    return report


@router.get("/reports/od0005/stores")
async def od0005_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stores = _load_report_store_options(
        db,
        current_user,
        permission_code=PERMISSION_CODE,
        prefix="od0005_stores",
    )
    return [
        store
        for store in stores
        if str(store.get("store_code") or "").strip() in MICRO_MALL_CASHIER_BY_STORE
    ]


@router.get("/reports/od0005/departments")
async def od0005_departments(
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_department_options(
        db,
        current_user,
        store_id,
        permission_code=PERMISSION_CODE,
        prefix="od0005_departments",
    )


@router.get("/reports/od0005")
async def od0005_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    store_id: str = Query(..., min_length=1),
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_for_request(
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
        department_id=department_id,
        db=db,
        current_user=current_user,
    )


@router.get("/reports/od0005/export")
async def export_od0005_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    store_id: str = Query(..., min_length=1),
    department_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = _load_report_for_request(
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
        department_id=department_id,
        db=db,
        current_user=current_user,
    )
    workbook_file = build_od0005_workbook_file(report)
    filename = (
        f"{report['store_name']}OD0005微商城品牌销售统计_"
        f"{start_date.isoformat()}_{end_date.isoformat()}.xlsx"
    )
    headers = {
        "Content-Disposition": (
            f"attachment; filename*=UTF-8''{quote(filename)}"
        ),
        "X-Report-Generated-At": datetime.now().isoformat(timespec="seconds"),
    }
    return StreamingResponse(
        workbook_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
