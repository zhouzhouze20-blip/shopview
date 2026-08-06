from __future__ import annotations

from datetime import datetime
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
    _od0002_scope_description,
    _od0002_store_id_for_code,
    _scope_explicitly_rejects_store,
)
from services.od0002_report import TrustedScopeSql
from services.store_other_business_income_excel import (
    build_store_other_business_income_workbook_file,
)
from services.store_other_business_income_report import (
    SUPPORTED_STORE_CODES,
    load_store_other_business_income_report,
)


router = APIRouter(prefix="/api/sales", tags=["sales"])
PERMISSION_CODE = "sales.store_other_business_income.view"


def _load_report_for_request(
    *,
    financial_year: int,
    end_period: int,
    store_id: str | None,
    db: Session,
    current_user: User,
):
    selected_store = (store_id or "").strip() or None
    if selected_store and selected_store not in SUPPORTED_STORE_CODES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该报表仅支持购物中心、百货大楼、新世纪和半山")

    require_permission(db, current_user, PERMISSION_CODE)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    has_explicit_store_scope = bool(
        scope.deny.get("store", set())
        or (not scope.all_access and scope.allow.get("store", set()))
    )
    selected_scope_store_id = (
        _od0002_store_id_for_code(db, selected_store)
        if selected_store and has_explicit_store_scope
        else None
    )
    if selected_store and has_explicit_store_scope and (
        selected_scope_store_id is None
        or _scope_explicitly_rejects_store(scope, selected_scope_store_id)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无该门店数据权限")

    scope_params: dict[str, object] = {}
    scope_filter_sql = _business_scope_filter_sql(
        scope,
        scope_params,
        prefix="store_other_business_income",
        store_expr="st.store_id::text",
        department_code_expr="f.valuecode",
        department_name_expr="f.valuename",
    )
    report = load_store_other_business_income_report(
        db,
        TrustedScopeSql(scope_filter_sql),
        scope_params,
        financial_year=financial_year,
        end_period=end_period,
        selected_store=selected_store,
    )
    report["scope_description"] = _od0002_scope_description(scope)
    return report


@router.get("/reports/store-other-business-income")
async def store_other_business_income_report(
    financial_year: int = Query(..., ge=2000, le=2100),
    end_period: int = Query(..., ge=1, le=12),
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _load_report_for_request(
        financial_year=financial_year,
        end_period=end_period,
        store_id=store_id,
        db=db,
        current_user=current_user,
    )


@router.get("/reports/store-other-business-income/stores")
async def store_other_business_income_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = _load_report_for_request(
        financial_year=datetime.now().year,
        end_period=12,
        store_id=None,
        db=db,
        current_user=current_user,
    )
    return [
        {
            "store_id": _od0002_store_id_for_code(db, row["store_code"]),
            "store_code": row["store_code"],
            "store_name": row["store_name"],
        }
        for row in report["store_rows"]
        if row["row_type"] == "grand_total"
    ]


@router.get("/reports/store-other-business-income/export")
async def export_store_other_business_income_report(
    financial_year: int = Query(..., ge=2000, le=2100),
    end_period: int = Query(..., ge=1, le=12),
    store_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = _load_report_for_request(
        financial_year=financial_year,
        end_period=end_period,
        store_id=store_id,
        db=db,
        current_user=current_user,
    )
    workbook_file = build_store_other_business_income_workbook_file(report)
    filename = f"门店其他业务收入_{financial_year}年01-{end_period:02d}期.xlsx"
    if store_id:
        selected_total = next(
            (row for row in report["store_rows"] if row["row_type"] == "grand_total"),
            None,
        )
        if selected_total:
            filename = f"{selected_total['store_name']}{filename}"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        "X-Report-Generated-At": datetime.now().isoformat(timespec="seconds"),
    }
    return StreamingResponse(
        workbook_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
