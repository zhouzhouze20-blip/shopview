"""
百货柜位管理系统 - 厅房管理API
Department Store Counter Management System - Hall Management API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from models.database import get_db
from models.models import Hall, CounterGroup, HallGroupBinding, Store
from schemas.schemas import (
    Hall as HallSchema, 
    HallCreate, 
    HallUpdate,
    CounterGroup as CounterGroupSchema,
    CounterGroupCreate,
    CounterGroupUpdate,
    HallGroupBinding as HallGroupBindingSchema,
    HallGroupBindingCreate,
    HallGroupBindingUpdate,
    HallManagementStats,
    BaseResponse
)
from sqlalchemy import text
from utils.floor_table import resolve_floor_table

router = APIRouter(
    prefix="/api/halls",
    tags=["halls"]
)


@router.get("/", response_model=List[HallSchema])
async def get_halls(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    store_id: Optional[int] = Query(None),
    floor_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取厅房列表"""
    query = db.query(Hall)
    
    # 过滤条件
    if store_id is not None:
        query = query.filter(Hall.store_id == store_id)
    if floor_id is not None:
        query = query.filter(Hall.floor_id == floor_id)
    if is_active is not None:
        query = query.filter(Hall.is_active == is_active)
    if search:
        query = query.filter(
            or_(
                Hall.hall_name.contains(search),
                Hall.counter_number.contains(search),
                Hall.hall_code.contains(search)
            )
        )
    
    halls = query.offset(skip).limit(limit).all()
    return halls


@router.get("/stats/overview", response_model=HallManagementStats)
async def get_hall_stats(
    store_id: Optional[int] = Query(None),
    floor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """获取厅房管理统计信息"""
    query = db.query(Hall)
    
    if store_id is not None:
        query = query.filter(Hall.store_id == store_id)
    if floor_id is not None:
        query = query.filter(Hall.floor_id == floor_id)
    
    total_halls = query.filter(Hall.is_active == True).count()
    
    occupied_halls = query.join(HallGroupBinding).filter(
        and_(
            Hall.is_active == True,
            HallGroupBinding.is_active == True
        )
    ).count()
    
    vacant_halls = total_halls - occupied_halls
    
    area_stats = query.filter(Hall.is_active == True).with_entities(
        func.sum(Hall.area).label('total_area')
    ).first()
    total_area = area_stats.total_area or 0
    
    occupied_area_stats = query.join(HallGroupBinding).filter(
        and_(
            Hall.is_active == True,
            HallGroupBinding.is_active == True
        )
    ).with_entities(
        func.sum(Hall.area).label('occupied_area')
    ).first()
    occupied_area = occupied_area_stats.occupied_area or 0
    
    vacancy_rate = (vacant_halls / total_halls * 100) if total_halls > 0 else 0
    
    revenue_stats = db.query(func.sum(CounterGroup.monthly_revenue)).join(
        HallGroupBinding, CounterGroup.group_code == HallGroupBinding.group_code
    ).join(
        Hall, HallGroupBinding.hall_id == Hall.hall_id
    ).filter(
        and_(
            Hall.is_active == True,
            HallGroupBinding.is_active == True,
            CounterGroup.is_active == True
        )
    ).first()
    monthly_revenue = revenue_stats[0] or 0
    
    return HallManagementStats(
        total_halls=total_halls,
        occupied_halls=occupied_halls,
        vacant_halls=vacant_halls,
        total_area=total_area,
        occupied_area=occupied_area,
        vacancy_rate=round(vacancy_rate, 2),
        monthly_revenue=monthly_revenue
    )


@router.get("/{hall_id}", response_model=HallSchema)
async def get_hall(hall_id: int, db: Session = Depends(get_db)):
    """获取单个厅房信息"""
    hall = db.query(Hall).filter(Hall.hall_id == hall_id).first()
    if not hall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="厅房不存在"
        )
    return hall


@router.post("/", response_model=HallSchema)
async def create_hall(hall: HallCreate, db: Session = Depends(get_db)):
    """创建新厅房"""
    # 检查厅房编码是否已存在
    existing_hall = db.query(Hall).filter(Hall.hall_code == hall.hall_code).first()
    if existing_hall:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="厅房编码已存在"
        )
    
    # 检查门店和楼层是否存在
    store = db.query(Store).filter(Store.store_id == hall.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="门店不存在"
        )
    
    floor_table = resolve_floor_table(db)
    floor_key = "floor_id" if floor_table == "store_floors" else "id"
    floor_row = db.execute(
        text(f"SELECT {floor_key} FROM {floor_table} WHERE {floor_key} = :floor_id"),
        {"floor_id": hall.floor_id},
    ).first()
    if not floor_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="楼层不存在"
        )
    
    db_hall = Hall(**hall.dict())
    db.add(db_hall)
    db.commit()
    db.refresh(db_hall)
    return db_hall


