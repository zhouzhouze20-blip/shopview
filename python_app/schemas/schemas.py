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
    building_code: Optional[str] = None
    building_name: Optional[str] = None
    floor_name: str
    floor_number: int
    floor_display_name: Optional[str] = None
    description: Optional[str] = None
    floor_plan_url: Optional[str] = None
    total_area: Optional[Decimal] = None
    sort_order: Optional[int] = 0


class FloorCreate(FloorBase):
    store_id: int


class FloorUpdate(BaseModel):
    store_id: Optional[int] = None
    building_code: Optional[str] = None
    building_name: Optional[str] = None
    floor_name: Optional[str] = None
    floor_number: Optional[int] = None
    floor_display_name: Optional[str] = None
    description: Optional[str] = None
    floor_plan_url: Optional[str] = None
    total_area: Optional[Decimal] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


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
    group_code: Optional[str] = None
    facade_image_url: Optional[str] = None
    monthly_revenue: Optional[Decimal] = None
    is_active: Optional[bool] = None


class Counter(CounterBase):
    counter_id: int
    store_id: int
    floor_id: int
    status: str
    group_code: Optional[str] = None
    facade_image_url: Optional[str] = None
    monthly_revenue: Optional[Decimal] = None
    daily_revenue: Optional[Decimal] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 楼层信息字段
    floor_name: Optional[str] = None
    floor_number: Optional[int] = None
    floor_display_name: Optional[str] = None
    floor_description: Optional[str] = None
    building_code: Optional[str] = None
    building_name: Optional[str] = None

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


class DepartmentBase(BaseModel):
    store_id: int
    dept_code: str
    dept_name: str
    parent_id: Optional[int] = None
    manager_user_id: Optional[int] = None


class DepartmentCreate(DepartmentBase):
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    store_id: Optional[int] = None
    dept_code: Optional[str] = None
    dept_name: Optional[str] = None
    parent_id: Optional[int] = None
    manager_user_id: Optional[int] = None
    is_active: Optional[bool] = None


class Department(DepartmentBase):
    id: int
    store_name: Optional[str] = None
    manager_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class PostBase(BaseModel):
    post_code: str
    post_name: str
    level: int = 0


class Post(PostBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class PermissionSchema(BaseModel):
    id: int
    permission_code: str
    permission_name: str
    module_code: str
    action_code: str


class RoleBase(BaseModel):
    role_code: str
    role_name: str
    role_level: int = 0
    is_system: bool = True


class RoleCreate(RoleBase):
    is_active: bool = True
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    role_level: Optional[int] = None
    is_system: Optional[bool] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[int]] = None


class RoleSchema(RoleBase):
    id: int
    is_active: bool
    permission_ids: List[int] = []
    permission_codes: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserDepartmentAssignmentInput(BaseModel):
    store_id: int
    department_id: int
    post_id: Optional[int] = None
    is_primary: bool = False


class UserDepartmentAssignmentSchema(UserDepartmentAssignmentInput):
    id: int
    store_name: Optional[str] = None
    department_name: Optional[str] = None
    post_name: Optional[str] = None
    is_active: bool = True


class SystemUserBase(BaseModel):
    username: str
    real_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: str = "ACTIVE"
    default_store_id: Optional[int] = None
    employee_no: Optional[str] = None
    is_active: bool = True


class SystemUserCreate(SystemUserBase):
    password: str
    role_ids: List[int] = []
    department_assignments: List[UserDepartmentAssignmentInput] = []


class SystemUserUpdate(BaseModel):
    real_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    default_store_id: Optional[int] = None
    employee_no: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    role_ids: Optional[List[int]] = None
    department_assignments: Optional[List[UserDepartmentAssignmentInput]] = None


class SystemUserSchema(SystemUserBase):
    user_id: int
    role_ids: List[int] = []
    role_codes: List[str] = []
    role_names: List[str] = []
    department_assignments: List[UserDepartmentAssignmentSchema] = []
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class DataPolicyItemInput(BaseModel):
    dimension_type: str
    dimension_value: str
    include_children: bool = False


class DataPolicyBase(BaseModel):
    subject_type: str
    subject_id: int
    resource_code: str
    action_code: str
    scope_mode: str = "CUSTOM"
    effect: str = "ALLOW"
    priority: int = 100
    is_active: bool = True


class DataPolicyCreate(DataPolicyBase):
    items: List[DataPolicyItemInput] = []


class DataPolicyUpdate(BaseModel):
    subject_type: Optional[str] = None
    subject_id: Optional[int] = None
    resource_code: Optional[str] = None
    action_code: Optional[str] = None
    scope_mode: Optional[str] = None
    effect: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    items: Optional[List[DataPolicyItemInput]] = None


class DataPolicyItemSchema(DataPolicyItemInput):
    id: int


