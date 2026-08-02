"""
百货柜位管理系统 - 门店管理API
Department Store Counter Management System - Store Management API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from models.database import get_db
from models.models import Store
from routers.authz import require_permission_dependency
from schemas.schemas import Store as StoreSchema, StoreCreate, StoreUpdate, BaseResponse

router = APIRouter(
    prefix="/api/stores",
    tags=["stores"]
)

BACKOFFICE_FLOOR_CODE = "BO"
BACKOFFICE_FLOOR_NAME = "后台部门"
STORE_LOGICAL_UNIT_CODES = ("后台部门收益", "多经")


def _ensure_store_logical_units(db: Session, store_code: str) -> None:
    """为门店创建不参与实体图形和面积统计的店级逻辑柜位。"""
    floor_row = db.execute(
        text(
            """
            INSERT INTO floors (store_code, building_code, floor_code, name, sort_no)
            VALUES (:store_code, :building_code, :floor_code, :floor_name, 999)
            ON CONFLICT (store_code, building_code, floor_code) DO UPDATE SET
              name = EXCLUDED.name,
              sort_no = EXCLUDED.sort_no
            RETURNING id
            """
        ),
        {
            "store_code": store_code,
            "building_code": f"{store_code}-BO",
            "floor_code": BACKOFFICE_FLOOR_CODE,
            "floor_name": BACKOFFICE_FLOOR_NAME,
        },
    ).fetchone()
    for unit_code in STORE_LOGICAL_UNIT_CODES:
        db.execute(
            text(
                """
                INSERT INTO business_units (
                  floor_id, unit_code, status, contract_mode, manual_area, parent_unit_id
                )
                VALUES (:floor_id, :unit_code, 'ACTIVE', 'SHARED', NULL, NULL)
                ON CONFLICT (floor_id, unit_code) DO UPDATE SET
                  status = 'ACTIVE',
                  contract_mode = 'SHARED',
                  updated_at = NOW()
                """
            ),
            {"floor_id": int(floor_row.id), "unit_code": unit_code},
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
    
    try:
        db_store = Store(**store.dict())
        db.add(db_store)
        db.flush()
        _ensure_store_logical_units(db, db_store.store_code)
        db.commit()
        db.refresh(db_store)
        return db_store
    except Exception:
        db.rollback()
        raise


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
