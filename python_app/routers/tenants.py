"""
百货柜位管理系统 - 租户管理API
Department Store Counter Management System - Tenant Management API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models.database import get_db
from models.models import Tenant
from schemas.schemas import Tenant as TenantSchema, TenantCreate, TenantUpdate, BaseResponse

router = APIRouter(
    prefix="/api/tenants",
    tags=["tenants"]
)


@router.get("/", response_model=List[TenantSchema])
async def get_tenants(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    business_category: Optional[str] = Query(None, description="经营类别"),
    db: Session = Depends(get_db)
):
    """获取租户列表"""
    query = db.query(Tenant)
    
    if is_active is not None:
        query = query.filter(Tenant.is_active == is_active)
    if business_category is not None:
        query = query.filter(Tenant.business_category == business_category)
    
    tenants = query.offset(skip).limit(limit).all()
    return tenants


@router.get("/search/", response_model=List[TenantSchema])
async def search_tenants(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    q: Optional[str] = Query(None, description="兼容前端搜索参数"),
    storeId: Optional[int] = Query(None, description="兼容前端门店参数，当前未启用"),
    db: Session = Depends(get_db)
):
    """搜索租户"""
    _ = storeId
    search_value = (keyword or q or "").strip()
    if not search_value:
        return []

    tenants = db.query(Tenant).filter(
        (Tenant.company_name.ilike(f"%{search_value}%")) |
        (Tenant.tenant_code.ilike(f"%{search_value}%")) |
        (Tenant.contact_person.ilike(f"%{search_value}%"))
    ).all()
    return tenants


@router.post("/", response_model=TenantSchema)
async def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    """创建新租户"""
    # 检查租户编码是否已存在
    existing_tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant.tenant_code).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="租户编码已存在"
        )
    
    db_tenant = Tenant(**tenant.dict())
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


@router.put("/{tenant_id}", response_model=TenantSchema)
async def update_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    db: Session = Depends(get_db)
):
    """更新租户信息"""
    db_tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not db_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )
    
    update_data = tenant_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tenant, field, value)
    
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


@router.delete("/{tenant_id}", response_model=BaseResponse)
async def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    """删除租户（软删除）"""
    db_tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not db_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )
    
    db_tenant.is_active = False
    db.commit()
    return BaseResponse(message="租户删除成功")


@router.get("/{tenant_id}", response_model=TenantSchema)
async def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    """获取单个租户信息"""
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )
    return tenant