class DataPolicySchema(DataPolicyBase):
    id: int
    subject_name: Optional[str] = None
    items: List[DataPolicyItemSchema] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthUserSchema(BaseModel):
    user_id: int
    username: str
    real_name: Optional[str] = None
    status: str
    is_active: bool
    role_codes: List[str] = []
    role_names: List[str] = []


class LoginResponse(BaseModel):
    message: str
    user: AuthUserSchema


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


# 厅房相关模型
class HallBase(BaseModel):
    hall_code: str
    hall_name: Optional[str] = None
    counter_number: str
    area: Optional[Decimal] = None
    shape_type: str = "rectangle"
    position_data: Optional[dict] = None


class HallCreate(HallBase):
    store_id: int
    floor_id: int


class HallUpdate(BaseModel):
    hall_name: Optional[str] = None
    counter_number: Optional[str] = None
    area: Optional[Decimal] = None
    shape_type: Optional[str] = None
    position_data: Optional[dict] = None
    is_active: Optional[bool] = None


class Hall(HallBase):
    hall_id: int
    store_id: int
    floor_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 柜组相关模型
class CounterGroupBase(BaseModel):
    group_code: str
    group_name: str
    department_code: Optional[str] = None
    department_name: Optional[str] = None
    operation_method: Optional[str] = None
    brand_name: Optional[str] = None
    monthly_revenue: Optional[Decimal] = None


class CounterGroupCreate(CounterGroupBase):
    pass


class CounterGroupUpdate(BaseModel):
    group_name: Optional[str] = None
    department_code: Optional[str] = None
    department_name: Optional[str] = None
    operation_method: Optional[str] = None
    brand_name: Optional[str] = None
    monthly_revenue: Optional[Decimal] = None
    is_active: Optional[bool] = None


class CounterGroup(CounterGroupBase):
    group_id: int
    is_active: bool
    erp_sync_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 厅房-柜组绑定相关模型
class HallGroupBindingBase(BaseModel):
    hall_id: int
    group_code: str


class HallGroupBindingCreate(HallGroupBindingBase):
    bound_by: Optional[str] = None


class HallGroupBindingUpdate(BaseModel):
    is_active: Optional[bool] = None


class HallGroupBinding(HallGroupBindingBase):
    binding_id: int
    is_active: bool
    bound_at: datetime
    bound_by: Optional[str] = None

    class Config:
        from_attributes = True


# 柜位管理统计模型
class HallManagementStats(BaseModel):
    total_halls: int
    occupied_halls: int
    vacant_halls: int
    total_area: Decimal
    occupied_area: Decimal
    vacancy_rate: float
    monthly_revenue: Decimal


# 收益数据相关模型
class RevenueDataBase(BaseModel):
    counter_id: int
    counter_code: Optional[str] = None
    counter_name: Optional[str] = None
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    floor_id: Optional[int] = None
    floor_name: Optional[str] = None
    area: Optional[Decimal] = None
    x: Optional[Decimal] = None
    y: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    monthly_revenue: Optional[Decimal] = None
    daily_revenue: Optional[Decimal] = None
    revenue_per_sqm: Optional[Decimal] = None
    revenue_trend: Optional[str] = None
    revenue_change_percent: Optional[Decimal] = None
    report_date: Optional[date] = None
    
    # 时间分析字段
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    date: Optional[date] = None
    
    # 同期对比字段
    same_period_sales: Optional[Decimal] = None
    same_period_date: Optional[date] = None
    same_period_revenue: Optional[Decimal] = None
    year_over_year: Optional[Decimal] = None
    
    # 其他字段
    status: Optional[str] = None
    tenant_name: Optional[str] = None
    brand_name: Optional[str] = None


class RevenueDataCreate(RevenueDataBase):
    pass


class RevenueDataUpdate(BaseModel):
    counter_code: Optional[str] = None
    counter_name: Optional[str] = None
    store_name: Optional[str] = None
    floor_name: Optional[str] = None
    area: Optional[Decimal] = None
    x: Optional[Decimal] = None
    y: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    monthly_revenue: Optional[Decimal] = None
    daily_revenue: Optional[Decimal] = None
    revenue_per_sqm: Optional[Decimal] = None
    revenue_trend: Optional[str] = None
    revenue_change_percent: Optional[Decimal] = None
    report_date: Optional[date] = None
    
    # 时间分析字段
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    date: Optional[date] = None
    
    # 同期对比字段
    same_period_sales: Optional[Decimal] = None
    same_period_date: Optional[date] = None
    same_period_revenue: Optional[Decimal] = None
    year_over_year: Optional[Decimal] = None
    
    # 其他字段
    status: Optional[str] = None
    tenant_name: Optional[str] = None
    brand_name: Optional[str] = None


