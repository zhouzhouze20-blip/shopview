"""
装修流程模块数据模型
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


PROJECT_STATUS_VALUES = (
    "DRAFT",
    "PENDING_PROPERTY_REVIEW",
    "PENDING_LEADER_APPROVAL",
    "PENDING_DEPOSIT_CONFIRM",
    "PENDING_ENTRY_CONFIRM",
    "IN_CONSTRUCTION",
    "PENDING_ACCEPTANCE",
    "PENDING_SETTLEMENT",
    "PENDING_REFUND_APPROVAL",
    "COMPLETED",
    "REJECTED",
    "CANCELLED",
)

WORKFLOW_INSTANCE_STATUS_VALUES = (
    "RUNNING",
    "COMPLETED",
    "REJECTED",
    "CANCELLED",
)

WORKFLOW_NODE_STATUS_VALUES = (
    "PENDING",
    "APPROVED",
    "REJECTED",
    "RETURNED",
    "SKIPPED",
)

WORKFLOW_ACTION_VALUES = (
    "SUBMIT",
    "APPROVE",
    "REJECT",
    "RETURN",
    "CANCEL",
    "CONFIRM",
)

SPACE_TYPE_VALUES = ("HALL", "UNIT")


class DecorationProject(Base):
    """装修项目主表"""

    __tablename__ = "decoration_projects"
    __table_args__ = (
        UniqueConstraint("project_no", name="uq_decoration_projects_project_no"),
        CheckConstraint(
            "current_status IN ('DRAFT','PENDING_PROPERTY_REVIEW','PENDING_LEADER_APPROVAL',"
            "'PENDING_DEPOSIT_CONFIRM','PENDING_ENTRY_CONFIRM','IN_CONSTRUCTION',"
            "'PENDING_ACCEPTANCE','PENDING_SETTLEMENT','PENDING_REFUND_APPROVAL',"
            "'COMPLETED','REJECTED','CANCELLED')",
            name="ck_decoration_projects_status",
        ),
        Index("ix_decoration_projects_store_status", "store_id", "current_status"),
        Index("ix_decoration_projects_applicant", "applicant_user_id"),
        Index("ix_decoration_projects_current_assignee", "current_assignee_user_id"),
        Index("ix_decoration_projects_planned_entry_date", "planned_entry_date"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_no = Column(String(50), nullable=False, comment="项目编号")
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False, comment="门店ID")
    department_id = Column(BigInteger, ForeignKey("departments.id"), nullable=False, comment="发起部门ID")
    applicant_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, comment="发起人ID")
    applicant_phone = Column(String(30), nullable=False, comment="发起人联系电话")
    brand_name = Column(String(200), nullable=False, comment="品牌名称")
    tenant_name = Column(String(200), comment="商户主体名称")
    contractor_name = Column(String(200), nullable=False, comment="施工单位")
    contractor_contact = Column(String(100), nullable=False, comment="施工负责人")
    contractor_phone = Column(String(30), nullable=False, comment="施工负责人电话")
    fitout_type = Column(String(30), nullable=False, comment="装修类型")
    fitout_reason = Column(String(200), nullable=False, comment="装修原因")
    description = Column(Text, comment="装修说明")
    planned_entry_date = Column(Date, nullable=False, comment="计划进场日期")
    planned_finish_date = Column(Date, nullable=False, comment="计划完工日期")
    actual_entry_date = Column(Date, comment="实际进场日期")
    actual_finish_date = Column(Date, comment="实际完工日期")
    applied_area = Column(Numeric(12, 2), nullable=False, comment="申请面积")
    deposit_amount = Column(Numeric(12, 2), comment="保证金应缴金额")
    actual_measured_area = Column(Numeric(12, 2), comment="实测面积")
    actual_power_usage = Column(Numeric(12, 2), comment="实际用电")
    power_fee_amount = Column(Numeric(12, 2), comment="电费金额")
    deduction_amount = Column(Numeric(12, 2), comment="扣费金额")
    refund_amount = Column(Numeric(12, 2), comment="应退金额")
    current_status = Column(String(40), nullable=False, server_default="DRAFT", comment="当前状态")
    current_node_code = Column(String(50), comment="当前节点编码")
    current_assignee_user_id = Column(Integer, ForeignKey("users.user_id"), comment="当前处理人ID")
    current_workflow_instance_id = Column(
        BigInteger,
        ForeignKey(
            "workflow_instances.id",
            use_alter=True,
            name="fk_decoration_projects_current_workflow_instance_id",
        ),
        comment="当前流程实例ID",
    )
    is_closed = Column(Boolean, nullable=False, server_default="false", comment="是否闭环")
    closed_at = Column(DateTime, comment="完成时间")
    reject_reason = Column(Text, comment="驳回原因")
    cancel_reason = Column(Text, comment="取消原因")
    oa_ref_no = Column(String(100), comment="OA参考编号")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    spaces = relationship("DecorationProjectSpace", back_populates="project", cascade="all, delete-orphan")
    attachments = relationship("DecorationAttachment", back_populates="project", cascade="all, delete-orphan")
    workflow_instances = relationship(
        "WorkflowInstance",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="WorkflowInstance.project_id",
    )
    property_reviews = relationship("DecorationPropertyReview", back_populates="project", cascade="all, delete-orphan")
    deposit_confirms = relationship("DecorationDepositConfirm", back_populates="project", cascade="all, delete-orphan")
    entry_confirms = relationship("DecorationEntryConfirm", back_populates="project", cascade="all, delete-orphan")
    acceptances = relationship("DecorationAcceptance", back_populates="project", cascade="all, delete-orphan")
    settlements = relationship("DecorationSettlement", back_populates="project", cascade="all, delete-orphan")
    refunds = relationship("DecorationRefund", back_populates="project", cascade="all, delete-orphan")


class DecorationProjectSpace(Base):
    """装修项目空间明细表"""

    __tablename__ = "decoration_project_spaces"
    __table_args__ = (
        CheckConstraint(
            "space_type IN ('HALL','UNIT')",
            name="ck_decoration_project_spaces_space_type",
        ),
        CheckConstraint(
            "(space_type = 'HALL' AND hall_id IS NOT NULL AND business_unit_id IS NULL) OR "
            "(space_type = 'UNIT' AND business_unit_id IS NOT NULL AND hall_id IS NULL)",
            name="ck_decoration_project_spaces_target_ref",
        ),
        Index("ix_decoration_project_spaces_project_id", "project_id"),
        Index("ix_decoration_project_spaces_hall_id", "hall_id"),
        Index("ix_decoration_project_spaces_business_unit_id", "business_unit_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    space_type = Column(String(20), nullable=False, comment="空间类型")
    hall_id = Column(Integer, ForeignKey("halls.hall_id"), comment="厅房ID")
    business_unit_id = Column(BigInteger, ForeignKey("business_units.id"), comment="经营单元ID")
    floor_id = Column(BigInteger, comment="楼层ID冗余")
    space_code = Column(String(100), comment="空间编码冗余")
    space_name = Column(String(200), comment="空间名称冗余")
    applied_area = Column(Numeric(12, 2), comment="申请面积")
    measured_area = Column(Numeric(12, 2), comment="实测面积")
    remarks = Column(Text, comment="备注")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    project = relationship("DecorationProject", back_populates="spaces")


class DecorationAttachment(Base):
    """装修项目附件表"""

    __tablename__ = "decoration_attachments"
    __table_args__ = (
        Index("ix_decoration_attachments_project_id", "project_id"),
        Index("ix_decoration_attachments_type", "attachment_type"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    attachment_type = Column(String(40), nullable=False, comment="附件类型")
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_url = Column(Text, nullable=False, comment="文件地址")
    file_size = Column(BigInteger, comment="文件大小")
    mime_type = Column(String(100), comment="MIME类型")
    uploaded_by = Column(Integer, ForeignKey("users.user_id"), nullable=False, comment="上传人")
    uploaded_at = Column(DateTime, nullable=False, server_default=func.now(), comment="上传时间")
    related_node_code = Column(String(50), comment="关联节点编码")
    extra_data = Column(JSONB, comment="扩展元数据")

    project = relationship("DecorationProject", back_populates="attachments")


class WorkflowTemplate(Base):
    """流程模板表"""

    __tablename__ = "workflow_templates"
    __table_args__ = (
        UniqueConstraint("template_code", name="uq_workflow_templates_template_code"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    template_code = Column(String(50), nullable=False, comment="模板编码")
    template_name = Column(String(100), nullable=False, comment="模板名称")
    business_type = Column(String(50), nullable=False, comment="业务类型")
    scene_code = Column(String(50), nullable=False, comment="场景编码")
    store_id = Column(Integer, ForeignKey("stores.store_id"), comment="门店ID，为空表示通用")
    is_active = Column(Boolean, nullable=False, server_default="true", comment="是否启用")
    version_no = Column(Integer, nullable=False, server_default="1", comment="版本号")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    nodes = relationship("WorkflowTemplateNode", back_populates="template", cascade="all, delete-orphan")
    instances = relationship("WorkflowInstance", back_populates="template")


class WorkflowTemplateNode(Base):
    """流程模板节点表"""

    __tablename__ = "workflow_template_nodes"
    __table_args__ = (
        UniqueConstraint("template_id", "node_code", name="uq_workflow_template_nodes_code"),
        UniqueConstraint("template_id", "node_order", name="uq_workflow_template_nodes_order"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    template_id = Column(BigInteger, ForeignKey("workflow_templates.id", ondelete="CASCADE"), nullable=False, comment="流程模板ID")
    node_code = Column(String(50), nullable=False, comment="节点编码")
    node_name = Column(String(100), nullable=False, comment="节点名称")
    node_order = Column(Integer, nullable=False, comment="节点顺序")
    node_type = Column(String(30), nullable=False, comment="节点类型")
    role_code = Column(String(50), nullable=False, comment="默认责任角色编码")
    allow_reject = Column(Boolean, nullable=False, server_default="false", comment="是否允许驳回")
    allow_return = Column(Boolean, nullable=False, server_default="false", comment="是否允许退回")
    return_target = Column(String(50), comment="默认退回目标节点")
    is_final_node = Column(Boolean, nullable=False, server_default="false", comment="是否结束节点")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    template = relationship("WorkflowTemplate", back_populates="nodes")
    instance_nodes = relationship("WorkflowInstanceNode", back_populates="template_node")


class WorkflowInstance(Base):
    """流程实例表"""

    __tablename__ = "workflow_instances"
    __table_args__ = (
        CheckConstraint(
            "status IN ('RUNNING','COMPLETED','REJECTED','CANCELLED')",
            name="ck_workflow_instances_status",
        ),
        Index("ix_workflow_instances_project_id", "project_id"),
        Index("ix_workflow_instances_current_assignee", "current_assignee_user_id"),
        Index("ix_workflow_instances_status", "status"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    template_id = Column(BigInteger, ForeignKey("workflow_templates.id"), nullable=False, comment="流程模板ID")
    flow_type = Column(String(30), nullable=False, comment="流程类型 ENTRY/REFUND")
    status = Column(String(30), nullable=False, server_default="RUNNING", comment="流程实例状态")
    current_node_code = Column(String(50), comment="当前节点编码")
    current_assignee_user_id = Column(Integer, ForeignKey("users.user_id"), comment="当前处理人")
    started_by = Column(Integer, ForeignKey("users.user_id"), nullable=False, comment="发起人")
    started_at = Column(DateTime, nullable=False, server_default=func.now(), comment="发起时间")
    completed_at = Column(DateTime, comment="完成时间")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    project = relationship("DecorationProject", back_populates="workflow_instances", foreign_keys=[project_id])
    template = relationship("WorkflowTemplate", back_populates="instances")
    nodes = relationship("WorkflowInstanceNode", back_populates="workflow_instance", cascade="all, delete-orphan")
    actions = relationship("WorkflowAction", back_populates="workflow_instance", cascade="all, delete-orphan")


class WorkflowInstanceNode(Base):
    """流程实例节点表"""

    __tablename__ = "workflow_instance_nodes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED','RETURNED','SKIPPED')",
            name="ck_workflow_instance_nodes_status",
        ),
        Index("ix_workflow_instance_nodes_instance_id", "workflow_instance_id"),
        Index("ix_workflow_instance_nodes_assignee_status", "assignee_user_id", "status"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    workflow_instance_id = Column(BigInteger, ForeignKey("workflow_instances.id", ondelete="CASCADE"), nullable=False, comment="流程实例ID")
    template_node_id = Column(BigInteger, ForeignKey("workflow_template_nodes.id"), nullable=False, comment="模板节点ID")
    node_code = Column(String(50), nullable=False, comment="节点编码")
    node_name = Column(String(100), nullable=False, comment="节点名称")
    node_order = Column(Integer, nullable=False, comment="节点顺序")
    assignee_user_id = Column(Integer, ForeignKey("users.user_id"), comment="处理人")
    status = Column(String(30), nullable=False, server_default="PENDING", comment="节点状态")
    arrived_at = Column(DateTime, comment="到达时间")
    acted_at = Column(DateTime, comment="处理时间")
    action_result = Column(String(30), comment="处理结果")
    comment = Column(Text, comment="节点意见")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    workflow_instance = relationship("WorkflowInstance", back_populates="nodes")
    template_node = relationship("WorkflowTemplateNode", back_populates="instance_nodes")
    actions = relationship("WorkflowAction", back_populates="workflow_instance_node")


class WorkflowAction(Base):
    """流程动作记录表"""

    __tablename__ = "workflow_actions"
    __table_args__ = (
        CheckConstraint(
            "action_code IN ('SUBMIT','APPROVE','REJECT','RETURN','CANCEL','CONFIRM')",
            name="ck_workflow_actions_action_code",
        ),
        Index("ix_workflow_actions_instance_id", "workflow_instance_id"),
        Index("ix_workflow_actions_actor_user_id", "actor_user_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    workflow_instance_id = Column(BigInteger, ForeignKey("workflow_instances.id", ondelete="CASCADE"), nullable=False, comment="流程实例ID")
    workflow_instance_node_id = Column(BigInteger, ForeignKey("workflow_instance_nodes.id", ondelete="SET NULL"), comment="流程实例节点ID")
    action_code = Column(String(30), nullable=False, comment="动作编码")
    action_result = Column(String(30), comment="动作结果")
    actor_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, comment="操作人")
    action_comment = Column(Text, comment="操作意见")
    action_data = Column(JSONB, comment="扩展数据")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    workflow_instance = relationship("WorkflowInstance", back_populates="actions")
    workflow_instance_node = relationship("WorkflowInstanceNode", back_populates="actions")


class DecorationPropertyReview(Base):
    """物业审图记录表"""

    __tablename__ = "decoration_property_reviews"
    __table_args__ = (
        Index("ix_decoration_property_reviews_project_id", "project_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    workflow_instance_id = Column(BigInteger, ForeignKey("workflow_instances.id", ondelete="SET NULL"), comment="流程实例ID")
    review_result = Column(String(30), nullable=False, comment="审图结果 APPROVED/RETURNED")
    review_comment = Column(Text, nullable=False, comment="审图意见")
    rectification_requirements = Column(Text, comment="整改要求")
    reviewed_by = Column(Integer, ForeignKey("users.user_id"), nullable=False, comment="审图人")
    reviewed_at = Column(DateTime, nullable=False, server_default=func.now(), comment="审图时间")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    project = relationship("DecorationProject", back_populates="property_reviews")


class DecorationDepositConfirm(Base):
    """保证金确认表"""

    __tablename__ = "decoration_deposit_confirms"
    __table_args__ = (
        Index("ix_decoration_deposit_confirms_project_id", "project_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    workflow_instance_id = Column(BigInteger, ForeignKey("workflow_instances.id", ondelete="SET NULL"), comment="流程实例ID")
    deposit_amount_expected = Column(Numeric(12, 2), nullable=False, comment="应缴金额")
    deposit_amount_received = Column(Numeric(12, 2), nullable=False, comment="实缴金额")
    received_date = Column(Date, nullable=False, comment="到账日期")
    receipt_attachment_id = Column(BigInteger, ForeignKey("decoration_attachments.id", ondelete="SET NULL"), comment="收款凭证附件ID")
    finance_comment = Column(Text, comment="财务备注")
    status = Column(String(30), nullable=False, server_default="CONFIRMED", comment="确认状态")
    confirmed_by = Column(Integer, ForeignKey("users.user_id"), nullable=False, comment="确认人")
    confirmed_at = Column(DateTime, nullable=False, server_default=func.now(), comment="确认时间")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    project = relationship("DecorationProject", back_populates="deposit_confirms")


class DecorationEntryConfirm(Base):
    """进场确认表"""

    __tablename__ = "decoration_entry_confirms"
    __table_args__ = (
        Index("ix_decoration_entry_confirms_project_id", "project_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    workflow_instance_id = Column(BigInteger, ForeignKey("workflow_instances.id", ondelete="SET NULL"), comment="流程实例ID")
    entry_result = Column(String(30), nullable=False, comment="进场结果 APPROVED/DEFERRED/RETURNED")
    entry_date = Column(Date, comment="进场日期")
    requirements = Column(Text, comment="现场要求")
    security_note = Column(Text, comment="保安协同说明")
    confirmed_by = Column(Integer, ForeignKey("users.user_id"), nullable=False, comment="确认人")
    confirmed_at = Column(DateTime, nullable=False, server_default=func.now(), comment="确认时间")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    project = relationship("DecorationProject", back_populates="entry_confirms")


class DecorationAcceptance(Base):
    """完工验收表"""

    __tablename__ = "decoration_acceptances"
    __table_args__ = (
        Index("ix_decoration_acceptances_project_id", "project_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    acceptance_result = Column(String(30), nullable=False, comment="验收结果 APPROVED/RECTIFICATION")
    acceptance_date = Column(Date, nullable=False, comment="验收日期")
    acceptance_comment = Column(Text, nullable=False, comment="验收意见")
    rectification_items = Column(JSONB, comment="整改项")
    accepted_by = Column(Integer, ForeignKey("users.user_id"), nullable=False, comment="验收人")
    accepted_at = Column(DateTime, nullable=False, server_default=func.now(), comment="验收时间")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")

    project = relationship("DecorationProject", back_populates="acceptances")


class DecorationSettlement(Base):
    """结算确认表"""

    __tablename__ = "decoration_settlements"
    __table_args__ = (
        Index("ix_decoration_settlements_project_id", "project_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    measured_area = Column(Numeric(12, 2), nullable=False, comment="实测面积")
    actual_power_usage = Column(Numeric(12, 2), nullable=False, comment="实际用电")
    power_fee_amount = Column(Numeric(12, 2), nullable=False, comment="电费金额")
    deduction_items = Column(JSONB, comment="扣费明细")
    deduction_amount = Column(Numeric(12, 2), comment="扣费金额")
    refund_amount = Column(Numeric(12, 2), nullable=False, comment="应退金额")
    settlement_comment = Column(Text, comment="结算说明")
    confirmed_by_property = Column(Integer, ForeignKey("users.user_id"), comment="物业确认人")
    confirmed_by_finance = Column(Integer, ForeignKey("users.user_id"), comment="财务确认人")
    confirmed_at = Column(DateTime, comment="确认时间")
    status = Column(String(30), nullable=False, server_default="CONFIRMED", comment="结算状态")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    project = relationship("DecorationProject", back_populates="settlements")


class DecorationRefund(Base):
    """退款审批与执行结果表"""

    __tablename__ = "decoration_refunds"
    __table_args__ = (
        Index("ix_decoration_refunds_project_id", "project_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    project_id = Column(BigInteger, ForeignKey("decoration_projects.id", ondelete="CASCADE"), nullable=False, comment="装修项目ID")
    workflow_instance_id = Column(BigInteger, ForeignKey("workflow_instances.id", ondelete="SET NULL"), comment="流程实例ID")
    approved_refund_amount = Column(Numeric(12, 2), comment="审批通过金额")
    final_refund_amount = Column(Numeric(12, 2), comment="最终退款金额")
    leader_comment = Column(Text, comment="领导审批意见")
    finance_comment = Column(Text, comment="财务备注")
    refund_date = Column(Date, comment="退款日期")
    refund_proof_attachment_id = Column(BigInteger, ForeignKey("decoration_attachments.id", ondelete="SET NULL"), comment="退款凭证附件ID")
    status = Column(String(30), nullable=False, server_default="PENDING", comment="退款状态")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    project = relationship("DecorationProject", back_populates="refunds")
