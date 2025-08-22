"""
百货柜位管理系统 - 柜位管理API
Department Store Counter Management System - Counter Management API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from ..models.database import get_db
from ..models.models import Counter, Store, Floor
from ..schemas.schemas import Counter as CounterSchema, CounterCreate, CounterUpdate, BaseResponse

router = APIRouter(
    prefix="/api/counters",
    tags=["counters"]
)


@router.get("/", response_model=List[CounterSchema])
async def get_counters(
    skip: int = 0,
    limit: int = 100,
    store_id: Optional[int] = Query(None, description="门店ID"),
    floor_id: Optional[int] = Query(None, description="楼层ID"),
    status: Optional[str] = Query(None, description="柜位状态"),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取柜位列表"""
    query = db.query(Counter)
    
    if store_id is not None:
        query = query.filter(Counter.store_id == store_id)
    if floor_id is not None:
        query = query.filter(Counter.floor_id == floor_id)
    if status is not None:
        query = query.filter(Counter.status == status)
    if is_active is not None:
        query = query.filter(Counter.is_active == is_active)
    
    counters = query.offset(skip).limit(limit).all()
    return counters


@router.get("/{counter_id}", response_model=CounterSchema)
async def get_counter(counter_id: int, db: Session = Depends(get_db)):
    """获取单个柜位信息"""
    counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="柜位不存在"
        )
    return counter


@router.post("/", response_model=CounterSchema)
async def create_counter(counter: CounterCreate, db: Session = Depends(get_db)):
    """创建新柜位"""
    # 验证门店和楼层是否存在
    store = db.query(Store).filter(Store.store_id == counter.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="门店不存在"
        )
    
    floor = db.query(Floor).filter(Floor.floor_id == counter.floor_id).first()
    if not floor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="楼层不存在"
        )
    
    # 检查柜位编号是否已存在
    existing_counter = db.query(Counter).filter(
        Counter.counter_code == counter.counter_code,
        Counter.store_id == counter.store_id
    ).first()
    if existing_counter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该门店中柜位编号已存在"
        )
    
    db_counter = Counter(**counter.dict())
    db.add(db_counter)
    db.commit()
    db.refresh(db_counter)
    return db_counter


@router.put("/{counter_id}", response_model=CounterSchema)
async def update_counter(
    counter_id: int,
    counter_update: CounterUpdate,
    db: Session = Depends(get_db)
):
    """更新柜位信息"""
    db_counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
    if not db_counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="柜位不存在"
        )
    
    update_data = counter_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_counter, field, value)
    
    db.commit()
    db.refresh(db_counter)
    return db_counter


@router.delete("/{counter_id}", response_model=BaseResponse)
async def delete_counter(counter_id: int, db: Session = Depends(get_db)):
    """删除柜位（软删除）"""
    db_counter = db.query(Counter).filter(Counter.counter_id == counter_id).first()
    if not db_counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="柜位不存在"
        )
    
    db_counter.is_active = False
    db.commit()
    return BaseResponse(message="柜位删除成功")


@router.get("/search/", response_model=List[CounterSchema])
async def search_counters(
    keyword: str = Query(..., description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """搜索柜位"""
    counters = db.query(Counter).filter(
        (Counter.counter_code.ilike(f"%{keyword}%")) |
        (Counter.counter_name.ilike(f"%{keyword}%"))
    ).all()
    return counters