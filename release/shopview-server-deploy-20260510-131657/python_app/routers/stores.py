"""
百货柜位管理系统 - 门店管理API
Department Store Counter Management System - Store Management API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from models.database import get_db
from models.models import Store
from routers.authz import require_permission_dependency
from schemas.schemas import Store as StoreSchema, StoreCreate, StoreUpdate, BaseResponse

router = APIRouter(
    prefix="/api/stores",
    tags=["stores"]
)


@router.get("", response_model=List[StoreSchema])
@router.get("/", response_model=List[StoreSchema])
async def get_stores(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取门店列表"""
    query = db.query(Store)
    if is_active is not None:
        query = query.filter(Store.is_active == is_active)
    stores = query.offset(skip).limit(limit).all()
    return stores


@router.get("/{store_id}", response_model=StoreSchema)
async def get_store(store_id: int, db: Session = Depends(get_db)):
    """获取单个门店信息"""
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在"
        )
    return store


@router.post("/", response_model=StoreSchema)
async def create_store(
    store: StoreCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("store.create")),
):
    """创建新门店"""
    # 检查门店编码是否已存在
    existing_store = db.query(Store).filter(Store.store_code == store.store_code).first()
    if existing_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="门店编码已存在"
        )
    
    db_store = Store(**store.dict())
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store


@router.put("/{store_id}", response_model=StoreSchema)
async def update_store(
    store_id: int,
    store_update: StoreUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("store.edit")),
):
    """更新门店信息"""
    db_store = db.query(Store).filter(Store.store_id == store_id).first()
    if not db_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在"
        )
    
    update_data = store_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_store, field, value)
    
    db.commit()
    db.refresh(db_store)
    return db_store


@router.delete("/{store_id}", response_model=BaseResponse)
async def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission_dependency("store.delete")),
):
    """删除门店（软删除）"""
    db_store = db.query(Store).filter(Store.store_id == store_id).first()
    if not db_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在"
        )
    
    db_store.is_active = False
    db.commit()
    return BaseResponse(message="门店删除成功")