class RevenueData(RevenueDataBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 收益数据分析模型
class RevenueAnalysis(BaseModel):
    """收益数据分析结果"""
    total_revenue: Decimal
    average_revenue: Decimal
    revenue_growth: Optional[Decimal] = None
    year_over_year_growth: Optional[Decimal] = None
    top_performers: List[RevenueData] = []
    revenue_trend: str
    period: str


# 时间序列分析模型
class TimeSeriesAnalysis(BaseModel):
    """时间序列分析结果"""
    period: str  # 如 "2025-09"
    total_revenue: Decimal
    record_count: int
    average_revenue: Decimal
    growth_rate: Optional[Decimal] = None
    same_period_revenue: Optional[Decimal] = None
    year_over_year: Optional[Decimal] = None


# ==================== 新增收益相关模型 ====================

# 销售毛利相关模型
class SalesProfitBase(BaseModel):
    counter_id: int
    order_id: str
    order_date: date
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    gross_sales: Decimal
    cost_of_goods: Decimal
    gross_profit: Decimal
    profit_margin: Optional[Decimal] = None
    product_category: Optional[str] = None
    brand_name: Optional[str] = None
    sales_person: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class SalesProfitCreate(SalesProfitBase):
    pass


class SalesProfitUpdate(BaseModel):
    order_id: Optional[str] = None
    order_date: Optional[date] = None
    gross_sales: Optional[Decimal] = None
    cost_of_goods: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None
    product_category: Optional[str] = None
    brand_name: Optional[str] = None
    sales_person: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class SalesProfit(SalesProfitBase):
    profit_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 收费相关模型
class FeeBase(BaseModel):
    counter_id: int
    fee_date: date
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    fee_type: str
    fee_amount: Decimal
    fee_description: Optional[str] = None
    billing_period: Optional[str] = None
    payment_status: str = "unpaid"
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class FeeCreate(FeeBase):
    pass


class FeeUpdate(BaseModel):
    fee_date: Optional[date] = None
    fee_type: Optional[str] = None
    fee_amount: Optional[Decimal] = None
    fee_description: Optional[str] = None
    billing_period: Optional[str] = None
    payment_status: Optional[str] = None
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class Fee(FeeBase):
    fee_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 订单相关模型
class OrderBase(BaseModel):
    order_id: str
    counter_id: int
    order_date: date
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    order_type: Optional[str] = None
    order_status: str = "pending"
    total_amount: Decimal
    discount_amount: Decimal = 0
    final_amount: Decimal
    payment_method: Optional[str] = None
    sales_person: Optional[str] = None
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    order_type: Optional[str] = None
    order_status: Optional[str] = None
    total_amount: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    final_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    sales_person: Optional[str] = None
    notes: Optional[str] = None


class Order(OrderBase):
    created_at: datetime
    updated_at: Optional[datetime] = None
    order_items: List['OrderItem'] = []

    class Config:
        from_attributes = True


# 订单明细相关模型
class OrderItemBase(BaseModel):
    order_id: str
    counter_id: int
    product_code: Optional[str] = None
    product_name: str
    product_category: Optional[str] = None
    brand_name: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    profit: Optional[Decimal] = None
    notes: Optional[str] = None


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemUpdate(BaseModel):
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    brand_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    profit: Optional[Decimal] = None
    notes: Optional[str] = None


class OrderItem(OrderItemBase):
    item_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 收益仪表盘相关模型
class RevenueDashboardSummary(BaseModel):
    """收益仪表盘汇总数据"""
    total_daily_revenue: Decimal
    total_monthly_revenue: Decimal
    total_yearly_revenue: Decimal
    average_daily_revenue: Decimal
    revenue_growth_rate: Optional[Decimal] = None
    year_over_year_growth: Optional[Decimal] = None
    top_performing_counters: List[dict] = []
    revenue_by_floor: List[dict] = []
    revenue_trend: str = "stable"


class CounterRevenueDetail(BaseModel):
    """柜位收益详情"""
    counter_id: int
    counter_code: str
    counter_name: str
    floor_name: str
    store_name: str
    area: Decimal
    
    # 收益数据
    daily_revenue: Decimal
    monthly_revenue: Decimal
    yearly_revenue: Decimal
    revenue_per_sqm: Decimal
    
    # 同比数据
    same_period_daily_revenue: Optional[Decimal] = None
    same_period_monthly_revenue: Optional[Decimal] = None
    year_over_year_daily: Optional[Decimal] = None
    year_over_year_monthly: Optional[Decimal] = None
    
    # 收益分解
    total_sales_profit: Decimal
    total_fees: Decimal
    profit_breakdown: dict = {}


class RevenueBreakdown(BaseModel):
    """收益分解数据"""
    total_revenue: Decimal
    sales_profit: Decimal
    fees: Decimal
    sales_profit_percentage: Decimal
    fees_percentage: Decimal
    profit_margin: Decimal
    fee_breakdown: List[dict] = []
    sales_breakdown: List[dict] = []


# 更新 Order 模型以包含 order_items
Order.model_rebuild()
