"""
装修流程 API
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.database import get_db
from models.decoration_models import (
    DecorationAcceptance,
    DecorationAttachment,
    DecorationDepositConfirm,
    DecorationEntryConfirm,
    DecorationProject,
    DecorationProjectSpace,
    DecorationPropertyReview,
    DecorationRefund,
    DecorationSettlement,
    WorkflowAction,
    WorkflowInstance,
    WorkflowInstanceNode,
    WorkflowTemplate,
    WorkflowTemplateNode,
)
from models.models import Department, OperationLog, Role, Store, User, UserRole
from routers.auth import get_current_user
from schemas.decoration_schemas import (
    DecorationAcceptancePayload,
    DecorationActionResponse,
    DecorationAttachmentCreate,
    DecorationAttachmentSchema,
    DecorationCancelPayload,
    DecorationCompletionSubmitPayload,
    DecorationDepositConfirmPayload,
    DecorationEntryConfirmPayload,
    DecorationLeaderApprovalPayload,
    DecorationMetaDepartment,
    DecorationMetaOption,
    DecorationMetaSchema,
    DecorationMetaStore,
    DecorationProjectCreate,
    DecorationProjectDetail,
    DecorationProjectListItem,
    DecorationProjectUpdate,
    DecorationPropertyReviewPayload,
    DecorationRefundApprovalPayload,
    DecorationRefundConfirmPayload,
    DecorationSettlementPayload,
    DecorationSubmitPayload,
    DecorationTimelineItem,
    DecorationTodoItem,
    DecorationWorkflowDetail,
    DecorationWorkflowSummary,
    DecorationNodeResultSummary,
    WorkflowInstanceNodeSchema,
    WorkflowInstanceSchema,
)
from schemas.schemas import BaseResponse


router = APIRouter(prefix="/api/decorations", tags=["decorations"])


PROJECT_STATUS_LABELS = {
    "DRAFT": "草稿",
    "PENDING_PROPERTY_REVIEW": "待物业审图",
    "PENDING_LEADER_APPROVAL": "待领导审批",
    "PENDING_DEPOSIT_CONFIRM": "待保证金确认",
    "PENDING_ENTRY_CONFIRM": "待进场确认",
    "IN_CONSTRUCTION": "施工中",
    "PENDING_ACCEPTANCE": "待完工验收",
    "PENDING_SETTLEMENT": "待结算确认",
    "PENDING_REFUND_APPROVAL": "待退保证金审批",
    "COMPLETED": "已完成",
    "REJECTED": "已驳回",
    "CANCELLED": "已取消",
}

ATTACHMENT_TYPE_OPTIONS = [
    ("DRAWING_DRAFT", "图纸初稿"),
    ("CONSTRUCTION_PLAN", "施工方案"),
    ("CONTRACTOR_LICENSE", "施工单位资质"),
    ("SAFETY_COMMITMENT", "安全承诺书"),
    ("DEPOSIT_RECEIPT", "保证金单据"),
    ("RECTIFICATION_PHOTO", "整改照片"),
    ("ACCEPTANCE_FILE", "验收附件"),
    ("SETTLEMENT_FILE", "结算附件"),
    ("REFUND_PROOF", "退款凭证"),
    ("OTHER", "其他"),
]

FITOUT_TYPE_OPTIONS = [
    ("NEW", "新进场"),
    ("REMODEL", "改造"),
    ("REFRESH", "翻新"),
]


def _role_codes(db: Session, user_id: int) -> set[str]:
    rows = (
        db.query(Role.role_code)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return {row.role_code for row in rows}


def _is_admin_role(role_codes: set[str]) -> bool:
    return bool({"super_admin", "system_admin", "decoration_admin"} & role_codes)


def _require_project(db: Session, project_id: int) -> DecorationProject:
    project = db.query(DecorationProject).filter(DecorationProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="装修项目不存在")
    return project


def _make_project_no(db: Session) -> str:
    prefix = datetime.now().strftime("DEC%Y%m%d")
    count = (
        db.query(DecorationProject)
        .filter(DecorationProject.project_no.like(f"{prefix}%"))
        .count()
    )
    return f"{prefix}{count + 1:03d}"


def _log_operation(db: Session, user_id: int, action_code: str, target_id: Any, detail: dict[str, Any] | None = None) -> None:
    db.add(
        OperationLog(
            user_id=user_id,
            action_code=action_code,
            resource_code="decoration",
            target_id=str(target_id),
            detail=detail or {},
            created_at=datetime.now(),
        )
    )


def _latest_by_project(items: Iterable[Any]) -> Optional[Any]:
    rows = list(items)
    if not rows:
        return None
    rows.sort(key=lambda x: getattr(x, "created_at", None) or getattr(x, "confirmed_at", None) or getattr(x, "reviewed_at", None) or datetime.min)
    return rows[-1]


def _serialize_attachment(row: DecorationAttachment) -> DecorationAttachmentSchema:
    return DecorationAttachmentSchema(
        id=row.id,
        project_id=row.project_id,
        attachment_type=row.attachment_type,
        file_name=row.file_name,
        file_url=row.file_url,
        file_size=row.file_size,
        mime_type=row.mime_type,
        related_node_code=row.related_node_code,
        extra_data=row.extra_data,
        uploaded_by=row.uploaded_by,
        uploaded_at=row.uploaded_at,
    )


def _latest_result_summary(project: DecorationProject) -> DecorationNodeResultSummary:
    prop = _latest_by_project(project.property_reviews)
    dep = _latest_by_project(project.deposit_confirms)
    entry = _latest_by_project(project.entry_confirms)
    acc = _latest_by_project(project.acceptances)
    st = _latest_by_project(project.settlements)
    ref = _latest_by_project(project.refunds)
    return DecorationNodeResultSummary(
        property_review=None if not prop else {
            "review_result": prop.review_result,
            "review_comment": prop.review_comment,
            "reviewed_at": prop.reviewed_at.isoformat() if prop.reviewed_at else None,
        },
        deposit_confirm=None if not dep else {
            "deposit_amount_received": float(dep.deposit_amount_received),
            "received_date": dep.received_date.isoformat() if dep.received_date else None,
        },
        entry_confirm=None if not entry else {
            "entry_result": entry.entry_result,
            "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
        },
        acceptance=None if not acc else {
            "acceptance_result": acc.acceptance_result,
            "acceptance_date": acc.acceptance_date.isoformat() if acc.acceptance_date else None,
        },
        settlement=None if not st else {
            "refund_amount": float(st.refund_amount),
            "confirmed_at": st.confirmed_at.isoformat() if st.confirmed_at else None,
        },
        refund=None if not ref else {
            "final_refund_amount": None if ref.final_refund_amount is None else float(ref.final_refund_amount),
            "refund_date": ref.refund_date.isoformat() if ref.refund_date else None,
        },
    )


def _serialize_workflow_summary(project: DecorationProject) -> Optional[DecorationWorkflowSummary]:
    current = None
    if project.current_workflow_instance_id:
        current = next((x for x in project.workflow_instances if x.id == project.current_workflow_instance_id), None)
    if current is None:
        current = _latest_by_project(project.workflow_instances)
    if not current:
        return None
    return DecorationWorkflowSummary(
        flow_type=current.flow_type,
        current_node_code=current.current_node_code,
        current_assignee_user_id=current.current_assignee_user_id,
    )


def _available_actions(project: DecorationProject, role_codes: set[str], current_user_id: int) -> list[str]:
    actions: list[str] = []
    is_admin = _is_admin_role(role_codes)
    if project.current_status == "DRAFT" and (project.applicant_user_id == current_user_id or is_admin):
        actions.extend(["edit", "submit", "cancel", "upload_attachment"])
    if project.current_status == "PENDING_PROPERTY_REVIEW" and ("decoration_property" in role_codes or is_admin):
        actions.append("property_review")
    if project.current_status == "PENDING_LEADER_APPROVAL" and ("decoration_leader" in role_codes or is_admin):
        actions.append("leader_approval")
    if project.current_status == "PENDING_DEPOSIT_CONFIRM" and ("decoration_finance" in role_codes or is_admin):
        actions.append("deposit_confirm")
    if project.current_status == "PENDING_ENTRY_CONFIRM" and ("decoration_property" in role_codes or is_admin):
        actions.append("entry_confirm")
    if project.current_status == "IN_CONSTRUCTION" and (project.applicant_user_id == current_user_id or "decoration_property" in role_codes or is_admin):
        actions.extend(["completion_submit", "cancel"])
    if project.current_status == "PENDING_ACCEPTANCE" and ("decoration_property" in role_codes or is_admin):
        actions.append("acceptance")
    if project.current_status == "PENDING_SETTLEMENT" and ({"decoration_property", "decoration_finance"} & role_codes or is_admin):
        actions.append("settlement")
    if project.current_status == "PENDING_REFUND_APPROVAL" and ("decoration_leader" in role_codes or "decoration_finance" in role_codes or is_admin):
        actions.extend(["refund_approval", "refund_confirm"])
    return actions


def _ensure_attachment_types(project: DecorationProject) -> None:
    required = {"DRAWING_DRAFT", "CONSTRUCTION_PLAN", "CONTRACTOR_LICENSE"}
    actual = {item.attachment_type for item in project.attachments}
    missing = sorted(required - actual)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"缺少必传附件: {', '.join(missing)}")


def _ensure_default_templates(db: Session) -> None:
    existing = {
        row.template_code: row
        for row in db.query(WorkflowTemplate).filter(
            WorkflowTemplate.template_code.in_(["DECORATION_ENTRY_V1", "DECORATION_REFUND_V1"])
        ).all()
    }
    changed = False
    if "DECORATION_ENTRY_V1" not in existing:
        entry = WorkflowTemplate(
            template_code="DECORATION_ENTRY_V1",
            template_name="装修进场流程",
            business_type="DECORATION",
            scene_code="ENTRY",
            is_active=True,
            version_no=1,
        )
        db.add(entry)
        db.flush()
        nodes = [
            ("SUBMIT", "发起申请", 1, "SUBMIT", "decoration_applicant", False, False, None, False),
            ("PROPERTY_REVIEW", "物业审图", 2, "REVIEW", "decoration_property", False, True, "SUBMIT", False),
            ("LEADER_APPROVAL", "领导审批", 3, "REVIEW", "decoration_leader", True, False, None, False),
            ("DEPOSIT_CONFIRM", "保证金确认", 4, "FINANCE", "decoration_finance", False, True, "SUBMIT", False),
            ("ENTRY_CONFIRM", "进场确认", 5, "CONFIRM", "decoration_property", False, True, "SUBMIT", True),
        ]
        for node in nodes:
            db.add(
                WorkflowTemplateNode(
                    template_id=entry.id,
                    node_code=node[0],
                    node_name=node[1],
                    node_order=node[2],
                    node_type=node[3],
                    role_code=node[4],
                    allow_reject=node[5],
                    allow_return=node[6],
                    return_target=node[7],
                    is_final_node=node[8],
                )
            )
        changed = True
    if "DECORATION_REFUND_V1" not in existing:
        refund = WorkflowTemplate(
            template_code="DECORATION_REFUND_V1",
            template_name="装修退款流程",
            business_type="DECORATION",
            scene_code="REFUND",
            is_active=True,
            version_no=1,
        )
        db.add(refund)
        db.flush()
        nodes = [
            ("REFUND_APPROVAL", "退款审批", 1, "REVIEW", "decoration_leader", True, False, None, False),
            ("REFUND_CONFIRM", "退款确认", 2, "FINANCE", "decoration_finance", False, True, "REFUND_APPROVAL", True),
        ]
        for node in nodes:
            db.add(
                WorkflowTemplateNode(
                    template_id=refund.id,
                    node_code=node[0],
                    node_name=node[1],
                    node_order=node[2],
                    node_type=node[3],
                    role_code=node[4],
                    allow_reject=node[5],
                    allow_return=node[6],
                    return_target=node[7],
                    is_final_node=node[8],
                )
            )
        changed = True
    if changed:
        db.commit()


def _pick_assignee(db: Session, store_id: int, role_code: str) -> Optional[int]:
    preferred = (
        db.query(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.role_code == role_code)
        .filter(or_(UserRole.store_id == store_id, UserRole.store_id.is_(None)))
        .order_by(UserRole.store_id.is_(None))
        .first()
    )
    if preferred:
        return preferred.user_id
    fallback = (
        db.query(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.role_code.in_(["super_admin", "system_admin", "decoration_admin"]))
        .first()
    )
    return fallback.user_id if fallback else None


def _status_from_node(node_code: str) -> str:
    return {
        "PROPERTY_REVIEW": "PENDING_PROPERTY_REVIEW",
        "LEADER_APPROVAL": "PENDING_LEADER_APPROVAL",
        "DEPOSIT_CONFIRM": "PENDING_DEPOSIT_CONFIRM",
        "ENTRY_CONFIRM": "PENDING_ENTRY_CONFIRM",
        "REFUND_APPROVAL": "PENDING_REFUND_APPROVAL",
        "REFUND_CONFIRM": "PENDING_REFUND_APPROVAL",
    }.get(node_code, "DRAFT")


def _assert_can_mutate(project: DecorationProject, current_user: User, role_codes: set[str]) -> None:
    if project.applicant_user_id != current_user.user_id and not _is_admin_role(role_codes):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该装修项目")


def _assert_status(project: DecorationProject, expected: str) -> None:
    if project.current_status != expected:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"当前状态不允许该操作: {project.current_status}")


def _advance_workflow(
    db: Session,
    project: DecorationProject,
    workflow: WorkflowInstance,
    action_user_id: int,
    *,
    result: str,
    comment: Optional[str],
    next_node_code: Optional[str],
    fallback_status: Optional[str] = None,
) -> None:
    current_node = (
        db.query(WorkflowInstanceNode)
        .filter(
            WorkflowInstanceNode.workflow_instance_id == workflow.id,
            WorkflowInstanceNode.node_code == workflow.current_node_code,
        )
        .first()
    )
    if current_node:
        current_node.status = (
            "APPROVED"
            if result in {"APPROVE", "CONFIRM", "APPROVED"}
            else "REJECTED"
            if result == "REJECT"
            else "RETURNED"
            if result == "RETURN"
            else result
        )
        current_node.action_result = result
        current_node.comment = comment
        current_node.acted_at = datetime.now()
    db.add(
        WorkflowAction(
            workflow_instance_id=workflow.id,
            workflow_instance_node_id=current_node.id if current_node else None,
            action_code=result if result in {"SUBMIT", "RETURN", "CANCEL"} else (
                "CONFIRM" if result in {"CONFIRM", "APPROVED"} and workflow.flow_type == "ENTRY" and current_node and current_node.node_code in {"DEPOSIT_CONFIRM", "ENTRY_CONFIRM"} else
                "APPROVE" if result in {"APPROVE", "APPROVED"} else result
            ),
            action_result=result,
            actor_user_id=action_user_id,
            action_comment=comment,
            action_data={},
            created_at=datetime.now(),
        )
    )

    if next_node_code:
        next_node = (
            db.query(WorkflowInstanceNode)
            .filter(
                WorkflowInstanceNode.workflow_instance_id == workflow.id,
                WorkflowInstanceNode.node_code == next_node_code,
            )
            .first()
        )
        if not next_node:
            raise HTTPException(status_code=500, detail=f"流程节点不存在: {next_node_code}")
        next_node.assignee_user_id = _pick_assignee(db, project.store_id, _template_role_code(db, workflow.template_id, next_node_code))
        next_node.status = "PENDING"
        next_node.arrived_at = datetime.now()
        workflow.current_node_code = next_node_code
        workflow.current_assignee_user_id = next_node.assignee_user_id
        project.current_status = _status_from_node(next_node_code) if not fallback_status else fallback_status
        project.current_node_code = next_node_code
        project.current_assignee_user_id = next_node.assignee_user_id
        project.current_workflow_instance_id = workflow.id
    else:
        workflow.status = "COMPLETED"
        workflow.completed_at = datetime.now()
        workflow.current_node_code = None
        workflow.current_assignee_user_id = None


def _template_role_code(db: Session, template_id: int, node_code: str) -> str:
    node = (
        db.query(WorkflowTemplateNode.role_code)
        .filter(
            WorkflowTemplateNode.template_id == template_id,
            WorkflowTemplateNode.node_code == node_code,
        )
        .first()
    )
    return node.role_code if node else "decoration_admin"


def _start_entry_workflow(db: Session, project: DecorationProject, current_user: User, comment: Optional[str]) -> None:
    _ensure_default_templates(db)
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.template_code == "DECORATION_ENTRY_V1").first()
    if not template:
        raise HTTPException(status_code=500, detail="未找到进场流程模板")
    workflow = WorkflowInstance(
        project_id=project.id,
        template_id=template.id,
        flow_type="ENTRY",
        status="RUNNING",
        current_node_code="PROPERTY_REVIEW",
        started_by=current_user.user_id,
        started_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(workflow)
    db.flush()

    nodes = db.query(WorkflowTemplateNode).filter(WorkflowTemplateNode.template_id == template.id).order_by(WorkflowTemplateNode.node_order.asc()).all()
    current_assignee = None
    for node in nodes:
        status_value = "APPROVED" if node.node_code == "SUBMIT" else "PENDING" if node.node_code == "PROPERTY_REVIEW" else "SKIPPED"
        assignee = current_user.user_id if node.node_code == "SUBMIT" else (
            _pick_assignee(db, project.store_id, node.role_code) if node.node_code == "PROPERTY_REVIEW" else None
        )
        if node.node_code == "PROPERTY_REVIEW":
            current_assignee = assignee
        db.add(
            WorkflowInstanceNode(
                workflow_instance_id=workflow.id,
                template_node_id=node.id,
                node_code=node.node_code,
                node_name=node.node_name,
                node_order=node.node_order,
                assignee_user_id=assignee,
                status=status_value,
                arrived_at=datetime.now() if node.node_code == "PROPERTY_REVIEW" else None,
                acted_at=datetime.now() if node.node_code == "SUBMIT" else None,
                action_result="SUBMIT" if node.node_code == "SUBMIT" else None,
                comment=comment if node.node_code == "SUBMIT" else None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
    db.add(
        WorkflowAction(
            workflow_instance_id=workflow.id,
            action_code="SUBMIT",
            action_result="SUBMIT",
            actor_user_id=current_user.user_id,
            action_comment=comment,
            action_data={},
            created_at=datetime.now(),
        )
    )
    workflow.current_assignee_user_id = current_assignee
    project.current_status = "PENDING_PROPERTY_REVIEW"
    project.current_node_code = "PROPERTY_REVIEW"
    project.current_assignee_user_id = current_assignee
    project.current_workflow_instance_id = workflow.id


def _start_refund_workflow(db: Session, project: DecorationProject, current_user: User) -> WorkflowInstance:
    _ensure_default_templates(db)
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.template_code == "DECORATION_REFUND_V1").first()
    if not template:
        raise HTTPException(status_code=500, detail="未找到退款流程模板")
    workflow = WorkflowInstance(
        project_id=project.id,
        template_id=template.id,
        flow_type="REFUND",
        status="RUNNING",
        current_node_code="REFUND_APPROVAL",
        started_by=current_user.user_id,
        started_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(workflow)
    db.flush()
    nodes = db.query(WorkflowTemplateNode).filter(WorkflowTemplateNode.template_id == template.id).order_by(WorkflowTemplateNode.node_order.asc()).all()
    current_assignee = None
    for node in nodes:
        status_value = "PENDING" if node.node_code == "REFUND_APPROVAL" else "SKIPPED"
        assignee = _pick_assignee(db, project.store_id, node.role_code) if status_value == "PENDING" else None
        if node.node_code == "REFUND_APPROVAL":
            current_assignee = assignee
        db.add(
            WorkflowInstanceNode(
                workflow_instance_id=workflow.id,
                template_node_id=node.id,
                node_code=node.node_code,
                node_name=node.node_name,
                node_order=node.node_order,
                assignee_user_id=assignee,
                status=status_value,
                arrived_at=datetime.now() if status_value == "PENDING" else None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
    workflow.current_assignee_user_id = current_assignee
    project.current_status = "PENDING_REFUND_APPROVAL"
    project.current_node_code = "REFUND_APPROVAL"
    project.current_assignee_user_id = current_assignee
    project.current_workflow_instance_id = workflow.id
    return workflow


def _serialize_detail(db: Session, project: DecorationProject, current_user: User) -> DecorationProjectDetail:
    store = db.query(Store).filter(Store.store_id == project.store_id).first()
    department = db.query(Department).filter(Department.id == project.department_id).first()
    applicant = db.query(User).filter(User.user_id == project.applicant_user_id).first()
    assignee = db.query(User).filter(User.user_id == project.current_assignee_user_id).first() if project.current_assignee_user_id else None
    role_codes = _role_codes(db, current_user.user_id)
    return DecorationProjectDetail(
        id=project.id,
        project_no=project.project_no,
        store_id=project.store_id,
        store_name=store.store_name if store else None,
        department_id=project.department_id,
        department_name=department.dept_name if department else None,
        applicant_user_id=project.applicant_user_id,
        applicant_name=applicant.real_name if applicant else None,
        applicant_phone=project.applicant_phone,
        brand_name=project.brand_name,
        tenant_name=project.tenant_name,
        contractor_name=project.contractor_name,
        contractor_contact=project.contractor_contact,
        contractor_phone=project.contractor_phone,
        fitout_type=project.fitout_type,
        fitout_reason=project.fitout_reason,
        description=project.description,
        planned_entry_date=project.planned_entry_date,
        planned_finish_date=project.planned_finish_date,
        actual_entry_date=project.actual_entry_date,
        actual_finish_date=project.actual_finish_date,
        applied_area=project.applied_area,
        deposit_amount=project.deposit_amount,
        actual_measured_area=project.actual_measured_area,
        actual_power_usage=project.actual_power_usage,
        power_fee_amount=project.power_fee_amount,
        deduction_amount=project.deduction_amount,
        refund_amount=project.refund_amount,
        current_status=project.current_status,
        current_node_code=project.current_node_code,
        current_assignee_user_id=project.current_assignee_user_id,
        current_assignee_name=assignee.real_name if assignee else None,
        is_closed=bool(project.is_closed),
        closed_at=project.closed_at,
        reject_reason=project.reject_reason,
        cancel_reason=project.cancel_reason,
        oa_ref_no=project.oa_ref_no,
        spaces=project.spaces,
        attachments=[_serialize_attachment(x) for x in project.attachments],
        workflow_summary=_serialize_workflow_summary(project),
        node_results=_latest_result_summary(project),
        available_actions=_available_actions(project, role_codes, current_user.user_id),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/meta", response_model=DecorationMetaSchema)
async def get_decoration_meta(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_default_templates(db)
    stores = db.query(Store).filter(Store.is_active.is_(True)).all()
    departments = db.query(Department).filter(Department.is_active.is_(True)).all()
    return DecorationMetaSchema(
        status_options=[DecorationMetaOption(label=v, value=k) for k, v in PROJECT_STATUS_LABELS.items()],
        attachment_type_options=[DecorationMetaOption(label=label, value=value) for value, label in ATTACHMENT_TYPE_OPTIONS],
        fitout_type_options=[DecorationMetaOption(label=label, value=value) for value, label in FITOUT_TYPE_OPTIONS],
        stores=[DecorationMetaStore(store_id=s.store_id, store_name=s.store_name) for s in stores],
        departments=[DecorationMetaDepartment(id=d.id, dept_name=d.dept_name, store_id=d.store_id) for d in departments],
        workflow_node_options=[
            DecorationMetaOption(label="物业审图", value="PROPERTY_REVIEW"),
            DecorationMetaOption(label="领导审批", value="LEADER_APPROVAL"),
            DecorationMetaOption(label="保证金确认", value="DEPOSIT_CONFIRM"),
            DecorationMetaOption(label="进场确认", value="ENTRY_CONFIRM"),
            DecorationMetaOption(label="退款审批", value="REFUND_APPROVAL"),
            DecorationMetaOption(label="退款确认", value="REFUND_CONFIRM"),
        ],
    )


@router.get("/todos", response_model=list[DecorationTodoItem])
async def get_decoration_todos(
    store_id: Optional[int] = Query(None),
    flow_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        db.query(WorkflowInstanceNode, DecorationProject, Store, User)
        .join(WorkflowInstance, WorkflowInstance.id == WorkflowInstanceNode.workflow_instance_id)
        .join(DecorationProject, DecorationProject.id == WorkflowInstance.project_id)
        .join(Store, Store.store_id == DecorationProject.store_id)
        .join(User, User.user_id == DecorationProject.applicant_user_id)
        .filter(WorkflowInstanceNode.status == "PENDING")
        .filter(WorkflowInstanceNode.assignee_user_id == current_user.user_id)
    )
    if store_id is not None:
        q = q.filter(DecorationProject.store_id == store_id)
    if flow_type:
        q = q.filter(WorkflowInstance.flow_type == flow_type)
    rows = q.order_by(WorkflowInstanceNode.arrived_at.desc().nullslast()).offset(skip).limit(limit).all()
    return [
        DecorationTodoItem(
            workflow_instance_node_id=node.id,
            project_id=project.id,
            project_no=project.project_no,
            node_code=node.node_code,
            node_name=node.node_name,
            store_name=store.store_name,
            brand_name=project.brand_name,
            applicant_name=user.real_name,
            current_status=project.current_status,
            arrived_at=node.arrived_at,
            is_overdue=False,
        )
        for node, project, store, user in rows
    ]


@router.get("/my-applications", response_model=list[DecorationProjectListItem])
async def get_my_decoration_applications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_decorations(mine=True, skip=skip, limit=limit, db=db, current_user=current_user)


@router.get("", response_model=list[DecorationProjectListItem])
@router.get("/", response_model=list[DecorationProjectListItem])
async def list_decorations(
    store_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    keyword: Optional[str] = Query(None),
    mine: bool = False,
    assignee_me: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(DecorationProject)
    role_codes = _role_codes(db, current_user.user_id)
    if store_id is not None:
        query = query.filter(DecorationProject.store_id == store_id)
    if status_filter:
        query = query.filter(DecorationProject.current_status == status_filter)
    if keyword:
        kw = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                DecorationProject.project_no.ilike(kw),
                DecorationProject.brand_name.ilike(kw),
                DecorationProject.contractor_name.ilike(kw),
            )
        )
    if mine:
        query = query.filter(DecorationProject.applicant_user_id == current_user.user_id)
    elif assignee_me:
        query = query.filter(DecorationProject.current_assignee_user_id == current_user.user_id)
    elif not _is_admin_role(role_codes) and "decoration_property" not in role_codes and "decoration_finance" not in role_codes and "decoration_leader" not in role_codes:
        query = query.filter(DecorationProject.applicant_user_id == current_user.user_id)

    projects = query.order_by(DecorationProject.created_at.desc()).offset(skip).limit(limit).all()
    store_ids = {p.store_id for p in projects}
    user_ids = {p.applicant_user_id for p in projects} | {p.current_assignee_user_id for p in projects if p.current_assignee_user_id}
    stores = {s.store_id: s for s in db.query(Store).filter(Store.store_id.in_(store_ids)).all()} if store_ids else {}
    users = {u.user_id: u for u in db.query(User).filter(User.user_id.in_(user_ids)).all()} if user_ids else {}
    return [
        DecorationProjectListItem(
            id=p.id,
            project_no=p.project_no,
            store_id=p.store_id,
            store_name=stores.get(p.store_id).store_name if stores.get(p.store_id) else None,
            brand_name=p.brand_name,
            contractor_name=p.contractor_name,
            applicant_user_id=p.applicant_user_id,
            applicant_name=users.get(p.applicant_user_id).real_name if users.get(p.applicant_user_id) else None,
            current_status=p.current_status,
            current_status_name=PROJECT_STATUS_LABELS.get(p.current_status),
            current_node_code=p.current_node_code,
            current_assignee_user_id=p.current_assignee_user_id,
            current_assignee_name=users.get(p.current_assignee_user_id).real_name if users.get(p.current_assignee_user_id) else None,
            planned_entry_date=p.planned_entry_date,
            planned_finish_date=p.planned_finish_date,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.post("/", response_model=DecorationProjectDetail)
async def create_decoration(
    payload: DecorationProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = DecorationProject(
        project_no=_make_project_no(db),
        store_id=payload.store_id,
        department_id=payload.department_id,
        applicant_user_id=current_user.user_id,
        applicant_phone=payload.applicant_phone,
        brand_name=payload.brand_name,
        tenant_name=payload.tenant_name,
        contractor_name=payload.contractor_name,
        contractor_contact=payload.contractor_contact,
        contractor_phone=payload.contractor_phone,
        fitout_type=payload.fitout_type,
        fitout_reason=payload.fitout_reason,
        description=payload.description,
        planned_entry_date=payload.planned_entry_date,
        planned_finish_date=payload.planned_finish_date,
        applied_area=payload.applied_area,
        current_status="DRAFT",
        is_closed=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(project)
    db.flush()
    for item in payload.spaces:
        db.add(
            DecorationProjectSpace(
                project_id=project.id,
                space_type=item.space_type,
                hall_id=item.hall_id,
                business_unit_id=item.business_unit_id,
                floor_id=item.floor_id,
                space_code=item.space_code,
                space_name=item.space_name,
                applied_area=item.applied_area,
                measured_area=item.measured_area,
                remarks=item.remarks,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
    _log_operation(db, current_user.user_id, "decoration.create", project.id, {"project_no": project.project_no})
    db.commit()
    db.refresh(project)
    project = _require_project(db, project.id)
    return _serialize_detail(db, project, current_user)


@router.get("/{project_id}", response_model=DecorationProjectDetail)
async def get_decoration(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    return _serialize_detail(db, project, current_user)


@router.put("/{project_id}", response_model=DecorationProjectDetail)
async def update_decoration(
    project_id: int,
    payload: DecorationProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    role_codes = _role_codes(db, current_user.user_id)
    _assert_can_mutate(project, current_user, role_codes)
    _assert_status(project, "DRAFT")
    data = payload.model_dump(exclude_unset=True)
    spaces = data.pop("spaces", None)
    for key, value in data.items():
        setattr(project, key, value)
    project.updated_at = datetime.now()
    if spaces is not None:
        db.query(DecorationProjectSpace).filter(DecorationProjectSpace.project_id == project.id).delete()
        for item in spaces:
            db.add(
                DecorationProjectSpace(
                    project_id=project.id,
                    space_type=item.space_type,
                    hall_id=item.hall_id,
                    business_unit_id=item.business_unit_id,
                    floor_id=item.floor_id,
                    space_code=item.space_code,
                    space_name=item.space_name,
                    applied_area=item.applied_area,
                    measured_area=item.measured_area,
                    remarks=item.remarks,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
    _log_operation(db, current_user.user_id, "decoration.edit", project.id)
    db.commit()
    db.refresh(project)
    project = _require_project(db, project.id)
    return _serialize_detail(db, project, current_user)


@router.post("/{project_id}/submit", response_model=DecorationActionResponse)
async def submit_decoration(
    project_id: int,
    payload: DecorationSubmitPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    role_codes = _role_codes(db, current_user.user_id)
    _assert_can_mutate(project, current_user, role_codes)
    _assert_status(project, "DRAFT")
    _ensure_attachment_types(project)
    if not project.spaces:
        raise HTTPException(status_code=400, detail="请至少关联一个装修空间")
    _start_entry_workflow(db, project, current_user, payload.comment)
    _log_operation(db, current_user.user_id, "decoration.submit", project.id)
    db.commit()
    return DecorationActionResponse(
        message="提交成功",
        project_id=project.id,
        current_status=project.current_status,
        current_node_code=project.current_node_code,
    )


@router.post("/{project_id}/cancel", response_model=DecorationActionResponse)
async def cancel_decoration(
    project_id: int,
    payload: DecorationCancelPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    role_codes = _role_codes(db, current_user.user_id)
    _assert_can_mutate(project, current_user, role_codes)
    if project.current_status in {"COMPLETED", "CANCELLED"}:
        raise HTTPException(status_code=409, detail="当前状态不可取消")
    project.current_status = "CANCELLED"
    project.cancel_reason = payload.reason
    project.is_closed = True
    project.closed_at = datetime.now()
    project.current_node_code = None
    project.current_assignee_user_id = None
    if project.current_workflow_instance_id:
        workflow = db.query(WorkflowInstance).filter(WorkflowInstance.id == project.current_workflow_instance_id).first()
        if workflow:
            workflow.status = "CANCELLED"
            workflow.completed_at = datetime.now()
            workflow.current_node_code = None
            workflow.current_assignee_user_id = None
    _log_operation(db, current_user.user_id, "decoration.cancel", project.id, {"reason": payload.reason})
    db.commit()
    return DecorationActionResponse(message="取消成功", project_id=project.id, current_status=project.current_status, current_node_code=None)


@router.get("/{project_id}/attachments", response_model=list[DecorationAttachmentSchema])
async def get_decoration_attachments(
    project_id: int,
    attachment_type: Optional[str] = Query(None),
    related_node_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_project(db, project_id)
    q = db.query(DecorationAttachment).filter(DecorationAttachment.project_id == project_id)
    if attachment_type:
        q = q.filter(DecorationAttachment.attachment_type == attachment_type)
    if related_node_code:
        q = q.filter(DecorationAttachment.related_node_code == related_node_code)
    rows = q.order_by(DecorationAttachment.uploaded_at.desc()).all()
    return [_serialize_attachment(x) for x in rows]


@router.post("/{project_id}/attachments", response_model=DecorationAttachmentSchema)
async def create_decoration_attachment(
    project_id: int,
    payload: DecorationAttachmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    role_codes = _role_codes(db, current_user.user_id)
    if project.current_status != "DRAFT" and not _is_admin_role(role_codes):
        # 阶段1先限制非草稿只允许管理员补附件，避免复杂节点权限
        raise HTTPException(status_code=409, detail="当前状态暂不允许上传附件")
    row = DecorationAttachment(
        project_id=project.id,
        attachment_type=payload.attachment_type,
        file_name=payload.file_name,
        file_url=payload.file_url,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        related_node_code=payload.related_node_code,
        extra_data=payload.extra_data,
        uploaded_by=current_user.user_id,
        uploaded_at=datetime.now(),
    )
    db.add(row)
    _log_operation(db, current_user.user_id, "decoration.attachment.create", project.id, {"attachment_type": payload.attachment_type})
    db.commit()
    db.refresh(row)
    return _serialize_attachment(row)


@router.delete("/{project_id}/attachments/{attachment_id}", response_model=BaseResponse)
async def delete_decoration_attachment(
    project_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    role_codes = _role_codes(db, current_user.user_id)
    _assert_can_mutate(project, current_user, role_codes)
    _assert_status(project, "DRAFT")
    row = db.query(DecorationAttachment).filter(
        DecorationAttachment.id == attachment_id,
        DecorationAttachment.project_id == project_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="附件不存在")
    db.delete(row)
    _log_operation(db, current_user.user_id, "decoration.attachment.delete", project.id, {"attachment_id": attachment_id})
    db.commit()
    return BaseResponse(message="附件删除成功")


@router.get("/{project_id}/timeline", response_model=list[DecorationTimelineItem])
async def get_decoration_timeline(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    user_ids = {project.applicant_user_id}
    action_rows = db.query(WorkflowAction).join(WorkflowInstance, WorkflowInstance.id == WorkflowAction.workflow_instance_id).filter(WorkflowInstance.project_id == project.id).all()
    user_ids |= {x.actor_user_id for x in action_rows}
    users = {u.user_id: u.real_name for u in db.query(User).filter(User.user_id.in_(user_ids)).all()} if user_ids else {}
    items = [
        DecorationTimelineItem(
            time=project.created_at,
            type="PROJECT_CREATED",
            operator_name=users.get(project.applicant_user_id),
            content="创建装修项目",
        )
    ]
    for row in action_rows:
        items.append(
            DecorationTimelineItem(
                time=row.created_at,
                type=f"WORKFLOW_{row.action_code}",
                operator_name=users.get(row.actor_user_id),
                content=row.action_comment or row.action_code,
            )
        )
    items.sort(key=lambda x: x.time)
    return items


@router.get("/{project_id}/workflow", response_model=DecorationWorkflowDetail)
async def get_decoration_workflow(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    instances = db.query(WorkflowInstance).filter(WorkflowInstance.project_id == project.id).order_by(WorkflowInstance.started_at.asc()).all()
    payload = []
    for wf in instances:
        nodes = db.query(WorkflowInstanceNode).filter(WorkflowInstanceNode.workflow_instance_id == wf.id).order_by(WorkflowInstanceNode.node_order.asc()).all()
        payload.append(
            WorkflowInstanceSchema(
                id=wf.id,
                flow_type=wf.flow_type,
                status=wf.status,
                current_node_code=wf.current_node_code,
                nodes=[
                    WorkflowInstanceNodeSchema(
                        id=node.id,
                        node_code=node.node_code,
                        node_name=node.node_name,
                        node_order=node.node_order,
                        assignee_user_id=node.assignee_user_id,
                        status=node.status,
                        arrived_at=node.arrived_at,
                        acted_at=node.acted_at,
                        action_result=node.action_result,
                        comment=node.comment,
                    )
                    for node in nodes
                ],
            )
        )
    return DecorationWorkflowDetail(workflow_instances=payload)


def _current_workflow(db: Session, project: DecorationProject, flow_type: str) -> WorkflowInstance:
    workflow = (
        db.query(WorkflowInstance)
        .filter(
            WorkflowInstance.project_id == project.id,
            WorkflowInstance.flow_type == flow_type,
            WorkflowInstance.status == "RUNNING",
        )
        .order_by(WorkflowInstance.started_at.desc())
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=409, detail="当前不存在可处理的流程实例")
    return workflow


@router.post("/{project_id}/property-review", response_model=DecorationActionResponse)
async def property_review(
    project_id: int,
    payload: DecorationPropertyReviewPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "PENDING_PROPERTY_REVIEW")
    workflow = _current_workflow(db, project, "ENTRY")
    db.add(
        DecorationPropertyReview(
            project_id=project.id,
            workflow_instance_id=workflow.id,
            review_result=payload.review_result,
            review_comment=payload.review_comment,
            rectification_requirements=payload.rectification_requirements,
            reviewed_by=current_user.user_id,
            reviewed_at=datetime.now(),
            created_at=datetime.now(),
        )
    )
    if payload.review_result == "RETURNED":
        workflow.status = "CANCELLED"
        workflow.completed_at = datetime.now()
        project.current_status = "DRAFT"
        project.current_node_code = None
        project.current_assignee_user_id = project.applicant_user_id
        _advance_workflow(db, project, workflow, current_user.user_id, result="RETURN", comment=payload.review_comment, next_node_code=None, fallback_status="DRAFT")
    else:
        _advance_workflow(db, project, workflow, current_user.user_id, result="APPROVE", comment=payload.review_comment, next_node_code="LEADER_APPROVAL")
    _log_operation(db, current_user.user_id, "decoration.property_review", project.id)
    db.commit()
    return DecorationActionResponse(message="审图处理成功", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)


@router.post("/{project_id}/leader-approval", response_model=DecorationActionResponse)
async def leader_approval(
    project_id: int,
    payload: DecorationLeaderApprovalPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "PENDING_LEADER_APPROVAL")
    workflow = _current_workflow(db, project, "ENTRY")
    if payload.action == "REJECT":
        _advance_workflow(db, project, workflow, current_user.user_id, result="REJECT", comment=payload.comment, next_node_code=None, fallback_status="REJECTED")
        workflow.status = "REJECTED"
        project.current_status = "REJECTED"
        project.reject_reason = payload.comment
        project.is_closed = True
        project.closed_at = datetime.now()
        project.current_node_code = None
        project.current_assignee_user_id = None
    else:
        _advance_workflow(db, project, workflow, current_user.user_id, result="APPROVE", comment=payload.comment, next_node_code="DEPOSIT_CONFIRM")
    _log_operation(db, current_user.user_id, "decoration.leader_approve", project.id)
    db.commit()
    return DecorationActionResponse(message="审批处理成功", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)


@router.post("/{project_id}/deposit-confirm", response_model=DecorationActionResponse)
async def deposit_confirm(
    project_id: int,
    payload: DecorationDepositConfirmPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "PENDING_DEPOSIT_CONFIRM")
    workflow = _current_workflow(db, project, "ENTRY")
    db.add(
        DecorationDepositConfirm(
            project_id=project.id,
            workflow_instance_id=workflow.id,
            deposit_amount_expected=payload.deposit_amount_expected,
            deposit_amount_received=payload.deposit_amount_received,
            received_date=payload.received_date,
            receipt_attachment_id=payload.receipt_attachment_id,
            finance_comment=payload.finance_comment,
            status="RETURNED" if payload.action == "RETURN" else "CONFIRMED",
            confirmed_by=current_user.user_id,
            confirmed_at=datetime.now(),
            created_at=datetime.now(),
        )
    )
    project.deposit_amount = payload.deposit_amount_expected
    if payload.action == "RETURN":
        _advance_workflow(db, project, workflow, current_user.user_id, result="RETURN", comment=payload.finance_comment, next_node_code=None, fallback_status="DRAFT")
        workflow.status = "CANCELLED"
        workflow.completed_at = datetime.now()
        project.current_status = "DRAFT"
        project.current_node_code = None
        project.current_assignee_user_id = project.applicant_user_id
    else:
        _advance_workflow(db, project, workflow, current_user.user_id, result="CONFIRM", comment=payload.finance_comment, next_node_code="ENTRY_CONFIRM")
    _log_operation(db, current_user.user_id, "decoration.deposit_confirm", project.id)
    db.commit()
    return DecorationActionResponse(message="保证金处理成功", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)


@router.post("/{project_id}/entry-confirm", response_model=DecorationActionResponse)
async def entry_confirm(
    project_id: int,
    payload: DecorationEntryConfirmPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "PENDING_ENTRY_CONFIRM")
    workflow = _current_workflow(db, project, "ENTRY")
    db.add(
        DecorationEntryConfirm(
            project_id=project.id,
            workflow_instance_id=workflow.id,
            entry_result=payload.entry_result,
            entry_date=payload.entry_date,
            requirements=payload.requirements,
            security_note=payload.security_note,
            confirmed_by=current_user.user_id,
            confirmed_at=datetime.now(),
            created_at=datetime.now(),
        )
    )
    if payload.entry_result == "APPROVED":
        _advance_workflow(db, project, workflow, current_user.user_id, result="CONFIRM", comment=payload.requirements, next_node_code=None, fallback_status="IN_CONSTRUCTION")
        workflow.status = "COMPLETED"
        workflow.completed_at = datetime.now()
        project.current_status = "IN_CONSTRUCTION"
        project.current_node_code = None
        project.current_assignee_user_id = None
        project.actual_entry_date = payload.entry_date or date.today()
    elif payload.entry_result == "RETURNED":
        _advance_workflow(db, project, workflow, current_user.user_id, result="RETURN", comment=payload.requirements, next_node_code=None, fallback_status="DRAFT")
        workflow.status = "CANCELLED"
        workflow.completed_at = datetime.now()
        project.current_status = "DRAFT"
        project.current_node_code = None
        project.current_assignee_user_id = project.applicant_user_id
    else:
        db.add(
            WorkflowAction(
                workflow_instance_id=workflow.id,
                action_code="RETURN",
                action_result="DEFERRED",
                actor_user_id=current_user.user_id,
                action_comment=payload.requirements,
                action_data={},
                created_at=datetime.now(),
            )
        )
    _log_operation(db, current_user.user_id, "decoration.entry_confirm", project.id)
    db.commit()
    return DecorationActionResponse(message="进场处理成功", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)


@router.post("/{project_id}/completion-submit", response_model=DecorationActionResponse)
async def completion_submit(
    project_id: int,
    payload: DecorationCompletionSubmitPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "IN_CONSTRUCTION")
    project.actual_finish_date = payload.actual_finish_date
    project.current_status = "PENDING_ACCEPTANCE"
    project.current_node_code = "ACCEPTANCE"
    project.current_assignee_user_id = _pick_assignee(db, project.store_id, "decoration_property")
    _log_operation(db, current_user.user_id, "decoration.completion_submit", project.id, {"comment": payload.comment})
    db.commit()
    return DecorationActionResponse(message="已提交完工验收", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)


@router.post("/{project_id}/acceptance", response_model=DecorationActionResponse)
async def acceptance(
    project_id: int,
    payload: DecorationAcceptancePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "PENDING_ACCEPTANCE")
    db.add(
        DecorationAcceptance(
            project_id=project.id,
            acceptance_result=payload.acceptance_result,
            acceptance_date=payload.acceptance_date,
            acceptance_comment=payload.acceptance_comment,
            rectification_items=payload.rectification_items,
            accepted_by=current_user.user_id,
            accepted_at=datetime.now(),
            created_at=datetime.now(),
        )
    )
    if payload.acceptance_result == "RECTIFICATION":
        project.current_status = "IN_CONSTRUCTION"
        project.current_node_code = None
        project.current_assignee_user_id = project.applicant_user_id
    else:
        project.current_status = "PENDING_SETTLEMENT"
        project.current_node_code = "SETTLEMENT"
        project.current_assignee_user_id = _pick_assignee(db, project.store_id, "decoration_property")
    _log_operation(db, current_user.user_id, "decoration.acceptance", project.id)
    db.commit()
    return DecorationActionResponse(message="验收处理成功", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)


@router.post("/{project_id}/settlement", response_model=DecorationActionResponse)
async def settlement(
    project_id: int,
    payload: DecorationSettlementPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "PENDING_SETTLEMENT")
    db.add(
        DecorationSettlement(
            project_id=project.id,
            measured_area=payload.measured_area,
            actual_power_usage=payload.actual_power_usage,
            power_fee_amount=payload.power_fee_amount,
            deduction_items=[item.model_dump() for item in (payload.deduction_items or [])],
            deduction_amount=payload.deduction_amount,
            refund_amount=payload.refund_amount,
            settlement_comment=payload.settlement_comment,
            confirmed_by_property=current_user.user_id,
            confirmed_at=datetime.now(),
            status="CONFIRMED",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )
    project.actual_measured_area = payload.measured_area
    project.actual_power_usage = payload.actual_power_usage
    project.power_fee_amount = payload.power_fee_amount
    project.deduction_amount = payload.deduction_amount
    project.refund_amount = payload.refund_amount
    _start_refund_workflow(db, project, current_user)
    _log_operation(db, current_user.user_id, "decoration.settlement", project.id)
    db.commit()
    return DecorationActionResponse(message="结算确认成功", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)


@router.post("/{project_id}/refund-approval", response_model=DecorationActionResponse)
async def refund_approval(
    project_id: int,
    payload: DecorationRefundApprovalPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "PENDING_REFUND_APPROVAL")
    workflow = _current_workflow(db, project, "REFUND")
    if payload.action == "REJECT":
        db.add(
            DecorationRefund(
                project_id=project.id,
                workflow_instance_id=workflow.id,
                approved_refund_amount=payload.approved_refund_amount,
                leader_comment=payload.comment,
                status="REJECTED",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        _advance_workflow(db, project, workflow, current_user.user_id, result="REJECT", comment=payload.comment, next_node_code=None, fallback_status="PENDING_SETTLEMENT")
        workflow.status = "REJECTED"
        project.current_status = "PENDING_SETTLEMENT"
        project.current_node_code = "SETTLEMENT"
        project.current_assignee_user_id = _pick_assignee(db, project.store_id, "decoration_property")
    else:
        db.add(
            DecorationRefund(
                project_id=project.id,
                workflow_instance_id=workflow.id,
                approved_refund_amount=payload.approved_refund_amount,
                leader_comment=payload.comment,
                status="APPROVED",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        _advance_workflow(db, project, workflow, current_user.user_id, result="APPROVE", comment=payload.comment, next_node_code="REFUND_CONFIRM")
    _log_operation(db, current_user.user_id, "decoration.refund_approve", project.id)
    db.commit()
    return DecorationActionResponse(message="退款审批处理成功", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)


@router.post("/{project_id}/refund-confirm", response_model=DecorationActionResponse)
async def refund_confirm(
    project_id: int,
    payload: DecorationRefundConfirmPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _require_project(db, project_id)
    _assert_status(project, "PENDING_REFUND_APPROVAL")
    workflow = _current_workflow(db, project, "REFUND")
    db.add(
        DecorationRefund(
            project_id=project.id,
            workflow_instance_id=workflow.id,
            final_refund_amount=payload.final_refund_amount,
            finance_comment=payload.comment,
            refund_date=payload.refund_date,
            refund_proof_attachment_id=payload.refund_proof_attachment_id,
            status="COMPLETED",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )
    _advance_workflow(db, project, workflow, current_user.user_id, result="CONFIRM", comment=payload.comment, next_node_code=None, fallback_status="COMPLETED")
    workflow.status = "COMPLETED"
    workflow.completed_at = datetime.now()
    project.current_status = "COMPLETED"
    project.current_node_code = None
    project.current_assignee_user_id = None
    project.is_closed = True
    project.closed_at = datetime.now()
    _log_operation(db, current_user.user_id, "decoration.refund_confirm", project.id)
    db.commit()
    return DecorationActionResponse(message="退款确认成功", project_id=project.id, current_status=project.current_status, current_node_code=project.current_node_code)
