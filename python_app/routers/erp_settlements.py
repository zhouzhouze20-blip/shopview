"""
ERP 联营结算单 API

数据源：supsettlehead、paybatch（表头单据号 pbbillno，关联 pbjsno=sshbillno）、supsettledettot、
可选 supsettledet（与 paybatch 按单据号关联生成结算单销售）、supsetcharge（见 Alembic f8e9d0c1b2a3）。

说明：列表与明细需登录；功能权限 settlement.view；数据范围按 business_scope 的查询业务范围
过滤（部门、柜组及排除范围）。管理员不受业务范围限制。
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import (
    is_admin,
    load_business_scope,
    require_permission,
    scope_allows_business,
)
from services import erp_settlement_service as svc
from services import joint_payment_confirmation as payment_confirmation_svc


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/erp-settlements", tags=["erp-settlements"])


class JointSettlementListResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class JointSettlementDetailResponse(BaseModel):
    head: dict
    header_display: dict | None = Field(
        default=None,
        description="ERP 付款头展示（suppayhead + paybatch 聚合 + 维表），对齐原 Oracle 结算单表头字段",
    )
    charges_by_payment_bill: list[dict] = Field(
        default_factory=list,
        description="按付款单号 suppayhead.sphbillno = supsetcharge.sscpaybillno 汇总前的费用行",
    )
    paybatch: list[dict] = Field(
        default_factory=list,
        description="付款批次 paybatch：pbjsno=结算单号，pbbillno=单据号（表头单据号）",
    )
    paybatch_sales: list[dict] = Field(
        default_factory=list,
        description="结算单销售：paybatch 左联 supsettledet 按单据号聚合（考核类型/数量/税率）",
    )
    lines: list[dict] = Field(default_factory=list)
    charges: list[dict] = Field(default_factory=list)


class JointPaymentSummary(BaseModel):
    total_generated_count: int = 0
    total_generated_supplier_count: int = 0
    total_generated_amount: float = 0
    supplier_confirmation_available: bool = False
    supplier_confirmed_count: int | None = None
    supplier_confirmed_supplier_count: int | None = None
    supplier_confirmed_amount: float | None = None
    supplier_unreported_count: int | None = None
    supplier_unreported_supplier_count: int | None = None
    supplier_unreported_amount: float | None = None
    generated_count: int = 0
    generated_supplier_count: int = 0
    generated_amount: float = 0
    audited_count: int = 0
    audited_supplier_count: int = 0
    audited_amount: float = 0
    current_financial_month_audited_amount: float = 0
    current_financial_month_start: str | None = None
    current_financial_month_end: str | None = None
    latest_status_date: str | None = None


class JointPaymentListResponse(BaseModel):
    summary: JointPaymentSummary = Field(default_factory=JointPaymentSummary)
    items: list[dict] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class JointPaymentDetailResponse(BaseModel):
    head: dict
    lines: list[dict] = Field(default_factory=list)
    charges: list[dict] = Field(default_factory=list)


class JointPaymentDepartmentOptionsResponse(BaseModel):
    departments: list[dict] = Field(default_factory=list)


class MobileSupplierPaymentOptionsResponse(JointPaymentDepartmentOptionsResponse):
    stores: list[dict] = Field(default_factory=list)


def _joint_payment_scope(db: Session, current_user: User) -> payment_confirmation_svc.BusinessScope:
    scope = load_business_scope(db, current_user, fallback_resource_code="settlement")
    if is_admin(db, current_user) or scope.all_access:
        return payment_confirmation_svc.BusinessScope(all_access=True)
    return payment_confirmation_svc.BusinessScope(
        group_allow=frozenset(scope.allow.get("group", set())),
        group_deny=frozenset(scope.deny.get("group", set())),
        department_allow=frozenset(scope.allow.get("department", set())),
        department_deny=frozenset(scope.deny.get("department", set())),
    )


def _mobile_supplier_payment_scope(
    db: Session,
    current_user: User,
) -> payment_confirmation_svc.BusinessScope:
    """Use the same query business scope as the desktop joint-payment module."""
    return _joint_payment_scope(db, current_user)


@router.get("/mobile/supplier-payments", response_model=JointPaymentListResponse)
async def list_mobile_supplier_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    payment_status: str | None = Query(None, description="付款单状态：M 待审核、C 供应商已填报确认、Y 已审核、U 已生成未填报、P 已填报未审核、N 未填报（全部）"),
    date_from: date | None = Query(None, description="状态日期起；生成取录入日，已审核取审核日"),
    date_to: date | None = Query(None, description="状态日期止；生成取录入日，已审核取审核日"),
    supplier_code: str | None = Query(None, description="供应商编码精确匹配"),
    supplier_name: str | None = Query(None, description="供应商名称模糊匹配"),
    keyword: str | None = Query(None, description="兼容付款单号、结算单号和合同号搜索"),
    market: str | None = Query(None, description="门店编码精确匹配"),
    department_code: str | None = Query(None, description="部门编码"),
    financial_month: str | None = Query(None, description="付款单生成归属财务月 YYYY-MM；当月29—31日仍归当月"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手机端按当前账号查询业务范围查看联营供应商付款单。"""
    try:
        require_permission(db, current_user, "mobile.supplier_payments.view")
        normalized_status = (payment_status or "").strip().upper() or None
        if normalized_status not in {None, "M", "C", "Y", "U", "P", "N"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="付款单状态仅支持 M、C、Y、U、P 或 N")
        if financial_month is not None:
            try:
                payment_confirmation_svc.payment_generation_month_period(financial_month)
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="财务月格式应为有效的 YYYY-MM") from e
            if date_from or date_to:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="财务月不能与状态日期起止同时筛选")
        if date_from and date_to and date_from > date_to:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="开始日期不能晚于结束日期")
        result = payment_confirmation_svc.query_joint_payments(
            db,
            payment_confirmation_svc.JointPaymentFilters(
                page=page,
                page_size=page_size,
                status=normalized_status,
                date_from=date_from.isoformat() if date_from else None,
                date_to=date_to.isoformat() if date_to else None,
                supplier_code=supplier_code,
                supplier_name=supplier_name,
                keyword=keyword,
                market=market,
                market_exact=True,
                department_code=department_code,
                financial_month=financial_month,
                include_supplier_confirmation=True,
                include_banshan=True,
            ),
            _mobile_supplier_payment_scope(db, current_user),
        )
        return JointPaymentListResponse(**result)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    except SQLAlchemyError as e:
        logger.exception("手机端供应商付款单列表查询失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {e.__class__.__name__}",
        ) from e


