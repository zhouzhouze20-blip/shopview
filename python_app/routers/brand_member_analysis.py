from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import DataScope, load_business_scope, require_permission, scope_allows_business
from services.brand_member_analysis import (
    build_rule_conclusion,
    list_group_options,
    load_group_meta,
    load_brand_member_analysis,
    normalize_ai_conclusion_terms,
    sanitize_ai_snapshot,
    validate_ai_conclusion,
)
from services.sales_analysis.ai_report import generate_ai_report


router = APIRouter(
    prefix="/api/sales/brand-member-analysis",
    tags=["brand-member-analysis"],
)

BRAND_MEMBER_ANALYSIS_PERMISSION = "sales.brand_member_analysis.view"


class BrandMemberAnalysisRequest(BaseModel):
    store_code: str = Field(..., min_length=1, max_length=20)
    target_group_code: str = Field(..., min_length=1, max_length=20)
    competitor_group_codes: list[str] = Field(default_factory=list, max_length=5)
    current_start: date
    current_end: date
    prior_start: date
    prior_end: date

    @model_validator(mode="after")
    def validate_request(self) -> "BrandMemberAnalysisRequest":
        if self.current_end < self.current_start:
            raise ValueError("本期结束日期不能早于开始日期")
        if self.prior_end < self.prior_start:
            raise ValueError("同期结束日期不能早于开始日期")
        target = self.target_group_code.strip().upper()
        competitors = [code.strip().upper() for code in self.competitor_group_codes if code.strip()]
        if target in competitors:
            raise ValueError("竞品柜组不能包含目标柜组")
        if len(set(competitors)) != len(competitors):
            raise ValueError("竞品柜组不能重复")
        self.store_code = self.store_code.strip()
        self.target_group_code = target
        self.competitor_group_codes = competitors
        return self


class BrandMemberConclusionRequest(BaseModel):
    snapshot: dict[str, Any]


def _target_group_allowed(scope: DataScope, group: dict[str, Any]) -> bool:
    return scope_allows_business(
        scope,
        store_id=group.get("scope_store_id"),
        department_code=group.get("department_code"),
        department_name=group.get("department_name"),
        group_code=group.get("group_code"),
    )


def _group_options_for_user(scope: DataScope, groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose every store group for competitors and mark target eligibility separately."""
    return [
        {
            **{key: value for key, value in group.items() if key != "scope_store_id"},
            "target_selectable": _target_group_allowed(scope, group),
        }
        for group in groups
    ]


def _require_target_group_scope(scope: DataScope, group: dict[str, Any]) -> None:
    if not _target_group_allowed(scope, group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="目标柜组不在当前用户数据权限范围内",
        )


def brand_member_conclusion_instructions() -> str:
    return (
        "你是百货商场品牌会员经营顾问，正在为百货与品牌供应商的经营沟通准备结论。"
        "输入只包含已经由数据库计算好的汇总指标。"
        "本期的比较对象统一称为同期；无论两个日期区间如何选择，都不得写成同比、环比、上期或去年同期。"
        "只能引用输入中直接提供的金额、人数、比例、频次和排名。"
        "固定术语必须原样使用：sales_revenue称为销售收入，不得称销售额或销售码洋；"
        "spend_per_buyer称为会员人均消费，不得称客单价；"
        "purchase_frequency_analysis中的single_purchase称为一次客、repeat_purchase称为多次客；"
        "items_per_ticket称为客件数，average_item_price称为件单价；"
        "department_visit_count称为到目标部门人数，不得称品类到访；"
        "target_repurchase_count称为回购目标柜组人数。"
        "严禁自行做除法、加总、差额、占比或任何其他计算，严禁改写数字。"
        "不得设定输入中不存在的数值目标、提升幅度、预算或期限。"
        "不得编造活动、商品、库存、人员、天气等未提供的原因。"
        "如需解释原因，只能表述为待核查线索。"
        "竞品列表为空时不要提及竞品。"
        "老客漏斗中的历史品牌会员不得称为待激活会员，除非输入明确提供该标签。"
        "输出结构固定为：核心判断、客群变化、经营机会、沟通建议。"
        "每部分只写一句话，建议使用定性动作，不附加未经提供的量化目标。"
        "使用纯文本，不使用Markdown标题、星号、表格或代码块，总长度控制在350字以内。"
        "不得输出会员姓名、手机号、卡号或任何个人识别信息。"
    )


@router.get("/groups")
async def brand_member_group_options(
    store_code: str = Query(..., min_length=1, max_length=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 竞品可搜索所选门店全部柜组；目标柜组由 target_selectable 标记数据权限。
    require_permission(db, current_user, BRAND_MEMBER_ANALYSIS_PERMISSION)
    scope = load_business_scope(db, current_user, fallback_resource_code="sales")
    return _group_options_for_user(scope, list_group_options(db, store_code))


@router.post("/report")
async def brand_member_report(
    request: BrandMemberAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, BRAND_MEMBER_ANALYSIS_PERMISSION)
    target = load_group_meta(db, request.store_code, request.target_group_code)
    if target is not None:
        scope = load_business_scope(db, current_user, fallback_resource_code="sales")
        _require_target_group_scope(scope, target)
    try:
        return load_brand_member_analysis(
            db,
            store_code=request.store_code,
            target_group_code=request.target_group_code,
            competitor_group_codes=request.competitor_group_codes,
            current_start=request.current_start,
            current_end=request.current_end,
            prior_start=request.prior_start,
            prior_end=request.prior_end,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except OperationalError as exc:
        if getattr(exc.orig, "pgcode", None) == "57014":
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="品牌会员分析查询超时，请缩短日期范围后重试。",
            ) from exc
        raise


@router.post("/conclusion")
async def brand_member_conclusion(
    request: BrandMemberConclusionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_permission(db, current_user, BRAND_MEMBER_ANALYSIS_PERMISSION)
    snapshot = sanitize_ai_snapshot(request.snapshot)
    fallback = build_rule_conclusion(snapshot)
    instructions = brand_member_conclusion_instructions()
    ai = generate_ai_report(
        snapshot,
        instructions=instructions,
    )
    ai_report = normalize_ai_conclusion_terms(ai.get("report"))
    accepted, validation_error = validate_ai_conclusion(ai_report, snapshot)
    if not accepted and ai.get("status") in {"success", "truncated"}:
        retry_reason = ai.get("error") if ai.get("status") == "truncated" else validation_error
        retry_instructions = (
            f"{instructions}"
            f"上一次生成结果未通过系统校验：{retry_reason}。"
            "请重新生成完整结论，只能原样引用输入已有数值；"
            "不得自行计算、估算、凑整或输出任何输入中不存在的数字；"
            "四个部分各写一句话，总长度控制在300字以内。"
        )
        ai = generate_ai_report(snapshot, instructions=retry_instructions)
        ai_report = normalize_ai_conclusion_terms(ai.get("report"))
        accepted, validation_error = validate_ai_conclusion(ai_report, snapshot)
    conclusion = ai_report if accepted else fallback
    ai_status = ai.get("status")
    response_status = "guardrail_rejected" if not accepted and ai_status == "success" else ai_status
    return {
        "status": response_status,
        "provider": ai.get("provider"),
        "model": ai.get("model"),
        "conclusion": conclusion,
        "fallback_used": not accepted,
        "error": ai.get("error") or validation_error,
    }