@router.put("/{hall_id}", response_model=HallSchema)
async def update_hall(
    hall_id: int,
    hall_update: HallUpdate,
    db: Session = Depends(get_db)
):
    """更新厅房信息"""
    db_hall = db.query(Hall).filter(Hall.hall_id == hall_id).first()
    if not db_hall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="厅房不存在"
        )
    
    update_data = hall_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_hall, field, value)
    
    db.commit()
    db.refresh(db_hall)
    return db_hall


@router.delete("/{hall_id}", response_model=BaseResponse)
async def delete_hall(hall_id: int, db: Session = Depends(get_db)):
    """删除厅房（软删除）"""
    db_hall = db.query(Hall).filter(Hall.hall_id == hall_id).first()
    if not db_hall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="厅房不存在"
        )
    
    db_hall.is_active = False
    db.commit()
    return BaseResponse(message="厅房删除成功")


# 柜组管理API
@router.get("/counter-groups/", response_model=List[CounterGroupSchema])
async def get_counter_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    store_id: Optional[int] = Query(None, description="门店ID"),
    db: Session = Depends(get_db)
):
    """获取柜组列表"""
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
                CounterGroup.brand_name.contains(search)
            )
        )
    
    groups = query.offset(skip).limit(limit).all()
    return groups


@router.post("/counter-groups/", response_model=CounterGroupSchema)
async def create_counter_group(group: CounterGroupCreate, db: Session = Depends(get_db)):
    """创建新柜组"""
    existing_group = db.query(CounterGroup).filter(CounterGroup.group_code == group.group_code).first()
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="柜组编码已存在"
        )
    
    db_group = CounterGroup(**group.dict())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


# 厅房-柜组绑定API
@router.post("/bindings/", response_model=HallGroupBindingSchema)
async def create_hall_group_binding(
    binding: HallGroupBindingCreate,
    db: Session = Depends(get_db)
):
    """创建厅房-柜组绑定"""
    # 检查厅房是否存在
    hall = db.query(Hall).filter(Hall.hall_id == binding.hall_id).first()
    if not hall:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="厅房不存在"
        )
    
    # 检查柜组是否存在
    group = db.query(CounterGroup).filter(CounterGroup.group_code == binding.group_code).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="柜组不存在"
        )
    
    # 检查是否已存在绑定
    existing_binding = db.query(HallGroupBinding).filter(
        and_(
            HallGroupBinding.hall_id == binding.hall_id,
            HallGroupBinding.is_active == True
        )
    ).first()
    if existing_binding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该厅房已绑定其他柜组"
        )
    
    db_binding = HallGroupBinding(**binding.dict())
    db.add(db_binding)
    db.commit()
    db.refresh(db_binding)
    return db_binding


@router.get("/bindings/", response_model=List[HallGroupBindingSchema])
async def get_hall_group_bindings(
    hall_id: Optional[int] = Query(None),
    group_code: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """获取厅房-柜组绑定列表"""
    query = db.query(HallGroupBinding)
    
    if hall_id is not None:
        query = query.filter(HallGroupBinding.hall_id == hall_id)
    if group_code is not None:
        query = query.filter(HallGroupBinding.group_code == group_code)
    if is_active is not None:
        query = query.filter(HallGroupBinding.is_active == is_active)
    
    bindings = query.all()
    return bindings


@router.put("/bindings/{binding_id}", response_model=HallGroupBindingSchema)
async def update_hall_group_binding(
    binding_id: int,
    binding_update: HallGroupBindingUpdate,
    db: Session = Depends(get_db)
):
    """更新厅房-柜组绑定"""
    db_binding = db.query(HallGroupBinding).filter(HallGroupBinding.binding_id == binding_id).first()
    if not db_binding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="绑定记录不存在"
        )
    
    update_data = binding_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_binding, field, value)
    
    db.commit()
    db.refresh(db_binding)
    return db_binding
