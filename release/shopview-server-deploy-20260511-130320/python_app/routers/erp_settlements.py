"""
ERP 联营结算单 API

数据源：supsettlehead、paybatch（表头单据号 pbbillno，关联 pbjsno=sshbillno）、supsettledettot、
可选 supsettledet（与 paybatch 按单据号关联生成结算单销售）、supsetcharge（见 Alembic f8e9d0c1b2a3）。

说明：列表与明细需登录；功能权限 settlement.view；数据范围按 business_scope 的「柜组 group」
维度过滤（与 ERP 柜组/mfid 编码一致）。管理员不受柜组限制。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
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