@router.get("/mobile/supplier-payments/options", response_model=MobileSupplierPaymentOptionsResponse)
async def get_mobile_supplier_payment_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """仅返回当前账号查询业务范围内的门店和部门。"""
    try:
        require_permission(db, current_user, "mobile.supplier_payments.view")
        result = payment_confirmation_svc.query_mobile_supplier_payment_options(
            db, _mobile_supplier_payment_scope(db, current_user),
        )
        return MobileSupplierPaymentOptionsResponse(**result)
    except SQLAlchemyError as e:
        logger.exception("手机端供应商付款单筛选选项查询失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {e.__class__.__name__}",
        ) from e


@router.get(
    "/mobile/supplier-payments/{payment_bill_no}",
    response_model=JointPaymentDetailResponse,
)
async def get_mobile_supplier_payment_detail(
    payment_bill_no: str,
    department_code: str | None = Query(None, description="部门编码，与列表筛选一致"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手机端付款单头及当前账号可见的结算批次明细。"""
    try:
        require_permission(db, current_user, "mobile.supplier_payments.view")
        result = payment_confirmation_svc.get_joint_payment_detail(
            db,
            payment_bill_no,
            _mobile_supplier_payment_scope(db, current_user),
            department_code=department_code,
            include_banshan=True,
        )
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="付款单不存在或不在查询业务范围内")
        return JointPaymentDetailResponse(**result)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception("手机端供应商付款单明细查询失败 bill_no=%s", payment_bill_no)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {e.__class__.__name__}",
        ) from e


@router.get("/joint-payment-confirmation", response_model=JointPaymentListResponse)
async def list_joint_payment_confirmation(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    payment_status: str | None = Query(None, description="付款单状态：M 生成、Y 已审核"),
    date_from: date | None = Query(None, description="状态日期起；生成取录入日，已审核取审核日"),
    date_to: date | None = Query(None, description="状态日期止；生成取录入日，已审核取审核日"),
    market: str | None = Query(None, description="门店编码片段"),
    department_code: str | None = Query(None, description="部门编码"),
    group_prefix: str | None = Query(None, description="柜组编码前缀"),
    keyword: str | None = Query(None, description="付款单号、结算单号、合同号、供应商编码或名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """联营付款单生成/已审核数量、金额及分页明细。"""
    try:
        require_permission(db, current_user, "settlement.joint_payment_confirmation.view")
        normalized_status = (payment_status or "").strip().upper() or None
        if normalized_status not in {None, "M", "Y"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="付款单状态仅支持 M 或 Y")
        if date_from and date_to and date_from > date_to:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="开始日期不能晚于结束日期")
        result = payment_confirmation_svc.query_joint_payments(
            db,
            payment_confirmation_svc.JointPaymentFilters(
                page=page,
                page_size=page_size,
                status=normalized_status,
                date_from=date_from.isoformat() if date_from else None,
                date_to=date_to.isoformat() if date_to else None,
                market=market,
                department_code=department_code,
                group_prefix=group_prefix,
                keyword=keyword,
            ),
            _joint_payment_scope(db, current_user),
        )
        return JointPaymentListResponse(**result)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception("联营付款单确认列表查询失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {e.__class__.__name__}",
        ) from e


@router.get(
    "/joint-payment-confirmation/options",
    response_model=JointPaymentDepartmentOptionsResponse,
)
async def get_joint_payment_confirmation_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户部门数据范围内的联营付款单部门选项。"""
    try:
        require_permission(db, current_user, "settlement.joint_payment_confirmation.view")
        departments = payment_confirmation_svc.query_joint_payment_department_options(
            db,
            _joint_payment_scope(db, current_user),
        )
        return JointPaymentDepartmentOptionsResponse(departments=departments)
    except SQLAlchemyError as e:
        logger.exception("联营付款单部门选项查询失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {e.__class__.__name__}",
        ) from e


@router.get(
    "/joint-payment-confirmation/{payment_bill_no}",
    response_model=JointPaymentDetailResponse,
)
async def get_joint_payment_confirmation_detail(
    payment_bill_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """付款单头与构成该付款单的联营结算批次明细。"""
    try:
        require_permission(db, current_user, "settlement.joint_payment_confirmation.view")
        result = payment_confirmation_svc.get_joint_payment_detail(
            db,
            payment_bill_no,
            _joint_payment_scope(db, current_user),
        )
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="付款单不存在或不在数据范围内")
        return JointPaymentDetailResponse(**result)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception("联营付款单确认明细查询失败 bill_no=%s", payment_bill_no)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {e.__class__.__name__}",
        ) from e


@router.get("/joint-statements", response_model=JointSettlementListResponse)
async def list_joint_statements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    wmid: str | None = Query(
        None,
        description="经营方式精确过滤；不传则不过滤（不按联营码筛选）。",
    ),
    mkt: str | None = Query(None, description="门店编码/名称片段"),
    dept_prefix: str | None = Query(None, description="部门/柜组编码开头，例如 601 或 60201"),
    date_from: str | None = Query(None, description="制单日期起 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="制单日期止 YYYY-MM-DD"),
    keyword: str | None = Query(None, description="结算单号、合同号、供应商、paybatch.pbbillno 单据号 模糊搜索"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    联营结算单分页列表（主表 + 销售收入/费用汇总 + 付款单柜组维表）。
    按数据策略中「柜组」编码过滤；未配置任何允许柜组时列表为空（管理员除外）。
    """
    try:
        require_permission(db, current_user, "settlement.view")
        scope = load_business_scope(db, current_user, fallback_resource_code="settlement")

        if is_admin(db, current_user) or scope.all_access:
            items, total = svc.list_joint_settlements(
                db,
                page=page,
                page_size=page_size,
                wmid=wmid,
                mkt=mkt,
                dept_prefix=dept_prefix,
                date_from=date_from,
                date_to=date_to,
                keyword=keyword,
                scope_all_access=True,
            )
        else:
            allowed = scope.allow.get("group", set())
            if not allowed:
                return JointSettlementListResponse(
                    items=[],
                    total=0,
                    page=page,
                    page_size=page_size,
                )
            denied = scope.deny.get("group", set())
            items, total = svc.list_joint_settlements(
                db,
                page=page,
                page_size=page_size,
                wmid=wmid,
                mkt=mkt,
                dept_prefix=dept_prefix,
                date_from=date_from,
                date_to=date_to,
                keyword=keyword,
                scope_all_access=False,
                scope_group_allow=frozenset(allowed),
                scope_group_deny=frozenset(denied) if denied else None,
            )
        return JointSettlementListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    except SQLAlchemyError as e:
        logger.exception("联营结算单列表查询失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {e.__class__.__name__}",
        ) from e


@router.get("/joint-statements/{bill_no}", response_model=JointSettlementDetailResponse)
async def get_joint_statement_detail(
    bill_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """单笔结算单明细：头 + 销售类明细行 + 费用明细。"""
    try:
        require_permission(db, current_user, "settlement.view")
        bill = bill_no.strip()
        data = svc.get_settlement_detail(db, bill)
        if data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="结算单不存在")

        scope = load_business_scope(db, current_user, fallback_resource_code="settlement")
        if not is_admin(db, current_user) and not scope.all_access:
            g = svc.effective_settlement_group_norm(db, bill)
            if not scope_allows_business(scope, group_code=g):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权查看该结算单（柜组不在您的数据范围内）",
                )

        return JointSettlementDetailResponse(**data)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception("联营结算单明细查询失败 bill_no=%s", bill_no)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库查询失败: {e.__class__.__name__}",
        ) from e
