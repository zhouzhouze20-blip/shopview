"""
百货柜位管理系统 - Pydantic 数据模式
Department Store Counter Management System - Pydantic Schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


# 基础响应模型
class BaseResponse(BaseModel):
    message: str
    success: bool = True


# 门店相关模型
class StoreBase(BaseModel):
    store_name: str
    store_code: str
    address: Optional[str] = None
    manager_name: Optional[str] = None
    contact_phone: Optional[str] = None


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    store_name: Optional[str] = None
    address: Optional[str] = None
    manager_name: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None


class Store(StoreBase):
    store_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 楼层相关模型
class FloorBase(BaseModel):
    floor_name: str
    floor_number: Optional[int] = None
    description: Optional[str] = None
    floor_plan_url: Optional[str] = None
    total_area: Optional[Decimal] = None


class FloorCreate(FloorBase):
    store_id: int


class FloorUpdate(BaseModel):
    floor_name: Optional[str] = None
    floor_number: Optional[int] = None
    description: Optional[str] = None
    floor_plan_url: Optional[str] = None
    total_area: Optional[Decimal] = None
    is_active: Optional[bool] = None


class Floor(FloorBase):
    floor_id: int
    store_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# 柜位相关模型
class CounterBase(BaseModel):
    counter_code: str
    counter_name: Optional[str] = None
    area: Optional[Decimal] = None
    position_x: Optional[Decimal] = None
    position_y: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    counter_type: Optional[str] = None
    monthly_rent: Optional[Decimal] = None
    management_fee: Optional[Decimal] = None
    deposit: Optional[Decimal] = None


class CounterCreate(CounterBase):
    store_id: int
    floor_id: int


class CounterUpdate(BaseModel):
    counter_name: Optional[str] = None
    area: Optional[Decimal] = None
    position_x: Optional[Decimal] = None
    position_y: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    counter_type: Optional[str] = None
    status: Optional[str] = None
    monthly_rent: Optional[Decimal] = None
    management_fee: Optional[Decimal] = None
    deposit: Optional[Decimal] = None
    is_active: Optional[bool] = None


class Counter(CounterBase):
    counter_id: int
    store_id: int
    floor_id: int
    status: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 租户相关模型
class TenantBase(BaseModel):
    company_name: str
    tenant_code: str
    legal_representative: Optional[str] = None
    business_license: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    address: Optional[str] = None
    business_category: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    company_name: Optional[str] = None
    legal_representative: Optional[str] = None
    business_license: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    address: Optional[str] = None
    business_category: Optional[str] = None
    is_active: Optional[bool] = None


class Tenant(TenantBase):
    tenant_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 品牌相关模型
class BrandBase(BaseModel):
    brand_name: str
    brand_name_en: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None


class BrandCreate(BrandBase):
    tenant_id: int


class BrandUpdate(BaseModel):
    brand_name: Optional[str] = None
    brand_name_en: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None


class Brand(BrandBase):
    brand_id: int
    tenant_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# 合同相关模型
class ContractBase(BaseModel):
    contract_number: str
    contract_type: Optional[str] = None
    start_date: date
    end_date: date
    monthly_rent: Decimal
    management_fee: Optional[Decimal] = None
    deposit: Optional[Decimal] = None
    payment_method: Optional[str] = None
    payment_cycle: Optional[str] = None
    notes: Optional[str] = None


class ContractCreate(ContractBase):
    counter_id: int
    tenant_id: int


class ContractUpdate(BaseModel):
    contract_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    monthly_rent: Optional[Decimal] = None
    management_fee: Optional[Decimal] = None
    deposit: Optional[Decimal] = None
    payment_method: Optional[str] = None
    payment_cycle: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class Contract(ContractBase):
    contract_id: int
    counter_id: int
    tenant_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 账单相关模型
class BillBase(BaseModel):
    bill_number: str
    bill_type: Optional[str] = None
    billing_period: Optional[str] = None
    amount: Decimal
    due_date: Optional[date] = None
    notes: Optional[str] = None


class BillCreate(BillBase):
    contract_id: int
    counter_id: int


class BillUpdate(BaseModel):
    bill_type: Optional[str] = None
    billing_period: Optional[str] = None
    amount: Optional[Decimal] = None
    due_date: Optional[date] = None
    payment_status: Optional[str] = None
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class Bill(BillBase):
    bill_id: int
    contract_id: int
    counter_id: int
    payment_status: str
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 用户相关模型
class UserBase(BaseModel):
    username: str
    real_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: str = "user"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    user_id: int
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 统计数据模型
class DashboardStats(BaseModel):
    total_stores: int
    total_counters: int
    occupied_counters: int
    vacant_counters: int
    total_tenants: int
    active_contracts: int
    monthly_revenue: Decimal
    overdue_bills: int


class StoreStats(BaseModel):
    store_id: int
    store_name: str
    total_counters: int
    occupied_counters: int
    vacancy_rate: float
    monthly_revenue: Decimal


# 搜索和查询模型
class SearchParams(BaseModel):
    keyword: Optional[str] = None
    store_id: Optional[int] = None
    floor_id: Optional[int] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20


class PaginationResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int