"""Business-owned campaign configuration and holder-based reports."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from pydantic import BaseModel,Field,field_validator

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from routers.activity_analysis import _require_selected_activity_store, _activity_store_options_for_scope
from services.activity_analysis.campaign import (
    CampaignInput, VIEW_PERMISSION, MANAGE_PERMISSION, query_report, serializable,
    ISSUES_SQL,parameters,limited_rows,
)
from services.activity_analysis.campaign_erp import fetch_rule_summary, RuleSourceError
from services.activity_analysis.campaign_ownership import load_ownership,ownership_view,asset_key,scope_key

router = APIRouter(prefix="/api/activity-analysis/campaigns", tags=["coupon-campaigns"])


class OwnershipConfirmation(BaseModel):
    fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_version: int = Field(ge=0)
    note: str = Field(min_length=5,max_length=2000)

    @field_validator('note')
    @classmethod
    def meaningful_note(cls,value):
        if len(value.strip())<5:
            raise ValueError('请填写至少5字的归属核对依据')
        return value.strip()


def access(db, user, store=None, manage=False):
    require_permission(db, user, VIEW_PERMISSION)
    if manage:
        require_permission(db, user, MANAGE_PERMISSION)
    scope = load_business_scope(db, user)
    dimensions = (set(scope.allow) | set(scope.deny)) - {"store", "__all__"}
    if any(scope.deny.get(d) for d in dimensions) or (
        not scope.all_access and any(scope.allow.get(d) for d in dimensions)
    ):
        raise HTTPException(403, "活动建档分析需要整店数据范围，暂不支持品类/柜组局部权限")
    if store:
        _require_selected_activity_store(db, scope, store)
    return scope


def ensure_schema(db):
    if not db.execute(text("SELECT to_regclass('public.coupon_campaigns')")).scalar():
        raise HTTPException(503, "活动建档数据表尚未安装，请先执行本版本数据库迁移")


def load_campaign(db, user, campaign_id, manage=False):
    access(db, user, manage=manage)
    ensure_schema(db)
    row = db.execute(text("SELECT * FROM coupon_campaigns WHERE id=:id"), {"id": campaign_id}).mappings().first()
    if not row:
        raise HTTPException(404, "活动不存在")
    access(db, user, row["store_code"], manage=manage)
    return dict(row)


@router.get("/options")
def options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scope = access(db, user)
    can_manage = True
    try:
        require_permission(db, user, MANAGE_PERMISSION)
    except HTTPException:
        can_manage = False
    return {"stores": _activity_store_options_for_scope(db, scope), "can_manage": can_manage}


@router.get("")
def list_campaigns(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scope = access(db, user)
    ensure_schema(db)
    codes = {s["store_code"] for s in _activity_store_options_for_scope(db, scope)}
    rows = db.execute(text("SELECT * FROM coupon_campaigns ORDER BY start_date DESC,id DESC")).mappings()
    return serializable([dict(r) for r in rows if r["store_code"] in codes])


@router.post("")
def create_campaign(payload: CampaignInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    access(db, user, payload.store_code, manage=True)
    ensure_schema(db)
    params = payload.model_dump()
    # Serialize overlapping creations in a store. Existing ownership is never deleted.
    db.execute(text("SELECT pg_advisory_xact_lock(862031,CAST(:store_code AS integer))"), params)
    conflict = db.execute(text("""
      SELECT id,name FROM coupon_campaigns WHERE store_code=:store_code
      AND start_date<=:end_date AND end_date>=:start_date
      AND coupon_types && CAST(:coupon_types AS text[]) LIMIT 1
    """), params).mappings().first()
    if conflict:
        raise HTTPException(409, "本店已有日期重叠且包含相同券种的活动，不能重复归属")
    params["creator"] = user.user_id
    row = db.execute(text("""
      INSERT INTO coupon_campaigns(name,store_code,start_date,end_date,coupon_types,erp_activity_id,notes,created_by)
      VALUES(:name,:store_code,:start_date,:end_date,:coupon_types,:erp_activity_id,:notes,:creator)
      RETURNING *
    """), params).mappings().one()
    db.commit()
    return serializable(dict(row))


@router.put("/{campaign_id}")
def edit_campaign(campaign_id: int, payload: CampaignInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = load_campaign(db, user, campaign_id, manage=True)
    params = payload.model_dump()
    if any(params[k] != existing[k] for k in ("store_code", "start_date", "end_date")) or set(params["coupon_types"]) != set(existing["coupon_types"]):
        raise HTTPException(409, "已建档活动的门店、档期和券种不能修改，以免改变历史归属")
    params["id"] = campaign_id
    row = db.execute(text("""
      UPDATE coupon_campaigns SET name=:name,notes=:notes,
        rule_snapshot=CASE WHEN erp_activity_id=:erp_activity_id THEN rule_snapshot ELSE NULL END,
        erp_activity_id=:erp_activity_id,updated_at=NOW()
      WHERE id=:id RETURNING *
    """), params).mappings().one()
    db.commit()
    return serializable(dict(row))


@router.post("/{campaign_id}/erp-rules/refresh")
def refresh_rules(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = load_campaign(db, user, campaign_id, manage=True)
    try:
        rules = fetch_rule_summary(db, campaign)
    except RuleSourceError as exc:
        raise HTTPException(503, str(exc)) from exc
    snapshot = {"source": "柜位ODS：GPP TKTGOODSYQRATE + TKTBGOODSFQHEAD（PAPI同步）",
                "fetched_at": datetime.now(timezone.utc).isoformat(), **rules,
                "basis": "已审核收券规则摘要；不代表POS逐笔实际命中规则，不自动判违规"}
    snapshot = serializable(snapshot)
    update = db.execute(text("""
      UPDATE coupon_campaigns SET rule_snapshot=CAST(:snapshot AS jsonb),updated_at=NOW()
      WHERE id=:id AND erp_activity_id=:erp_activity_id
    """), {"id": campaign_id, "erp_activity_id": campaign["erp_activity_id"], "snapshot": json.dumps(snapshot, ensure_ascii=False)})
    if not update.rowcount:
        db.rollback()
        raise HTTPException(409, "ERP档期关联已变更，请重新读取规则")
    db.commit()
    return snapshot


@router.get("/{campaign_id}/report")
def report(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = load_campaign(db, user, campaign_id)
    # Authorization reads are complete. All analytical SELECTs share one read-only
    # snapshot so a concurrent ETL load cannot mix different source versions.
    db.rollback()
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    db.execute(text("SET LOCAL statement_timeout='30s'"))
    try:
        result = query_report(db, campaign)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(504, "活动报告查询未完成，请稍后重试或缩短档期") from exc
    except ProgrammingError as exc:
        db.rollback()
        raise HTTPException(503, "活动报告所需的卡券、销售或会员数据源尚未就绪") from exc
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.post('/{campaign_id}/ownership/confirm')
def confirm_ownership(campaign_id:int,payload:OwnershipConfirmation,
                      db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    try:
        return _confirm_ownership(campaign_id,payload,db,user)
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(504,'归属确认查询或锁等待未完成，请刷新状态后重试') from exc
    except ProgrammingError as exc:
        db.rollback()
        raise HTTPException(503,'归属确认所需的数据源尚未就绪') from exc


def _confirm_ownership(campaign_id,payload,db,user):
    campaign=load_campaign(db,user,campaign_id,manage=True)
    ready,_=load_ownership(db,campaign_id)
    if not ready:
        raise HTTPException(503,'归属确认表尚未安装，请先执行数据库迁移')
    db.execute(text("SET LOCAL statement_timeout='30s'"))
    db.execute(text("SET LOCAL lock_timeout='5s'"))
    db.execute(text("SELECT pg_advisory_xact_lock(862031,CAST(:store_code AS integer))"),campaign)
    # Refresh after locking: a concurrent ERP-link edit must not confirm stale scope.
    campaign=dict(db.execute(text('SELECT * FROM coupon_campaigns WHERE id=:id FOR UPDATE'),
                             {'id':campaign_id}).mappings().one())
    _,record=load_ownership(db,campaign_id)
    if (record or {}).get('version',0)!=payload.expected_version:
        raise HTTPException(409,'归属版本已变更，请刷新报告后重新确认')
    try:
        issues=limited_rows(db,ISSUES_SQL,parameters(campaign))
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    view,_=ownership_view(campaign,issues,record)
    if view['fingerprint']!=payload.fingerprint:
        raise HTTPException(409,'候选资产或活动配置已变化，请刷新并重新核对')
    if not view['can_confirm']:
        raise HTTPException(409,'没有可确认资产，或初始发券日志关联其他ERP档期，不能确认')
    keys={asset_key(r) for r in issues}
    others=db.execute(text("""SELECT DISTINCT ON(o.campaign_id) o.campaign_id,o.snapshot
      FROM coupon_campaign_ownership o JOIN coupon_campaigns c ON c.id=o.campaign_id
      WHERE c.store_code=:store_code AND c.id<>:id
      ORDER BY o.campaign_id,o.version DESC"""),{'store_code':campaign['store_code'],'id':campaign_id}).mappings()
    if any(keys & set(r['snapshot'].get('asset_keys',[])) for r in others):
        raise HTTPException(409,'候选券资产已归属本店其他活动，不能重复确认')
    snapshot=dict(scope=scope_key(campaign),asset_keys=sorted(keys),fingerprint=view['fingerprint'],
                  erp_periods=view['erp_periods'],basis=view['basis'])
    row=db.execute(text("""INSERT INTO coupon_campaign_ownership
      (campaign_id,version,snapshot,note,confirmed_by)
      VALUES(:id,:version,CAST(:snapshot AS jsonb),:note,:user_id)
      RETURNING version,confirmed_at,confirmed_by,note"""),dict(id=campaign_id,version=payload.expected_version+1,
        snapshot=json.dumps(snapshot,ensure_ascii=False),note=payload.note,user_id=user.user_id)).mappings().one()
    db.commit()
    return serializable(dict(row))
