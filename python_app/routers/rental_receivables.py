"""Rental accounts-receivable report backed by the local headquarters ODS."""

import logging
from datetime import date
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from services.rental_receivables import (
    BusinessScopeFilter,
    OdsUnavailableError,
    ReceivableFilters,
    ReceivableNotFoundError,
    query_rental_receivable_options,
    query_rental_receivable_detail,
    query_rental_receivable_expense_export,
    query_rental_receivables,
    query_mobile_rental_receivable_drilldown,
)
from services.rental_receivables_excel import build_rental_receivable_expense_workbook_file


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rental-receivables", tags=["rental-receivables"])


def _load_rental_scope(db: Session, current_user: User) -> BusinessScopeFilter:
    business_scope = load_business_scope(db, current_user, fallback_resource_code="settlement")
    return BusinessScopeFilter(
        all_access=business_scope.all_access,
        allow={key: frozenset(values) for key, values in business_scope.allow.items()},
        deny={key: frozenset(values) for key, values in business_scope.deny.items()},
    )


def _require_mobile_rental_access(db: Session, current_user: User) -> None:
    require_permission(db, current_user, "mobile.rental_receivables.view")
    require_permission(db, current_user, "settlement.view")


def _stream_and_close(file_obj):
    try:
        while chunk := file_obj.read(64 * 1024):
            yield chunk
    finally:
        file_obj.close()


@router.get("/options")
async def list_rental_receivable_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "settlement.view")
    try:
        return query_rental_receivable_options(db, _load_rental_scope(db, current_user))
    except OdsUnavailableError as exc:
        logger.error("租赁应收未收筛选项 ODS 不可用: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="总部库 ODS 尚未同步完成或本地表不可用，请联系系统管理员",
        ) from exc


@router.get("/mobile/drilldown")
async def mobile_rental_receivable_drilldown(
    level: Literal["store", "department", "group"] = Query(...),
    settle_from: date = Query(..., description="结算截止日起"),
    settle_to: date = Query(..., description="结算截止日止"),
    mkt: str | None = Query(None, max_length=20, description="上级门店编码"),
    department_code: str | None = Query(None, max_length=20, description="上级部门编码"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_mobile_rental_access(db, current_user)
    try:
        return query_mobile_rental_receivable_drilldown(
            db,
            level=level,
            settle_from=settle_from,
            settle_to=settle_to,
            scope=_load_rental_scope(db, current_user),
            mkt=mkt,
            department_code=department_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OdsUnavailableError as exc:
        logger.error("手机端租赁应收未收钻取 ODS 不可用: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="总部库 ODS 尚未同步完成或本地表不可用，请联系系统管理员",
        ) from exc


@router.get("/mobile/bills/{bill_no}/details")
async def get_mobile_rental_receivable_detail(
    bill_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_mobile_rental_access(db, current_user)
    try:
        return query_rental_receivable_detail(db, bill_no, _load_rental_scope(db, current_user))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ReceivableNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OdsUnavailableError as exc:
        logger.error("手机端租赁应收未收组成明细 ODS 不可用: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="总部库 ODS 明细尚未同步完成或本地表不可用，请联系系统管理员",
        ) from exc


@router.get("/mobile/bills")
async def list_mobile_rental_receivable_bills(
    settle_from: date = Query(..., description="结算截止日起"),
    settle_to: date = Query(..., description="结算截止日止"),
    mkt: str = Query(..., max_length=20, description="门店编码"),
    department_code: str = Query(..., max_length=20, description="部门编码"),
    group_code: str = Query(..., max_length=40, description="柜组编码"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_mobile_rental_access(db, current_user)
    try:
        return query_rental_receivables(
            db,
            ReceivableFilters(
                settle_from=settle_from,
                settle_to=settle_to,
                page=page,
                page_size=page_size,
                mkt=mkt,
                department_code=department_code,
                group_code=group_code,
            ),
            _load_rental_scope(db, current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OdsUnavailableError as exc:
        logger.error("手机端租赁应收未收账单 ODS 不可用: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="总部库 ODS 尚未同步完成或本地表不可用，请联系系统管理员",
        ) from exc


@router.get("/export/expense-details")
async def export_rental_receivable_expense_details(
    settle_from: date = Query(..., description="结算截止日起"),
    settle_to: date = Query(..., description="结算截止日止"),
    mkt: str | None = Query(None, max_length=20, description="门店编码"),
    department_code: str | None = Query(None, max_length=20, description="部门编码"),
    group_prefix: str | None = Query(None, max_length=40, description="柜组编码开头"),
    keyword: str | None = Query(None, max_length=80, description="单号、供应商、合同或柜组"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "settlement.view")
    filters = ReceivableFilters(
        settle_from=settle_from,
        settle_to=settle_to,
        mkt=mkt,
        department_code=department_code,
        group_prefix=group_prefix,
        keyword=keyword,
    )
    try:
        report = query_rental_receivable_expense_export(
            db,
            filters,
            _load_rental_scope(db, current_user),
        )
        workbook_file = await run_in_threadpool(
            build_rental_receivable_expense_workbook_file,
            report,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OdsUnavailableError as exc:
        logger.error("租赁应收未收费用明细导出 ODS 不可用: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="总部库 ODS 费用明细尚未同步完成或本地表不可用，请联系系统管理员",
        ) from exc

    filename = f"租赁应收未收_费用明细_{settle_from.isoformat()}_{settle_to.isoformat()}.xlsx"
    return StreamingResponse(
        _stream_and_close(workbook_file),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        background=BackgroundTask(workbook_file.close),
    )


@router.get("/{bill_no}/details")
async def get_rental_receivable_detail(
    bill_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "settlement.view")
    try:
        return query_rental_receivable_detail(
            db,
            bill_no,
            _load_rental_scope(db, current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ReceivableNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OdsUnavailableError as exc:
        logger.error("租赁应收未收组成明细 ODS 不可用: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="总部库 ODS 明细尚未同步完成或本地表不可用，请联系系统管理员",
        ) from exc


@router.get("")
async def list_rental_receivables(
    settle_from: date = Query(..., description="结算截止日起"),
    settle_to: date = Query(..., description="结算截止日止"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    mkt: str | None = Query(None, max_length=20, description="门店编码"),
    department_code: str | None = Query(None, max_length=20, description="部门编码"),
    group_prefix: str | None = Query(None, max_length=40, description="柜组编码开头"),
    keyword: str | None = Query(None, max_length=80, description="单号、供应商、合同或柜组"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, "settlement.view")
    if settle_from > settle_to:
        raise HTTPException(status_code=422, detail="结算截止日起不能晚于止日期")

    scope = _load_rental_scope(db, current_user)
    filters = ReceivableFilters(
        settle_from=settle_from,
        settle_to=settle_to,
        page=page,
        page_size=page_size,
        mkt=mkt,
        department_code=department_code,
        group_prefix=group_prefix,
        keyword=keyword,
    )
    try:
        return query_rental_receivables(db, filters, scope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OdsUnavailableError as exc:
        logger.error("租赁应收未收本地 ODS 不可用: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="总部库 ODS 尚未同步完成或本地表不可用，请联系系统管理员",
        ) from exc
