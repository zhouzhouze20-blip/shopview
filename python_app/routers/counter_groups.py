"""
柜组查询 API
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import CounterGroup
from routers.authz import require_permission_dependency
from schemas.schemas import CounterGroup as CounterGroupSchema, CounterGroupCreate


router = APIRouter(prefix="/api/counter-groups", tags=["counter-groups"])


@router.get("/", response_model=List[CounterGroupSchema])
async def get_counter_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    store_id: Optional[int] = Query(None, description="门店ID"),
    db: Session = Depends(get_db),
):
    query = db.query(CounterGroup)

    if is_active is not None:
        query = query.filter(CounterGroup.is_active == is_active)
    if store_id is not None:
        query = query.filter(CounterGroup.store_id == store_id)
    if search:
        query = query.filter(
            or_(
                CounterGroup.group_name.contains(search),
                CounterGroup.group_code.contains(search),
                CounterGroup.brand_name.contains(search),
            )
        )

    return query.offset(skip).limit(limit).all()


@router.post("/", response_model=CounterGroupSchema)
async def create_counter_group(
    group: CounterGroupCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("counter_group.create")),
):
    db_group = CounterGroup(**group.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group
