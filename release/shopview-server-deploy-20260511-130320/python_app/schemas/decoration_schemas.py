"""
装修流程 Pydantic schemas
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


DecorationProjectStatus = Literal[
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
]

FlowType = Literal["ENTRY", "REFUND"]
SpaceType = Literal["UNIT"]


class DecorationProjectSpaceBase(BaseModel):
    space_type: SpaceType
    business_unit_id: Optional[int] = None
    floor_id: Optional[int] = None
    space_code: Optional[str] = None
    space_name: Optional[str] = None
    applied_area: Optional[Decimal] = None
    measured_area: Optional[Decimal] = None
    remarks: Optional[str] = None


class DecorationProjectSpaceCreate(DecorationProjectSpaceBase):
    pass


class DecorationProjectSpaceSchema(DecorationProjectSpaceBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DecorationProjectBase(BaseModel):
    store_id: int
    department_id: int
    applicant_phone: str
    contract_no: str
    brand_name: str
    tenant_name: Optional[str] = None
    contractor_name: str
    contractor_contact: str
    contractor_phone: str
    fitout_type: Literal["NEW", "REMODEL", "REFRESH"]
    fitout_reason: str
    description: Optional[str] = None
    planned_entry_date: date
    planned_finish_date: date
    applied_area: Decimal


class DecorationProjectCreate(DecorationProjectBase):
    spaces: List[DecorationProjectSpaceCreate]


class DecorationProjectUpdate(BaseModel):
    applicant_phone: Optional[str] = None
    brand_name: Optional[str] = None
    tenant_name: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_contact: Optional[str] = None
    contractor_phone: Optional[str] = None
    fitout_type: Optional[Literal["NEW", "REMODEL", "REFRESH"]] = None
    fitout_reason: Optional[str] = None
    description: Optional[str] = None
    planned_entry_date: Optional[date] = None
    planned_finish_date: Optional[date] = None
    applied_area: Optional[Decimal] = None
    spaces: Optional[List[DecorationProjectSpaceCreate]] = None


class DecorationProjectListItem(BaseModel):
    id: int
    project_no: str
    store_id: int
    store_name: Optional[str] = None
    contract_no: Optional[str] = None
    brand_name: str
    contractor_name: str
    applicant_user_id: int
    applicant_name: Optional[str] = None
    current_status: DecorationProjectStatus
    current_status_name: Optional[str] = None
    current_node_code: Optional[str] = None
    current_assignee_user_id: Optional[int] = None
    current_assignee_name: Optional[str] = None
    planned_entry_date: date
    planned_finish_date: date
    updated_at: Optional[datetime] = None


class DecorationWorkflowSummary(BaseModel):
    flow_type: Optional[FlowType] = None
    current_node_code: Optional[str] = None
    current_assignee_user_id: Optional[int] = None


class DecorationNodeResultSummary(BaseModel):
    property_review: Optional[Dict[str, Any]] = None
    deposit_confirm: Optional[Dict[str, Any]] = None
    entry_confirm: Optional[Dict[str, Any]] = None
    acceptance: Optional[Dict[str, Any]] = None
    settlement: Optional[Dict[str, Any]] = None
    refund: Optional[Dict[str, Any]] = None


class DecorationProjectDetail(BaseModel):
    id: int
    project_no: str
    store_id: int
    store_name: Optional[str] = None
    department_id: int
    department_name: Optional[str] = None
    applicant_user_id: int
    applicant_name: Optional[str] = None
    applicant_phone: str
    contract_no: Optional[str] = None
    contract_status: Optional[str] = None
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    brand_name: str
    tenant_name: Optional[str] = None
    contractor_name: str
    contractor_contact: str
    contractor_phone: str
    fitout_type: str
    fitout_reason: str
    description: Optional[str] = None
    planned_entry_date: date
    planned_finish_date: date
    actual_entry_date: Optional[date] = None
    actual_finish_date: Optional[date] = None
    applied_area: Decimal
    deposit_amount: Optional[Decimal] = None
    actual_measured_area: Optional[Decimal] = None
    actual_power_usage: Optional[Decimal] = None
    power_fee_amount: Optional[Decimal] = None
    deduction_amount: Optional[Decimal] = None
    refund_amount: Optional[Decimal] = None
    current_status: DecorationProjectStatus
    current_node_code: Optional[str] = None
    current_assignee_user_id: Optional[int] = None
    current_assignee_name: Optional[str] = None
    is_closed: bool
    closed_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    cancel_reason: Optional[str] = None
    oa_ref_no: Optional[str] = None
    spaces: List[DecorationProjectSpaceSchema]
    attachments: List["DecorationAttachmentSchema"] = []
    workflow_summary: Optional[DecorationWorkflowSummary] = None
    node_results: Optional[DecorationNodeResultSummary] = None
    available_actions: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class DecorationAttachmentCreate(BaseModel):
    attachment_type: str
    file_name: str
    file_url: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    related_node_code: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class DecorationAttachmentSchema(DecorationAttachmentCreate):
    id: int
    project_id: int
    uploaded_by: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class DecorationTodoItem(BaseModel):
    workflow_instance_node_id: int
    project_id: int
    project_no: str
    node_code: str
    node_name: str
    store_name: Optional[str] = None
    brand_name: str
    applicant_name: Optional[str] = None
    current_status: DecorationProjectStatus
    arrived_at: Optional[datetime] = None
    is_overdue: bool = False


class WorkflowInstanceNodeSchema(BaseModel):
    id: int
    node_code: str
    node_name: str
    node_order: int
    assignee_user_id: Optional[int] = None
    status: str
    arrived_at: Optional[datetime] = None
    acted_at: Optional[datetime] = None
    action_result: Optional[str] = None
    comment: Optional[str] = None


class WorkflowInstanceSchema(BaseModel):
    id: int
    flow_type: FlowType
    status: str
    current_node_code: Optional[str] = None
    nodes: List[WorkflowInstanceNodeSchema]


class DecorationWorkflowDetail(BaseModel):
    workflow_instances: List[WorkflowInstanceSchema]


class DecorationTimelineItem(BaseModel):
    time: datetime
    type: str
    operator_name: Optional[str] = None
    content: str


class DecorationActionResponse(BaseModel):
    message: str
    project_id: int
    current_status: DecorationProjectStatus
    current_node_code: Optional[str] = None


class DecorationSubmitPayload(BaseModel):
    comment: Optional[str] = None


class DecorationCancelPayload(BaseModel):
    reason: str


class DecorationPropertyReviewPayload(BaseModel):
    review_result: Literal["APPROVED", "RETURNED"]
    review_comment: str
    rectification_requirements: Optional[str] = None


class DecorationLeaderApprovalPayload(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    comment: str


class DecorationDepositConfirmPayload(BaseModel):
    deposit_amount_expected: Decimal
    deposit_amount_received: Decimal
    received_date: date
    receipt_attachment_id: Optional[int] = None
    finance_comment: Optional[str] = None
    action: Literal["CONFIRM", "RETURN"] = "CONFIRM"


class DecorationEntryConfirmPayload(BaseModel):
    entry_result: Literal["APPROVED", "DEFERRED", "RETURNED"]
    entry_date: Optional[date] = None
    requirements: Optional[str] = None
    security_note: Optional[str] = None


class DecorationCompletionSubmitPayload(BaseModel):
    actual_finish_date: date
    comment: Optional[str] = None


class DecorationAcceptancePayload(BaseModel):
    acceptance_result: Literal["APPROVED", "RECTIFICATION"]
    acceptance_date: date
    acceptance_comment: str
    rectification_items: Optional[List[Dict[str, Any]]] = None


class DecorationSettlementItem(BaseModel):
    item_name: str
    amount: Decimal


class DecorationSettlementPayload(BaseModel):
    measured_area: Decimal
    actual_power_usage: Decimal
    power_fee_amount: Decimal
    deduction_items: Optional[List[DecorationSettlementItem]] = None
    deduction_amount: Optional[Decimal] = None
    refund_amount: Decimal
    settlement_comment: Optional[str] = None


class DecorationRefundApprovalPayload(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    approved_refund_amount: Optional[Decimal] = None
    comment: str


class DecorationRefundConfirmPayload(BaseModel):
    final_refund_amount: Decimal
    refund_date: date
    refund_proof_attachment_id: Optional[int] = None
    comment: Optional[str] = None


class DecorationMetaOption(BaseModel):
    label: str
    value: str


class DecorationMetaStore(BaseModel):
    store_id: int
    store_name: str


class DecorationMetaDepartment(BaseModel):
    id: int
    dept_name: str
    store_id: int


class DecorationMetaSchema(BaseModel):
    status_options: List[DecorationMetaOption] = []
    attachment_type_options: List[DecorationMetaOption] = []
    fitout_type_options: List[DecorationMetaOption] = []
    stores: List[DecorationMetaStore] = []
    departments: List[DecorationMetaDepartment] = []
    workflow_node_options: List[DecorationMetaOption] = []


DecorationProjectDetail.model_rebuild()
