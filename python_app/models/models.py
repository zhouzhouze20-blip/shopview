"""
百货柜位管理系统 - 数据模型
Department Store Counter Management System - Database Models
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Numeric, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Store(Base):
    """门店信息表"""
    __tablename__ = "stores"

    store_id = Column(Integer, primary_key=True, index=True)
    store_name = Column(String(100), nullable=False, comment="门店名称")
    store_code = Column(String(20), unique=True, nullable=False, comment="门店编码")
    address = Column(Text, comment="门店地址")
    manager_name = Column(String(50), comment="店长姓名")
    contact_phone = Column(String(20), comment="联系电话")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    floors = relationship("Floor", back_populates="store")
    counters = relationship("Counter", back_populates="store")


class Floor(Base):
    """楼层信息表"""
    __tablename__ = "floors"

    floor_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    floor_name = Column(String(50), nullable=False, comment="楼层名称")
    floor_number = Column(Integer, comment="楼层编号")
    description = Column(Text, comment="楼层描述")
    floor_plan_url = Column(String(500), comment="楼层平面图URL")
    total_area = Column(Numeric(10, 2), comment="总面积（平方米）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关联关系
    store = relationship("Store", back_populates="floors")
    counters = relationship("Counter", back_populates="floor")


class Counter(Base):
    """柜位信息表"""
    __tablename__ = "counters"

    counter_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.floor_id"), nullable=False)
    counter_code = Column(String(20), nullable=False, comment="柜位编号")
    counter_name = Column(String(100), comment="柜位名称")
    area = Column(Numeric(10, 2), comment="面积（平方米）")
    position_x = Column(Numeric(10, 2), comment="X坐标")
    position_y = Column(Numeric(10, 2), comment="Y坐标")
    width = Column(Numeric(10, 2), comment="宽度")
    height = Column(Numeric(10, 2), comment="高度")
    counter_type = Column(String(50), comment="柜位类型")
    status = Column(String(20), default="vacant", comment="状态：vacant-空置, occupied-已租, maintenance-维护")
    monthly_rent = Column(Numeric(10, 2), comment="月租金")
    management_fee = Column(Numeric(10, 2), comment="管理费")
    deposit = Column(Numeric(10, 2), comment="押金")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    store = relationship("Store", back_populates="counters")
    floor = relationship("Floor", back_populates="counters")
    contracts = relationship("Contract", back_populates="counter")
    bills = relationship("Bill", back_populates="counter")


class Tenant(Base):
    """租户（商户）信息表"""
    __tablename__ = "tenants"

    tenant_id = Column(Integer, primary_key=True, index=True)
    tenant_code = Column(String(20), unique=True, nullable=False, comment="商户编码")
    company_name = Column(String(200), nullable=False, comment="公司名称")
    legal_representative = Column(String(50), comment="法人代表")
    business_license = Column(String(50), comment="营业执照号")
    contact_person = Column(String(50), comment="联系人")
    contact_phone = Column(String(20), comment="联系电话")
    contact_email = Column(String(100), comment="联系邮箱")
    address = Column(Text, comment="公司地址")
    business_category = Column(String(50), comment="经营类别")
    is_active = Column(Boolean, default=True, comment="是否活跃")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    contracts = relationship("Contract", back_populates="tenant")
    brands = relationship("Brand", back_populates="tenant")


class Brand(Base):
    """品牌信息表"""
    __tablename__ = "brands"

    brand_id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.tenant_id"), nullable=False)
    brand_name = Column(String(100), nullable=False, comment="品牌名称")
    brand_name_en = Column(String(100), comment="品牌英文名")
    category = Column(String(50), comment="品牌类别")
    description = Column(Text, comment="品牌描述")
    logo_url = Column(String(500), comment="品牌logo URL")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关联关系
    tenant = relationship("Tenant", back_populates="brands")


class Contract(Base):
    """合同信息表"""
    __tablename__ = "contracts"

    contract_id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String(50), unique=True, nullable=False, comment="合同编号")
    counter_id = Column(Integer, ForeignKey("counters.counter_id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.tenant_id"), nullable=False)
    contract_type = Column(String(20), comment="合同类型：lease-租赁, management-管理")
    start_date = Column(Date, nullable=False, comment="开始日期")
    end_date = Column(Date, nullable=False, comment="结束日期")
    monthly_rent = Column(Numeric(10, 2), nullable=False, comment="月租金")
    management_fee = Column(Numeric(10, 2), comment="管理费")
    deposit = Column(Numeric(10, 2), comment="押金")
    payment_method = Column(String(20), comment="付款方式")
    payment_cycle = Column(String(20), comment="付款周期")
    status = Column(String(20), default="active", comment="合同状态：active-有效, expired-过期, terminated-终止")
    notes = Column(Text, comment="备注")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    counter = relationship("Counter", back_populates="contracts")
    tenant = relationship("Tenant", back_populates="contracts")
    bills = relationship("Bill", back_populates="contract")


class Bill(Base):
    """账单信息表"""
    __tablename__ = "bills"

    bill_id = Column(Integer, primary_key=True, index=True)
    bill_number = Column(String(50), unique=True, nullable=False, comment="账单编号")
    contract_id = Column(Integer, ForeignKey("contracts.contract_id"), nullable=False)
    counter_id = Column(Integer, ForeignKey("counters.counter_id"), nullable=False)
    bill_type = Column(String(20), comment="账单类型：rent-租金, management-管理费, utilities-水电费")
    billing_period = Column(String(20), comment="账期")
    amount = Column(Numeric(10, 2), nullable=False, comment="金额")
    due_date = Column(Date, comment="到期日期")
    payment_status = Column(String(20), default="unpaid", comment="付款状态：unpaid-未付, paid-已付, overdue-逾期")
    payment_date = Column(Date, comment="付款日期")
    payment_method = Column(String(20), comment="付款方式")
    notes = Column(Text, comment="备注")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    contract = relationship("Contract", back_populates="bills")
    counter = relationship("Counter", back_populates="bills")


class User(Base):
    """用户信息表"""
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(50), comment="真实姓名")
    email = Column(String(100), comment="邮箱")
    phone = Column(String(20), comment="电话")
    role = Column(String(20), default="user", comment="角色：admin-管理员, user-普通用户, viewer-查看者")
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_login = Column(DateTime, comment="最后登录时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    action = Column(String(50), comment="操作类型")
    target_type = Column(String(50), comment="操作对象类型")
    target_id = Column(Integer, comment="操作对象ID")
    description = Column(Text, comment="操作描述")
    ip_address = Column(String(50), comment="IP地址")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")