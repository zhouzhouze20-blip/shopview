"""联营续签合同收益影响报表 API。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import User
from routers.auth import get_current_user
from routers.authz import load_business_scope, require_permission
from services.joint_renewal_revenue_report import load_joint_renewal_revenue_report


router = APIRouter(prefix="/api/reports/joint-renewal-revenue", tags=["reports"])


@router.get("")
async def joint_renewal_revenue_report(
    start_date: date = Query(..., description="续签合同生效日期起"),
    end_date: date = Query(..., description="续签合同生效日期止"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    try:
        require_permission(db, current_user, "revenue.view")
        scope = load_business_scope(db, current_user, fallback_resource_code="revenue")
        return load_joint_renewal_revenue_report(
            db,
            start_date=start_date,
            end_date=end_date,
            scope=scope,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取联营续签收益分析失败: {exc}",
        ) from exc
