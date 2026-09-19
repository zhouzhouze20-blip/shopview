"""Authenticated, data-scoped coupon monitoring without campaign setup."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from services.activity_analysis.campaign import VIEW_PERMISSION
from services.activity_analysis.coupon_live import STORE, check_scope, query_report

router = APIRouter(prefix="/api/activity-analysis/coupon-live", tags=["coupon-live"])


@router.get("")
def report(response: Response, valid_to: date | None = None,
           db: Session = Depends(get_db), user: User = Depends(get_current_user),
           start_date: date | None = None, end_date: date | None = None):
    require_permission(db, user, VIEW_PERMISSION)
    scope = load_business_scope(db, user)
    response.headers["Cache-Control"] = "private, no-store"
    try:
        store_id = db.execute(text("SELECT store_id FROM stores WHERE TRIM(store_code)=:code AND is_active IS TRUE"),
                              {"code": STORE}).scalar_one_or_none()
        if store_id is None:
            raise HTTPException(503, "购物中心门店主档未就绪")
        check_scope(scope, store_id)
        db.rollback()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        db.execute(text("SET LOCAL statement_timeout='30s'"))
        return query_report(db, scope, store_id, valid_to, query_start=start_date, query_end=end_date)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(504, "卡券实时跟进查询超时或数据源暂不可用，请稍后刷新") from exc
    except ProgrammingError as exc:
        db.rollback()
        raise HTTPException(503, "卡券实时跟进所需的日志、销售或组织主档尚未就绪") from exc
