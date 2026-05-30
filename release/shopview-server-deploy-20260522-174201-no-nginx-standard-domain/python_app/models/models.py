"""
百货柜位管理系统 - 数据模型
Department Store Counter Management System - Database Models
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Text, Numeric, ForeignKey, Date, JSON, PrimaryKeyConstraint, UniqueConstraint
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
    floors = relationship("StoreFloor", back_populates="store")
    counters = relationship("Counter", back_populates="store")


class Floor(Base):
    """楼层字典表：统一管理楼层编码、名称与排序"""
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("store_code", "building_code", "floor_code", name="uq_floors_store_building_floor"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="楼层ID，系统主键")
    store_id = Column("store_code", String(20), nullable=True, comment="门店编码")
    building_code = Column(Text, nullable=False, default="DEFAULT", comment="建筑/项目编码（如百货名称，预留多项目）")
    floor_code = Column(Text, nullable=False, comment="楼层编码，如 B1 / 1F / 2F")
    name = Column(Text, nullable=False, comment="楼层显示名称")
    building_area = Column(Numeric(12, 2), nullable=True, comment="建筑面积（平方米）")
    sort_no = Column(Integer, nullable=False, default=0, comment="楼层排序号，用于前端展示排序")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")


class StoreFloor(Base):
    """门店楼层信息表（关联门店与楼层字典，含平面图等）"""
    __tablename__ = "store_floors"

    floor_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    floor_dict_id = Column(BigInteger, ForeignKey("floors.id"), nullable=True, comment="关联楼层字典ID")
    building_code = Column(String(20), nullable=True, comment="栋号编码（如A栋、B栋）")
    building_name = Column(String(50), nullable=True, comment="栋号名称（如A栋、B栋、主楼）")
    floor_name = Column(String(50), nullable=False, comment="楼层名称")
    floor_number = Column(Integer, nullable=False, comment="楼层编号（-1表示负一楼，0表示地面层，1表示一楼）")
    floor_display_name = Column(String(50), nullable=True, comment="楼层显示名称（如B1、1F、16F）")
    description = Column(Text, comment="楼层描述")
    floor_plan_url = Column(String(500), comment="楼层平面图URL")
    floor_plan_data = Column(JSON, comment="平面图元数据")
    total_area = Column(Numeric(10, 2), comment="总面积（平方米）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序顺序（用于楼层列表排序）")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关联关系
    store = relationship("Store", back_populates="floors")
    floor_dict = relationship("Floor", foreign_keys=[floor_dict_id])


class Counter(Base):
    """柜位信息表"""
    __tablename__ = "counters"

    counter_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    floor_id = Column(BigInteger, ForeignKey("floors.id"), nullable=False)
    counter_code = Column(String(20), nullable=False, comment="柜位编号")
    counter_name = Column(String(100), comment="柜位名称")
    area = Column(Numeric(10, 2), comment="面积（平方米）")
    
    # 位置和尺寸字段
    position_x = Column(Numeric(10, 2), default=0, comment="X坐标位置")
    position_y = Column(Numeric(10, 2), default=0, comment="Y坐标位置")
    width = Column(Numeric(10, 2), default=10, comment="宽度")
    height = Column(Numeric(10, 2), default=10, comment="高度")
    
    # 几何信息关联
    geometry_id = Column(Integer, ForeignKey("counter_geometries.geometry_id"), comment="几何信息ID，关联counter_geometries表")
    
    counter_type = Column(String(50), comment="柜位类型")
    status = Column(String(20), default="vacant", comment="状态：vacant-空置, occupied-已租, maintenance-维护")
    monthly_rent = Column(Numeric(10, 2), comment="月租金")
    management_fee = Column(Numeric(10, 2), comment="管理费")
    deposit = Column(Numeric(10, 2), comment="装修保证金")
    group_code = Column(String(20), comment="柜组编码")
    facade_image_url = Column(String(500), comment="门头图片URL")
    monthly_revenue = Column(Numeric(12, 2), comment="POS押金")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关联关系
    store = relationship("Store", back_populates="counters")
    floor = relationship("Floor")
    contracts = relationship("Contract", back_populates="counter")
    bills = relationship("Bill", back_populates="counter")
    # geometry = relationship("CounterGeometry", back_populates="counter", uselist=False, cascade="all, delete-orphan")


class CounterGroup(Base):
    """ERP 柜组表。

    - ``store_id``：外键，关联 ``stores`` 门店表。
    - ``department_code`` / ``department_name``：部门编码、部门名称。
    - ``group_code`` / ``group_name``：柜组编码、柜组名称。

    门店–部门–柜组在同一行；合同与销售等业务数据范围（business_scope）按上述字段过滤，
    勿与 ``departments`` 手工部门定义表混用。
    """
    __tablename__ = "counter_groups"

    group_id = Column(Integer, primary_key=True, index=True)
    group_code = Column(String(20), unique=True, nullable=False, comment="柜组编码")
    group_name = Column(String(200), nullable=False, comment="柜组名称")
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False, comment="关联门店表 stores.store_id")
    department_code = Column(String(20), comment="部门编码")
    department_name = Column(String(200), comment="部门名称")
    area_code = Column(String(20), comment="区域编码")
    area_name = Column(String(100), comment="区域名称")
    category_code = Column(String(20), comment="类别编码")
    category_name = Column(String(100), comment="类别名称")
    operation_method = Column(String(20), comment="经营方式：租赁/联营/自营")
    brand_name = Column(String(200), comment="品牌名称")
    is_active = Column(Boolean, default=True, comment="是否启用")
    erp_sync_time = Column(DateTime, comment="ERP同步时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    store = relationship("Store")


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
    status = Column(String(20), default="ACTIVE", comment="账号状态：PENDING, ACTIVE, DISABLED, LOCKED")
    default_store_id = Column(Integer, comment="默认门店ID")
    employee_no = Column(String(50), comment="员工编号")
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_login = Column(DateTime, comment="最后登录时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class UserIdentity(Base):
    """用户登录身份表"""
    __tablename__ = "user_identities"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    identity_type = Column(String(20), nullable=False, comment="身份类型：password, wecom")
    identifier = Column(String(200), nullable=False, comment="唯一标识")
    credential_hash = Column(String(255), comment="凭证哈希")
    corp_id = Column(String(100), comment="企业微信企业ID")
    wecom_user_id = Column(String(100), comment="企业微信用户ID")
    union_id = Column(String(100), comment="微信UnionID")
    is_primary = Column(Boolean, default=False, comment="是否主登录身份")
    last_used_at = Column(DateTime, comment="最近使用时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class Department(Base):
    """部门表"""
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("store_id", "dept_code", name="uq_departments_store_code"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False, comment="所属门店ID")
    dept_code = Column(String(50), nullable=False, comment="部门编码")
    dept_name = Column(String(100), nullable=False, comment="部门名称")
    parent_id = Column(BigInteger, ForeignKey("departments.id"), comment="上级部门ID")
    manager_user_id = Column(Integer, ForeignKey("users.user_id"), comment="部门主管用户ID")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class Post(Base):
    """岗位表"""
    __tablename__ = "posts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    post_code = Column(String(50), unique=True, nullable=False, comment="岗位编码")
    post_name = Column(String(100), nullable=False, comment="岗位名称")
    level = Column(Integer, default=0, nullable=False, comment="岗位层级")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class UserDepartmentPost(Base):
    """用户-部门-岗位关联表"""
    __tablename__ = "user_department_posts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    department_id = Column(BigInteger, ForeignKey("departments.id"), nullable=False)
    post_id = Column(BigInteger, ForeignKey("posts.id"), comment="岗位ID")
    is_primary = Column(Boolean, default=False, nullable=False, comment="是否主归属")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class Role(Base):
    """角色表"""
    __tablename__ = "roles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_code = Column(String(50), unique=True, nullable=False, comment="角色编码")
    role_name = Column(String(100), nullable=False, comment="角色名称")
    role_level = Column(Integer, default=0, nullable=False, comment="角色等级")
    is_system = Column(Boolean, default=True, nullable=False, comment="是否系统内置")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    permission_code = Column(String(100), unique=True, nullable=False, comment="权限编码")
    permission_name = Column(String(100), nullable=False, comment="权限名称")
    module_code = Column(String(50), nullable=False, comment="模块编码")
    action_code = Column(String(50), nullable=False, comment="动作编码")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class RolePermission(Base):
    """角色-权限关联表"""
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permissions"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_id = Column(BigInteger, ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = Column(BigInteger, ForeignKey("permissions.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class UserRole(Base):
    """用户-角色关联表"""
    __tablename__ = "user_roles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    role_id = Column(BigInteger, ForeignKey("roles.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), comment="限定门店ID")
    expires_at = Column(DateTime, comment="角色有效截止时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class DataPolicy(Base):
    """数据权限策略表"""
    __tablename__ = "data_policies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subject_type = Column(String(20), nullable=False, comment="授权主体类型：ROLE, USER")
    subject_id = Column(BigInteger, nullable=False, index=True, comment="授权主体ID")
    resource_code = Column(String(50), nullable=False, comment="资源编码")
    action_code = Column(String(50), nullable=False, comment="动作编码")
    scope_mode = Column(String(20), default="CUSTOM", nullable=False, comment="范围模式：ALL, SELF, CUSTOM")
    effect = Column(String(20), default="ALLOW", nullable=False, comment="生效方式：ALLOW, DENY")
    priority = Column(Integer, default=100, nullable=False, comment="优先级")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    source_type = Column(String(20), default="MANUAL", nullable=False, comment="来源类型：MANUAL, ERP")
    source_system = Column(String(50), default="shopview", nullable=False, comment="来源系统")
    external_scope_id = Column(String(100), comment="外部数据范围ID")
    external_scope_name = Column(String(200), comment="外部数据范围名称")
    synced_at = Column(DateTime, comment="外部同步时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class DataPolicyItem(Base):
    """数据权限策略维度项"""
    __tablename__ = "data_policy_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    policy_id = Column(BigInteger, ForeignKey("data_policies.id"), nullable=False, index=True)
    dimension_type = Column(String(20), nullable=False, comment="维度类型：store, department, group, floor, unit, supplier, brand, category")
    dimension_value = Column(String(100), nullable=False, comment="维度值")
    include_children = Column(Boolean, default=False, nullable=False, comment="是否包含下级")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class LoginLog(Base):
    """登录日志表"""
    __tablename__ = "login_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), comment="用户ID")
    identity_type = Column(String(20), comment="登录身份类型")
    identifier = Column(String(200), comment="登录标识")
    login_result = Column(String(20), nullable=False, comment="登录结果：SUCCESS, FAILED")
    ip_address = Column(String(64), comment="IP地址")
    user_agent = Column(Text, comment="客户端信息")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), comment="用户ID")
    action_code = Column(String(100), nullable=False, comment="动作编码")
    resource_code = Column(String(50), nullable=False, comment="资源编码")
    target_id = Column(String(100), comment="目标对象ID")
    detail = Column(JSON, comment="详情")
    ip_address = Column(String(64), comment="IP地址")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")


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


# ==================== ODS数据表 ====================

class OdsSaleGoodsList(Base):
    """销售商品清单表 - ODS数据"""
    __tablename__ = "ods_salegoodslist"

    # 复合主键 - 基于业务字段
    sgldate = Column(Date, nullable=False, comment="销售日期")
    sgltpid = Column(String(2), nullable=False, comment="终端ID")
    sglsummary = Column(String(10), nullable=False, comment="汇总码")
    sglmarket = Column(String(20), nullable=False, comment="市场")
    sglmfid = Column(String(20), nullable=False, comment="厂商ID")
    sglgdid = Column(String(20), nullable=False, comment="商品ID")
    sglbarcode = Column(String(20), nullable=False, comment="条码")
    sglgdtype = Column(String(1), nullable=False, comment="商品类型")
    sglcatid = Column(String(10), nullable=False, comment="类别ID")
    sgltaxtype = Column(String(1), nullable=False, comment="税种类型")
    sglxstax = Column(Numeric(8, 4), nullable=False, comment="销售税率")
    sglxftax = Column(Numeric(8, 4), nullable=False, comment="消费税率")
    sglppcode = Column(String(10), nullable=False, comment="促销代码")
    sgluid = Column(String(6), nullable=False, default='00', comment="用户ID")
    sglhsrq = Column(Date, nullable=False, comment="核算日期")
    sglbatchno = Column(String(20), nullable=False, default='0', comment="批次号")
    sglsupid = Column(String(20), nullable=False, comment="供应商ID")
    sglanalcode = Column(String(20), nullable=True, comment="分析代码")
    
    # 单据信息 - 作为主键的一部分
    sglbillno = Column(Numeric(), nullable=False, comment="单据号")
    sglrowno = Column(Numeric(), nullable=False, comment="行号")
    
    # 设置复合主键
    __table_args__ = (
        PrimaryKeyConstraint('sgldate', 'sgltpid', 'sglsummary', 'sglmarket', 
                           'sglmfid', 'sglgdid', 'sglbarcode', 'sglbillno', 'sglrowno',
                           name='pk_ods_salegoodslist'),
    )
    
    # 价格和数量字段
    sglsj = Column(Numeric(16, 4), nullable=False, comment="售价")
    sglkl = Column(Numeric(5, 4), nullable=False, comment="扣率")
    sgljs = Column(Numeric(16, 4), nullable=False, comment="结算价")
    sglsl = Column(Numeric(16, 4), nullable=False, comment="数量")
    sglsjje = Column(Numeric(16, 4), nullable=False, comment="售价金额")
    
    # 收入相关字段
    sglxssr = Column(Numeric(16, 4), nullable=False, comment="销售收入")
    sglxsse = Column(Numeric(16, 4), nullable=False, comment="销售税额")
    sglxfse = Column(Numeric(16, 4), nullable=False, comment="消费税额")
    sglqtsr = Column(Numeric(16, 4), nullable=False, comment="其他收入")
    sglsysy = Column(Numeric(16, 4), nullable=False, comment="损益收入")
    sglpopsr = Column(Numeric(16, 4), nullable=False, comment="POP收入")
    sglcustsr = Column(Numeric(16, 4), nullable=False, comment="客户收入")
    sglfcdsr = Column(Numeric(16, 4), nullable=False, comment="返厂单收入")
    sglpfsr = Column(Numeric(16, 4), nullable=False, comment="批发收入")
    sglyxssr = Column(Numeric(16, 4), nullable=False, comment="有效销售收入")
    
    # 折扣相关字段
    sgltotzk = Column(Numeric(16, 4), nullable=False, comment="总折扣")
    sglsupzk = Column(Numeric(16, 4), nullable=False, comment="供应商折扣")
    sglpopzk = Column(Numeric(16, 4), nullable=False, comment="POP折扣")
    sglcustzk = Column(Numeric(16, 4), nullable=False, comment="客户折扣")
    sglfcdzk = Column(Numeric(16, 4), nullable=False, comment="返厂单折扣")
    sglpfzk = Column(Numeric(16, 4), nullable=False, comment="批发折扣")
    sglgrantzk = Column(Numeric(16, 4), nullable=False, comment="授权折扣")
    sglyjhx = Column(Numeric(16, 4), nullable=False, comment="优惠活动")
    sglzszk = Column(Numeric(16, 4), nullable=False, comment="赠送折扣")
    sglthss = Column(Numeric(16, 4), nullable=False, comment="退货损失")
    sgladjustzk = Column(Numeric(16, 4), nullable=False, comment="调整折扣")
    
    # 支付方式字段
    sglcash = Column(Numeric(16, 4), nullable=False, comment="现金")
    sglcheck = Column(Numeric(16, 4), nullable=False, comment="支票")
    sglccard = Column(Numeric(16, 4), nullable=False, comment="信用卡")
    sglfcard = Column(Numeric(16, 4), nullable=False, comment="储值卡")
    sglgcert = Column(Numeric(16, 4), nullable=False, comment="购物券")
    sglgzje = Column(Numeric(16, 4), nullable=False, comment="购物券金额")
    sglopay = Column(Numeric(16, 4), nullable=False, comment="其他支付")
    
    # 扩展字段
    sgltimes = Column(Numeric(16, 4), nullable=True, comment="次数")
    sgln1 = Column(Numeric(16, 4), nullable=True, comment="数值1")
    sgln2 = Column(Numeric(16, 4), nullable=True, comment="数值2")
    sgln3 = Column(Numeric(16, 4), nullable=True, comment="数值3")
    sgln4 = Column(Numeric(16, 4), nullable=True, comment="数值4")
    sgln5 = Column(Numeric(16, 4), nullable=True, comment="数值5")
    sglvc1 = Column(String(20), nullable=True, comment="字符1")
    sglvc2 = Column(String(20), nullable=True, comment="字符2")
    sglvc3 = Column(String(64), nullable=True, comment="字符3")
    sglwmid = Column(String(1), nullable=False, default='1', comment="仓库ID")
    sglfqje = Column(Numeric(16, 4), nullable=True, default=0, comment="分期金额")
    sglsqje = Column(Numeric(16, 4), nullable=True, default=0, comment="申请金额")
    sglqxssr = Column(Numeric(16, 4), nullable=True, default=0, comment="取消销售收入")
    
    # 更多数值字段
    sgln6 = Column(Numeric(16, 4), nullable=True, comment="数值6")
    sgln7 = Column(Numeric(16, 4), nullable=True, comment="数值7")
    sgln8 = Column(Numeric(16, 4), nullable=True, comment="数值8")
    sgln9 = Column(Numeric(16, 4), nullable=True, comment="数值9")
    sgln10 = Column(Numeric(16, 4), nullable=True, comment="数值10")
    
    # 信用卡收入字段
    sglxyksr1 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入1")
    sglxyksr2 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入2")
    sglxyksr3 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入3")
    sglxyksr4 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入4")
    sglxyksr5 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入5")
    sglxyksr6 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入6")
    sglxyksr7 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入7")
    sglxyksr8 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入8")
    sglxyksr9 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入9")
    sglxyksr10 = Column(Numeric(16, 4), nullable=True, default=0, comment="信用卡收入10")
    
    # 单据信息
    sglbillno = Column(Numeric(), nullable=False, comment="单据号")
    sglrowno = Column(Numeric(), nullable=False, comment="行号")
    sglbasekl = Column(Numeric(5, 4), nullable=True, comment="基础扣率")
    
    # 更多数值字段
    sgln11 = Column(Numeric(), nullable=True, comment="数值11")
    sgln12 = Column(Numeric(), nullable=True, comment="数值12")
    sgln13 = Column(Numeric(), nullable=True, comment="数值13")
    sgln14 = Column(Numeric(), nullable=True, comment="数值14")
    sgln15 = Column(Numeric(), nullable=True, comment="数值15")
    sgln16 = Column(Numeric(), nullable=True, comment="数值16")
    sgln17 = Column(Numeric(), nullable=True, comment="数值17")
    sgln18 = Column(Numeric(), nullable=True, comment="数值18")
    sgln19 = Column(Numeric(), nullable=True, comment="数值19")
    sgln20 = Column(Numeric(), nullable=True, comment="数值20")
    sgln21 = Column(Numeric(), nullable=True, comment="数值21")
    sgln22 = Column(Numeric(), nullable=True, comment="数值22")
    sgln23 = Column(Numeric(), nullable=True, comment="数值23")
    sgln24 = Column(Numeric(), nullable=True, comment="数值24")
    sgln25 = Column(Numeric(), nullable=True, comment="数值25")
    
    # 更多字符字段
    sglvc4 = Column(String(20), nullable=True, comment="字符4")
    sglvc5 = Column(String(20), nullable=True, comment="字符5")
    sglvc6 = Column(String(20), nullable=True, comment="字符6")
    sglvc7 = Column(String(20), nullable=True, comment="字符7")
    sglvc8 = Column(String(20), nullable=True, comment="字符8")
    sglvc9 = Column(String(20), nullable=True, comment="字符9")
    sglvc10 = Column(String(20), nullable=True, comment="字符10")
    sglvc11 = Column(String(20), nullable=True, comment="字符11")
    sglvc12 = Column(String(20), nullable=True, comment="字符12")
    sglvc13 = Column(String(20), nullable=True, comment="字符13")
    sglvc14 = Column(String(20), nullable=True, comment="字符14")
    sglvc15 = Column(String(20), nullable=True, comment="字符15")
    
    # 销售相关字段
    sglsaledate = Column(Date, nullable=True, comment="销售日期")
    sglnetml = Column(Numeric(), nullable=True, comment="网络毛利")
    sglcardtype = Column(String(10), nullable=True, comment="卡类型")
    sglyjid = Column(String(20), nullable=True, comment="业务员ID")
    sglinvno = Column(Numeric(), nullable=True, comment="发票号")
    sglchecker = Column(String(20), nullable=True, comment="审核人")
    sglposcls = Column(String(1), nullable=True, comment="POS分类")
    sglshdate = Column(Date, nullable=True, comment="审核日期")
    sgltmtype = Column(String(1), nullable=True, default='0', comment="终端类型")
    sglmd = Column(String(1), nullable=True, default='1', comment="模式")
    
    # 返佣和VIP字段
    sglfysl = Column(Numeric(16, 4), nullable=True, comment="返佣数量")
    sglvip1sr = Column(Numeric(16, 4), nullable=True, comment="VIP1收入")
    sglvip2sr = Column(Numeric(16, 4), nullable=True, comment="VIP2收入")
    sglvip3sr = Column(Numeric(16, 4), nullable=True, comment="VIP3收入")
    sglvip4sr = Column(Numeric(16, 4), nullable=True, comment="VIP4收入")
    sglvip5sr = Column(Numeric(16, 4), nullable=True, comment="VIP5收入")
    
    # 信用卡费用字段
    sglxykfy1 = Column(Numeric(), nullable=True, comment="信用卡费用1")
    sglxykfy2 = Column(Numeric(), nullable=True, comment="信用卡费用2")
    sglxykfy3 = Column(Numeric(), nullable=True, comment="信用卡费用3")
    sglxykfy4 = Column(Numeric(), nullable=True, comment="信用卡费用4")
    sglxykfy5 = Column(Numeric(), nullable=True, comment="信用卡费用5")
    sglxykfy6 = Column(Numeric(), nullable=True, comment="信用卡费用6")
    sglxykfy7 = Column(Numeric(), nullable=True, comment="信用卡费用7")
    sglxykfy8 = Column(Numeric(), nullable=True, comment="信用卡费用8")
    sglxykfy9 = Column(Numeric(), nullable=True, comment="信用卡费用9")
    sglxykfy10 = Column(Numeric(), nullable=True, comment="信用卡费用10")
    
    # 其他字段
    sglspsx = Column(String(20), nullable=True, default='0', comment="商品属性")
    sgljjtax = Column(Numeric(8, 4), nullable=True, comment="基金税")
    sgln26 = Column(Numeric(), nullable=True, comment="数值26")
    sgln27 = Column(Numeric(), nullable=True, comment="数值27")
    sgln28 = Column(Numeric(), nullable=True, comment="数值28")
    sgln29 = Column(Numeric(), nullable=True, comment="数值29")
    
    # 创建时间戳
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
