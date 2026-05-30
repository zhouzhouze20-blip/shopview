"""
系统管理与权限配置 API
"""
import base64
import hashlib
import os
from collections import defaultdict
from datetime import date, datetime, time
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import (
    DataPolicy,
    DataPolicyItem,
    Department,
    LoginLog,
    OperationLog,
    Permission,
    Post,
    Role,
    RolePermission,
    Store,
    User,
    UserDepartmentPost,
    UserIdentity,
    UserRole,
)
from routers.auth import get_client_ip, get_current_user
from routers.authz import require_permission
from schemas.schemas import (
    BaseResponse,
    DataPolicyCreate,
    DataPolicySchema,
    DataPolicyUpdate,
    Department as DepartmentSchema,
    DepartmentCreate,
    DepartmentUpdate,
    PermissionSchema,
    Post as PostSchema,
    RoleCreate,
    RoleSchema,
    RoleUpdate,
    SystemUserCreate,
    SystemUserSchema,
    SystemUserUpdate,
)

router = APIRouter(prefix="/api/system", tags=["system"])
PASSWORD_ITERATIONS = 390000
CONTRACT_VIEWER_ROLE_CODE = "contract_viewer"
BUSINESS_SCOPE_RESOURCE = "business_scope"
BUSINESS_SCOPE_ACTION = "view"
MANUAL_SOURCE_TYPE = "MANUAL"
MANUAL_SOURCE_SYSTEM = "shopview"


def _require_system_permission(db: Session, user: User, permission_code: str) -> None:
    require_permission(db, user, permission_code)


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(digest).decode("utf-8"),
    )


def _ensure_role_ids_exist(db: Session, role_ids: List[int]) -> None:
    if not role_ids:
        return
    existing = {role.id for role in db.query(Role).filter(Role.id.in_(role_ids)).all()}
    missing = sorted(set(role_ids) - existing)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"角色不存在: {missing}")


def _ensure_permission_ids_exist(db: Session, permission_ids: List[int]) -> None:
    if not permission_ids:
        return
    existing = {permission.id for permission in db.query(Permission).filter(Permission.id.in_(permission_ids)).all()}
    missing = sorted(set(permission_ids) - existing)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"权限不存在: {missing}")


def _ensure_department_ids_exist(db: Session, department_ids: List[int]) -> None:
    if not department_ids:
        return
    existing = {department.id for department in db.query(Department).filter(Department.id.in_(department_ids)).all()}
    missing = sorted(set(department_ids) - existing)
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"部门不存在: {missing}")


def _sync_user_roles(db: Session, user_id: int, role_ids: List[int]) -> None:
    db.query(UserRole).filter(UserRole.user_id == user_id).delete()
    for role_id in role_ids:
        db.add(UserRole(user_id=user_id, role_id=role_id))


def _sync_user_department_posts(db: Session, user_id: int, assignments: List[dict]) -> None:
    db.query(UserDepartmentPost).filter(UserDepartmentPost.user_id == user_id).delete()
    for assignment in assignments:
        db.add(UserDepartmentPost(
            user_id=user_id,
            store_id=assignment["store_id"],
            department_id=assignment["department_id"],
            post_id=assignment.get("post_id"),
            is_primary=assignment.get("is_primary", False),
            is_active=True,
        ))


def _upsert_password_identity(db: Session, user: User, password: str) -> None:
    password_hash = _hash_password(password)
    user.password_hash = password_hash
    identity = db.query(UserIdentity).filter(
        UserIdentity.user_id == user.user_id,
        UserIdentity.identity_type == "password",
    ).first()
    if identity:
        identity.identifier = user.username
        identity.credential_hash = password_hash
        identity.is_primary = True
    else:
        db.add(UserIdentity(
            user_id=user.user_id,
            identity_type="password",
            identifier=user.username,
            credential_hash=password_hash,
            is_primary=True,
        ))


def _sync_role_permissions(db: Session, role_id: int, permission_ids: List[int]) -> None:
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    for permission_id in permission_ids:
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))


def _sync_policy_items(db: Session, policy_id: int, items: List[dict]) -> None:
    db.query(DataPolicyItem).filter(DataPolicyItem.policy_id == policy_id).delete()
    for item in items:
        db.add(DataPolicyItem(
            policy_id=policy_id,
            dimension_type=item["dimension_type"],
            dimension_value=item["dimension_value"],
            include_children=item.get("include_children", False),
        ))


def _ensure_contract_viewer_role(db: Session) -> Role:
    required_permissions = [
        ("contract.view", "查看合同", "contract", "view"),
        ("sales.view", "查看销售", "sales", "view"),
    ]
    permissions = []
    for permission_code, permission_name, module_code, action_code in required_permissions:
        permission = db.query(Permission).filter(Permission.permission_code == permission_code).first()
        if not permission:
            permission = Permission(
                permission_code=permission_code,
                permission_name=permission_name,
                module_code=module_code,
                action_code=action_code,
            )
            db.add(permission)
            db.flush()
        permissions.append(permission)

    role = db.query(Role).filter(Role.role_code == CONTRACT_VIEWER_ROLE_CODE).first()
    if not role:
        role = Role(
            role_code=CONTRACT_VIEWER_ROLE_CODE,
            role_name="合同查看人员",
            role_level=300,
            is_system=True,
            is_active=True,
        )
        db.add(role)
        db.flush()

    for permission in permissions:
        exists = db.query(RolePermission).filter(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        ).first()
        if not exists:
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
            db.flush()

    return role


def _user_has_permission(db: Session, user_id: int, permission_code: str) -> bool:
    return bool(
        db.query(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == user_id,
            Role.is_active == True,
            Permission.permission_code == permission_code,
        )
        .first()
    )


def _user_has_role(db: Session, user_id: int, role_code: str) -> bool:
    return bool(
        db.query(Role.id)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id, Role.role_code == role_code, Role.is_active == True)
        .first()
    )


def _manual_business_scope_for_user(db: Session, user_id: int) -> dict:
    """仅本页（手工 shopview）维护的策略维度，用于编辑弹窗；不含 ERP 合并值。"""
    policies = db.query(DataPolicy).filter(
        DataPolicy.subject_type == "USER",
        DataPolicy.subject_id == user_id,
        DataPolicy.resource_code == BUSINESS_SCOPE_RESOURCE,
        DataPolicy.action_code == BUSINESS_SCOPE_ACTION,
        DataPolicy.effect == "ALLOW",
        DataPolicy.is_active == True,
        DataPolicy.source_type == MANUAL_SOURCE_TYPE,
        DataPolicy.source_system == MANUAL_SOURCE_SYSTEM,
    ).all()
    if not policies:
        policies = db.query(DataPolicy).filter(
            DataPolicy.subject_type == "USER",
            DataPolicy.subject_id == user_id,
            DataPolicy.resource_code == "contract",
            DataPolicy.action_code == "view",
            DataPolicy.effect == "ALLOW",
            DataPolicy.is_active == True,
            DataPolicy.source_type == MANUAL_SOURCE_TYPE,
            DataPolicy.source_system == MANUAL_SOURCE_SYSTEM,
        ).all()
    policy_ids = [policy.id for policy in policies]
    values = {"store": [], "department": [], "group": []}
    if policy_ids:
        rows = db.query(DataPolicyItem).filter(DataPolicyItem.policy_id.in_(policy_ids)).all()
        for row in rows:
            if row.dimension_type in values and row.dimension_value not in values[row.dimension_type]:
                values[row.dimension_type].append(row.dimension_value)

    return {
        "scope_mode": "ALL" if any(policy.scope_mode == "ALL" for policy in policies) else "CUSTOM",
        "store_values": values["store"],
        "department_values": values["department"],
        "group_values": values["group"],
    }


def _scope_tab_active_from_manual(db: Session, user_id: int, manual: dict) -> bool:
    """业务范围弹窗「开通」开关：合同查看人员角色，或存在手工业务范围策略。"""
    if _user_has_role(db, user_id, CONTRACT_VIEWER_ROLE_CODE):
        return True
    if manual["scope_mode"] == "ALL":
        return True
    return bool(manual["store_values"] or manual["department_values"] or manual["group_values"])


def _contract_scope_for_user(db: Session, user_id: int) -> dict:
    policies = db.query(DataPolicy).filter(
        DataPolicy.subject_type == "USER",
        DataPolicy.subject_id == user_id,
        DataPolicy.resource_code == BUSINESS_SCOPE_RESOURCE,
        DataPolicy.action_code == BUSINESS_SCOPE_ACTION,
        DataPolicy.effect == "ALLOW",
        DataPolicy.is_active == True,
    ).all()
    if not policies:
        policies = db.query(DataPolicy).filter(
            DataPolicy.subject_type == "USER",
            DataPolicy.subject_id == user_id,
            DataPolicy.resource_code == "contract",
            DataPolicy.action_code == "view",
            DataPolicy.effect == "ALLOW",
            DataPolicy.is_active == True,
        ).all()
    policy_ids = [policy.id for policy in policies]
    values = {"store": [], "department": [], "group": []}
    if policy_ids:
        rows = db.query(DataPolicyItem).filter(DataPolicyItem.policy_id.in_(policy_ids)).all()
        for row in rows:
            if row.dimension_type in values and row.dimension_value not in values[row.dimension_type]:
                values[row.dimension_type].append(row.dimension_value)

    return {
        "scope_mode": "ALL" if any(policy.scope_mode == "ALL" for policy in policies) else "CUSTOM",
        "store_values": values["store"],
        "department_values": values["department"],
        "group_values": values["group"],
        "manual_scope_count": len([policy for policy in policies if (policy.source_type or MANUAL_SOURCE_TYPE).upper() == MANUAL_SOURCE_TYPE]),
        "erp_scope_count": len([policy for policy in policies if (policy.source_type or "").upper() == "ERP"]),
    }


def _ensure_subject_exists(db: Session, subject_type: str, subject_id: int) -> None:
    if subject_type == "ROLE":
        exists = db.query(Role).filter(Role.id == subject_id).first()
    elif subject_type == "USER":
        exists = db.query(User).filter(User.user_id == subject_id).first()
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的授权主体类型")

    if not exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="授权主体不存在")


def _serialize_departments(db: Session, departments: List[Department]) -> List[dict]:
    department_ids = [department.id for department in departments]
    if not department_ids:
        return []
    rows = (
        db.query(Department, Store.store_name, User.real_name)
        .join(Store, Store.store_id == Department.store_id)
        .outerjoin(User, User.user_id == Department.manager_user_id)
        .filter(Department.id.in_(department_ids))
        .order_by(Department.store_id.asc(), Department.dept_code.asc())
        .all()
    )
    return [{
        "id": department.id,
        "store_id": department.store_id,
        "store_name": store_name,
        "dept_code": department.dept_code,
        "dept_name": department.dept_name,
        "parent_id": department.parent_id,
        "manager_user_id": department.manager_user_id,
        "manager_name": manager_name,
        "is_active": department.is_active,
        "created_at": department.created_at,
        "updated_at": department.updated_at,
    } for department, store_name, manager_name in rows]


def _serialize_roles(db: Session, roles: List[Role]) -> List[dict]:
    role_ids = [role.id for role in roles]
    permission_map: Dict[int, List[int]] = defaultdict(list)
    permission_code_map: Dict[int, List[str]] = defaultdict(list)
    if role_ids:
        rows = (
            db.query(RolePermission.role_id, Permission.id, Permission.permission_code)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role_id.in_(role_ids))
            .all()
        )
        for role_id, permission_id, permission_code in rows:
            permission_map[role_id].append(permission_id)
            permission_code_map[role_id].append(permission_code)

    result = []
    for role in roles:
        result.append({
            "id": role.id,
            "role_code": role.role_code,
            "role_name": role.role_name,
            "role_level": role.role_level,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "permission_ids": permission_map.get(role.id, []),
            "permission_codes": permission_code_map.get(role.id, []),
            "created_at": role.created_at,
            "updated_at": role.updated_at,
        })
    return result


def _serialize_users(db: Session, users: List[User]) -> List[dict]:
    user_ids = [user.user_id for user in users]
    role_rows = []
    assignment_rows = []
    store_name_map = {
        store.store_id: store.store_name
        for store in db.query(Store).all()
    }

    if user_ids:
        role_rows = (
            db.query(UserRole.user_id, Role.id, Role.role_code, Role.role_name)
            .join(Role, Role.id == UserRole.role_id)
            .filter(UserRole.user_id.in_(user_ids))
            .all()
        )
        assignment_rows = (
            db.query(
                UserDepartmentPost.id,
                UserDepartmentPost.user_id,
                UserDepartmentPost.store_id,
                UserDepartmentPost.department_id,
                UserDepartmentPost.post_id,
                UserDepartmentPost.is_primary,
                UserDepartmentPost.is_active,
                Department.dept_name,
                Post.post_name,
            )
            .join(Department, Department.id == UserDepartmentPost.department_id)
            .outerjoin(Post, Post.id == UserDepartmentPost.post_id)
            .filter(UserDepartmentPost.user_id.in_(user_ids))
            .all()
        )

    role_id_map: Dict[int, List[int]] = defaultdict(list)
    role_code_map: Dict[int, List[str]] = defaultdict(list)
    role_name_map: Dict[int, List[str]] = defaultdict(list)
    for user_id, role_id, role_code, role_name in role_rows:
        role_id_map[user_id].append(role_id)
        role_code_map[user_id].append(role_code)
        role_name_map[user_id].append(role_name)

    assignment_map: Dict[int, List[dict]] = defaultdict(list)
    for row in assignment_rows:
        assignment_map[row.user_id].append({
            "id": row.id,
            "store_id": row.store_id,
            "store_name": store_name_map.get(row.store_id),
            "department_id": row.department_id,
            "department_name": row.dept_name,
            "post_id": row.post_id,
            "post_name": row.post_name,
            "is_primary": row.is_primary,
            "is_active": row.is_active,
        })

    return [{
        "user_id": user.user_id,
        "username": user.username,
        "real_name": user.real_name,
        "email": user.email,
        "phone": user.phone,
        "status": getattr(user, "status", "ACTIVE") or "ACTIVE",
        "default_store_id": getattr(user, "default_store_id", None),
        "employee_no": getattr(user, "employee_no", None),
        "is_active": user.is_active,
        "role_ids": role_id_map.get(user.user_id, []),
        "role_codes": role_code_map.get(user.user_id, []),
        "role_names": role_name_map.get(user.user_id, []),
        "department_assignments": assignment_map.get(user.user_id, []),
        "last_login": user.last_login,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    } for user in users]


def _serialize_data_policies(db: Session, policies: List[DataPolicy]) -> List[dict]:
    policy_ids = [policy.id for policy in policies]
    items_map: Dict[int, List[dict]] = defaultdict(list)
    if policy_ids:
        item_rows = (
            db.query(DataPolicyItem)
            .filter(DataPolicyItem.policy_id.in_(policy_ids))
            .order_by(DataPolicyItem.id.asc())
            .all()
        )
        for item in item_rows:
            items_map[item.policy_id].append({
                "id": item.id,
                "dimension_type": item.dimension_type,
                "dimension_value": item.dimension_value,
                "include_children": item.include_children,
            })

    role_name_map = {role.id: role.role_name for role in db.query(Role).all()}
    user_name_map = {
        user.user_id: (user.real_name or user.username)
        for user in db.query(User).all()
    }

    result = []
    for policy in policies:
        subject_name = role_name_map.get(policy.subject_id) if policy.subject_type == "ROLE" else user_name_map.get(policy.subject_id)
        result.append({
            "id": policy.id,
            "subject_type": policy.subject_type,
            "subject_id": policy.subject_id,
            "subject_name": subject_name,
            "resource_code": policy.resource_code,
            "action_code": policy.action_code,
            "scope_mode": policy.scope_mode,
            "effect": policy.effect,
            "priority": policy.priority,
            "is_active": policy.is_active,
            "source_type": policy.source_type or MANUAL_SOURCE_TYPE,
            "source_system": policy.source_system or MANUAL_SOURCE_SYSTEM,
            "external_scope_id": policy.external_scope_id,
            "external_scope_name": policy.external_scope_name,
            "synced_at": policy.synced_at,
            "items": items_map.get(policy.id, []),
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        })
    return result


def _date_start(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min)


def _date_end(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.max)


def _detect_login_device_type(user_agent: str | None) -> str:
    if not user_agent:
        return "UNKNOWN"

    normalized = user_agent.lower()
    mobile_tokens = (
        "mobile",
        "android",
        "iphone",
        "ipad",
        "ipod",
        "windows phone",
        "harmonyos",
        "micromessenger",
    )
    if any(token in normalized for token in mobile_tokens):
        return "MOBILE"
    return "DESKTOP"


def _serialize_login_log_rows(rows: list[tuple[LoginLog, str | None, str | None]]) -> list[dict]:
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": username,
            "real_name": real_name,
            "identity_type": log.identity_type,
            "identifier": log.identifier,
            "login_result": log.login_result,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "device_type": _detect_login_device_type(log.user_agent),
            "created_at": log.created_at,
        }
        for log, username, real_name in rows
    ]


def _serialize_operation_log_rows(rows: list[tuple[OperationLog, str | None, str | None]]) -> list[dict]:
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": username,
            "real_name": real_name,
            "action_code": log.action_code,
            "resource_code": log.resource_code,
            "target_id": log.target_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        }
        for log, username, real_name in rows
    ]


@router.get("/permissions", response_model=List[PermissionSchema])
async def get_permissions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.role.manage")
    permissions = db.query(Permission).order_by(Permission.module_code.asc(), Permission.action_code.asc()).all()
    return permissions


@router.get("/login-logs", response_model=dict)
async def get_login_logs(
    keyword: str | None = Query(None, description="用户名、姓名或登录标识"),
    login_result: str | None = Query(None, description="SUCCESS 或 FAILED"),
    identity_type: str | None = Query(None, description="password, wecom 等身份类型"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_system_permission(db, current_user, "system.audit_log.view")
    filters = []
    if keyword:
        like_keyword = f"%{keyword.strip()}%"
        filters.append(or_(
            LoginLog.identifier.ilike(like_keyword),
            User.username.ilike(like_keyword),
            User.real_name.ilike(like_keyword),
        ))
    if login_result and login_result != "ALL":
        filters.append(LoginLog.login_result == login_result)
    if identity_type and identity_type != "ALL":
        filters.append(LoginLog.identity_type == identity_type)
    started_at = _date_start(start_date)
    ended_at = _date_end(end_date)
    if started_at:
        filters.append(LoginLog.created_at >= started_at)
    if ended_at:
        filters.append(LoginLog.created_at <= ended_at)

    base_query = db.query(LoginLog).outerjoin(User, User.user_id == LoginLog.user_id).filter(*filters)
    total = base_query.count()
    rows = (
        db.query(LoginLog, User.username, User.real_name)
        .outerjoin(User, User.user_id == LoginLog.user_id)
        .filter(*filters)
        .order_by(LoginLog.created_at.desc(), LoginLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": _serialize_login_log_rows(rows),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/operation-logs", response_model=dict)
async def get_operation_logs(
    keyword: str | None = Query(None, description="用户名、姓名、目标 ID 或路径"),
    resource_code: str | None = Query(None, description="模块资源编码"),
    action_code: str | None = Query(None, description="动作编码"),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_system_permission(db, current_user, "system.audit_log.view")
    filters = []
    if keyword:
        like_keyword = f"%{keyword.strip()}%"
        filters.append(or_(
            User.username.ilike(like_keyword),
            User.real_name.ilike(like_keyword),
            OperationLog.target_id.ilike(like_keyword),
            OperationLog.resource_code.ilike(like_keyword),
        ))
    if resource_code and resource_code != "ALL":
        filters.append(OperationLog.resource_code == resource_code)
    if action_code and action_code != "ALL":
        filters.append(OperationLog.action_code == action_code)
    started_at = _date_start(start_date)
    ended_at = _date_end(end_date)
    if started_at:
        filters.append(OperationLog.created_at >= started_at)
    if ended_at:
        filters.append(OperationLog.created_at <= ended_at)

    base_query = db.query(OperationLog).outerjoin(User, User.user_id == OperationLog.user_id).filter(*filters)
    total = base_query.count()
    rows = (
        db.query(OperationLog, User.username, User.real_name)
        .outerjoin(User, User.user_id == OperationLog.user_id)
        .filter(*filters)
        .order_by(OperationLog.created_at.desc(), OperationLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": _serialize_operation_log_rows(rows),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/module-access-log", response_model=dict)
async def create_module_access_log(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    module_id = str(payload.get("module_id") or "").strip()
    module_name = str(payload.get("module_name") or "").strip()
    if not module_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模块 ID 不能为空")

    db.add(OperationLog(
        user_id=current_user.user_id,
        action_code="enter",
        resource_code="module",
        target_id=module_id[:100],
        detail={
            "module_id": module_id,
            "module_name": module_name or module_id,
        },
        ip_address=get_client_ip(request),
        created_at=datetime.now(),
    ))
    db.commit()
    return {"message": "模块访问日志已记录"}


@router.get("/posts", response_model=List[PostSchema])
async def get_posts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.user.manage")
    posts = db.query(Post).filter(Post.is_active == True).order_by(Post.level.desc(), Post.id.asc()).all()
    return posts


@router.get("/roles", response_model=List[RoleSchema])
async def get_roles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.role.manage")
    roles = db.query(Role).order_by(Role.role_level.desc(), Role.id.asc()).all()
    return _serialize_roles(db, roles)


@router.post("/roles", response_model=RoleSchema)
async def create_role(payload: RoleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.role.manage")
    existing = db.query(Role).filter(Role.role_code == payload.role_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色编码已存在")
    _ensure_permission_ids_exist(db, payload.permission_ids)

    role = Role(
        role_code=payload.role_code,
        role_name=payload.role_name,
        role_level=payload.role_level,
        is_system=payload.is_system,
        is_active=payload.is_active,
    )
    db.add(role)
    db.flush()
    _sync_role_permissions(db, role.id, payload.permission_ids)
    db.commit()
    db.refresh(role)
    return _serialize_roles(db, [role])[0]


@router.put("/roles/{role_id}", response_model=RoleSchema)
async def update_role(role_id: int, payload: RoleUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.role.manage")
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")

    if payload.role_code and payload.role_code != role.role_code:
        existing = db.query(Role).filter(Role.role_code == payload.role_code, Role.id != role_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色编码已存在")

    update_data = payload.model_dump(exclude_unset=True, exclude={"permission_ids"})
    for field, value in update_data.items():
        setattr(role, field, value)

    if payload.permission_ids is not None:
        _ensure_permission_ids_exist(db, payload.permission_ids)
        _sync_role_permissions(db, role.id, payload.permission_ids)

    db.commit()
    db.refresh(role)
    return _serialize_roles(db, [role])[0]


@router.get("/departments", response_model=List[DepartmentSchema])
async def get_departments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.user.manage")
    departments = db.query(Department).order_by(Department.store_id.asc(), Department.dept_code.asc()).all()
    return _serialize_departments(db, departments)


@router.post("/departments", response_model=DepartmentSchema)
async def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.user.manage")
    existing = db.query(Department).filter(
        Department.store_id == payload.store_id,
        Department.dept_code == payload.dept_code,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="同门店下部门编码已存在")

    department = Department(**payload.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    return _serialize_departments(db, [department])[0]


@router.put("/departments/{department_id}", response_model=DepartmentSchema)
async def update_department(department_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.user.manage")
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="部门不存在")

    update_data = payload.model_dump(exclude_unset=True)
    new_store_id = update_data.get("store_id", department.store_id)
    new_dept_code = update_data.get("dept_code", department.dept_code)
    existing = db.query(Department).filter(
        Department.store_id == new_store_id,
        Department.dept_code == new_dept_code,
        Department.id != department_id,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="同门店下部门编码已存在")

    for field, value in update_data.items():
        setattr(department, field, value)
    db.commit()
    db.refresh(department)
    return _serialize_departments(db, [department])[0]


@router.post("/departments/sync-from-counter-groups", response_model=dict)
async def sync_departments_from_counter_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.user.manage")
    rows = db.execute(
        text(
            """
            SELECT DISTINCT
              COALESCE(st_code.store_id, st_id.store_id, parsed.parsed_store_id) AS store_id,
              TRIM(BOTH FROM COALESCE(dept.mfcode, '')) AS department_code,
              TRIM(BOTH FROM COALESCE(dept.mfcname, '')) AS department_name
            FROM manaframe mf
            CROSS JOIN LATERAL (
              SELECT
                SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) AS parsed_store_code,
                CASE
                  WHEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) ~ '^[0-9]+$'
                  THEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3)::integer
                  ELSE NULL
                END AS parsed_store_id
            ) parsed
            LEFT JOIN manaframe dept
              ON upper(trim(COALESCE(mf.mfpcode, ''))) = upper(trim(COALESCE(dept.mfcode, '')))
            LEFT JOIN stores st_code
              ON TRIM(BOTH FROM COALESCE(st_code.store_code, '')) = parsed.parsed_store_code
            LEFT JOIN stores st_id
              ON st_id.store_id = parsed.parsed_store_id
            WHERE NULLIF(TRIM(BOTH FROM COALESCE(dept.mfcode, '')), '') IS NOT NULL
            """
        )
    ).mappings().all()

    created_count = 0
    updated_count = 0
    skipped_count = 0
    for row in rows:
        dept_code = (row.department_code or "").strip()
        dept_name = (row.department_name or dept_code).strip()
        if not row.store_id or not dept_code:
            skipped_count += 1
            continue

        department = db.query(Department).filter(
            Department.store_id == row.store_id,
            Department.dept_code == dept_code,
        ).first()
        if department:
            if department.dept_name != dept_name or not department.is_active:
                department.dept_name = dept_name
                department.is_active = True
                updated_count += 1
        else:
            db.add(Department(
                store_id=row.store_id,
                dept_code=dept_code,
                dept_name=dept_name,
                is_active=True,
            ))
            created_count += 1

    db.commit()
    return {
        "message": "部门已从柜组同步",
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
    }


@router.get("/users", response_model=List[SystemUserSchema])
async def get_system_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.user.manage")
    users = db.query(User).order_by(User.user_id.desc()).all()
    return _serialize_users(db, users)


@router.post("/users", response_model=SystemUserSchema)
async def create_system_user(payload: SystemUserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.user.manage")
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")

    _ensure_role_ids_exist(db, payload.role_ids)
    _ensure_department_ids_exist(db, [item.department_id for item in payload.department_assignments])

    user = User(
        username=payload.username,
        password_hash=_hash_password(payload.password),
        real_name=payload.real_name,
        email=payload.email,
        phone=payload.phone,
        role="user",
        status=payload.status,
        default_store_id=payload.default_store_id,
        employee_no=payload.employee_no,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()

    _upsert_password_identity(db, user, payload.password)
    _sync_user_roles(db, user.user_id, payload.role_ids)
    _sync_user_department_posts(db, user.user_id, [item.model_dump() for item in payload.department_assignments])

    if payload.role_ids:
        first_role = db.query(Role).filter(Role.id == payload.role_ids[0]).first()
        if first_role:
            user.role = first_role.role_code

    db.commit()
    db.refresh(user)
    return _serialize_users(db, [user])[0]


@router.put("/users/{user_id}", response_model=SystemUserSchema)
async def update_system_user(user_id: int, payload: SystemUserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.user.manage")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if payload.email and payload.email != user.email:
        existing_email = db.query(User).filter(User.email == payload.email, User.user_id != user_id).first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")

    if payload.role_ids is not None:
        _ensure_role_ids_exist(db, payload.role_ids)
    if payload.department_assignments is not None:
        _ensure_department_ids_exist(db, [item.department_id for item in payload.department_assignments])

    update_data = payload.model_dump(exclude_unset=True, exclude={"password", "role_ids", "department_assignments"})
    for field, value in update_data.items():
        setattr(user, field, value)

    if payload.password:
        _upsert_password_identity(db, user, payload.password)

    if payload.role_ids is not None:
        _sync_user_roles(db, user.user_id, payload.role_ids)
        if payload.role_ids:
            first_role = db.query(Role).filter(Role.id == payload.role_ids[0]).first()
            if first_role:
                user.role = first_role.role_code

    if payload.department_assignments is not None:
        _sync_user_department_posts(db, user.user_id, [item.model_dump() for item in payload.department_assignments])

    db.commit()
    db.refresh(user)
    return _serialize_users(db, [user])[0]


@router.get("/data-policies", response_model=List[DataPolicySchema])
async def get_data_policies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.data_policy.manage")
    policies = db.query(DataPolicy).order_by(DataPolicy.priority.asc(), DataPolicy.id.asc()).all()
    return _serialize_data_policies(db, policies)


@router.get("/contract-permissions/options", response_model=dict)
async def get_contract_permission_options(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.data_policy.manage")
    stores = db.query(Store).filter(Store.is_active == True).order_by(Store.store_id.asc()).all()
    # 与合同/销售口径一致：门店–部门–柜组来自同一数据源 manaframe（ERP）。
    # 使用 LEFT JOIN：避免因门店主数据缺失或 INNER JOIN 条件导致整表被放空；仅展示当前可选门店范围内的柜组。
    group_rows = db.execute(
        text(
            """
            WITH manaframe_groups AS (
              SELECT
                mf.mfcode AS group_code,
                mf.mfcname AS group_name,
                dept.mfcode AS department_code,
                dept.mfcname AS department_name,
                parsed.parsed_store_code,
                parsed.parsed_store_id,
                mf.mfzlgh AS brand_name
              FROM manaframe mf
              CROSS JOIN LATERAL (
                SELECT
                  SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) AS parsed_store_code,
                  CASE
                    WHEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) ~ '^[0-9]+$'
                    THEN SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3)::integer
                    ELSE NULL
                  END AS parsed_store_id
              ) parsed
              LEFT JOIN manaframe dept
                ON upper(trim(COALESCE(mf.mfpcode, ''))) = upper(trim(COALESCE(dept.mfcode, '')))
            )
            SELECT
              ROW_NUMBER() OVER (
                ORDER BY COALESCE(st_code.store_id, st_id.store_id, mg.parsed_store_id) ASC,
                         mg.department_code ASC,
                         mg.group_code ASC
              ) AS group_id,
              mg.group_code,
              mg.group_name,
              mg.department_code,
              mg.department_name,
              COALESCE(st_code.store_id, st_id.store_id, mg.parsed_store_id) AS store_id,
              mg.brand_name,
              COALESCE(st_code.store_name, st_id.store_name) AS store_name
            FROM manaframe_groups mg
            LEFT JOIN stores st_code
              ON TRIM(BOTH FROM COALESCE(st_code.store_code, '')) = mg.parsed_store_code
            LEFT JOIN stores st_id
              ON st_id.store_id = mg.parsed_store_id
            ORDER BY COALESCE(st_code.store_id, st_id.store_id, mg.parsed_store_id) ASC,
                     mg.department_code ASC,
                     mg.group_code ASC
            """
        )
    ).mappings().all()
    scope_matrix = [
        {
            "store_id": row["store_id"],
            "store_code": str(row["store_id"]),
            "store_name": (row["store_name"] or "").strip() or (f"门店#{row['store_id']}" if row["store_id"] is not None else ""),
            "department_code": (row["department_code"] or "").strip(),
            "department_name": (row["department_name"] or "").strip(),
            "group_id": row["group_id"],
            "group_code": row["group_code"],
            "group_name": row["group_name"],
        }
        for row in group_rows
    ]
    return {
        "stores": [
            {"id": store.store_id, "code": str(store.store_id), "name": store.store_name}
            for store in stores
        ],
        "departments": [],
        "groups": [
            {
                "id": row["group_id"],
                "store_id": row["store_id"],
                "code": row["group_code"],
                "name": row["group_name"],
                "department_code": row["department_code"],
                "department_name": row["department_name"],
                "brand_name": row["brand_name"],
            }
            for row in group_rows
        ],
        "scope_matrix": scope_matrix,
    }


@router.get("/contract-permissions", response_model=List[dict])
async def get_contract_permissions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.data_policy.manage")
    users = db.query(User).order_by(User.user_id.desc()).all()
    serialized_users = _serialize_users(db, users)
    result = []
    for user in serialized_users:
        scope = _contract_scope_for_user(db, user["user_id"])
        manual = _manual_business_scope_for_user(db, user["user_id"])
        result.append({
            "user_id": user["user_id"],
            "username": user["username"],
            "real_name": user["real_name"],
            "employee_no": user["employee_no"],
            "status": user["status"],
            "is_active": user["is_active"],
            "role_names": user["role_names"],
            "has_contract_view": _user_has_permission(db, user["user_id"], "contract.view"),
            "scope_tab_active": _scope_tab_active_from_manual(db, user["user_id"], manual),
            "manual_scope_mode": manual["scope_mode"],
            "manual_store_values": manual["store_values"],
            "manual_department_values": manual["department_values"],
            "manual_group_values": manual["group_values"],
            **scope,
        })
    return result


@router.put("/contract-permissions/{user_id}", response_model=dict)
async def update_contract_permission(user_id: int, payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.data_policy.manage")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    enabled = bool(payload.get("enabled"))
    viewer_role = _ensure_contract_viewer_role(db)

    db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == viewer_role.id,
    ).delete()
    db.query(DataPolicy).filter(
        DataPolicy.subject_type == "USER",
        DataPolicy.subject_id == user_id,
        DataPolicy.resource_code == BUSINESS_SCOPE_RESOURCE,
        DataPolicy.action_code == BUSINESS_SCOPE_ACTION,
        DataPolicy.source_type == MANUAL_SOURCE_TYPE,
        DataPolicy.source_system == MANUAL_SOURCE_SYSTEM,
    ).delete()

    if enabled:
        db.add(UserRole(user_id=user_id, role_id=viewer_role.id))
        scope_mode = payload.get("scope_mode") or "CUSTOM"
        if scope_mode not in {"ALL", "CUSTOM"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的范围模式")

        policy = DataPolicy(
            subject_type="USER",
            subject_id=user_id,
            resource_code=BUSINESS_SCOPE_RESOURCE,
            action_code=BUSINESS_SCOPE_ACTION,
            scope_mode=scope_mode,
            effect="ALLOW",
            priority=100,
            is_active=True,
            source_type=MANUAL_SOURCE_TYPE,
            source_system=MANUAL_SOURCE_SYSTEM,
        )
        db.add(policy)
        db.flush()

        if scope_mode == "CUSTOM":
            items = []
            for dimension_type, field in (
                ("store", "store_values"),
                ("department", "department_values"),
                ("group", "group_values"),
            ):
                for value in payload.get(field) or []:
                    value_text = str(value).strip()
                    if value_text:
                        items.append({
                            "dimension_type": dimension_type,
                            "dimension_value": value_text,
                            "include_children": False,
                        })
            if not items:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请至少选择一个门店、部门或柜组")
            _sync_policy_items(db, policy.id, items)

    db.commit()
    return {"message": "业务数据范围已保存"}


@router.post("/data-policies", response_model=DataPolicySchema)
async def create_data_policy(payload: DataPolicyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.data_policy.manage")
    _ensure_subject_exists(db, payload.subject_type, payload.subject_id)
    policy = DataPolicy(
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        resource_code=payload.resource_code,
        action_code=payload.action_code,
        scope_mode=payload.scope_mode,
        effect=payload.effect,
        priority=payload.priority,
        is_active=payload.is_active,
        source_type=payload.source_type,
        source_system=payload.source_system,
        external_scope_id=payload.external_scope_id,
        external_scope_name=payload.external_scope_name,
        synced_at=payload.synced_at,
    )
    db.add(policy)
    db.flush()
    _sync_policy_items(db, policy.id, [item.model_dump() for item in payload.items])
    db.commit()
    db.refresh(policy)
    return _serialize_data_policies(db, [policy])[0]


@router.put("/data-policies/{policy_id}", response_model=DataPolicySchema)
async def update_data_policy(policy_id: int, payload: DataPolicyUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.data_policy.manage")
    policy = db.query(DataPolicy).filter(DataPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数据策略不存在")

    update_data = payload.model_dump(exclude_unset=True, exclude={"items"})
    new_subject_type = update_data.get("subject_type", policy.subject_type)
    new_subject_id = update_data.get("subject_id", policy.subject_id)
    _ensure_subject_exists(db, new_subject_type, new_subject_id)
    for field, value in update_data.items():
        setattr(policy, field, value)

    if payload.items is not None:
        _sync_policy_items(db, policy.id, [item.model_dump() for item in payload.items])

    db.commit()
    db.refresh(policy)
    return _serialize_data_policies(db, [policy])[0]


@router.get("/meta", response_model=dict)
async def get_system_meta(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_system_permission(db, current_user, "system.data_policy.manage")
    return {
        "subject_types": ["ROLE", "USER"],
        "resource_codes": ["business_scope", "counter", "hall", "tenant", "contract", "bill", "revenue", "sales", "settlement"],
        "action_codes": ["view", "edit", "approve", "export"],
        "scope_modes": ["ALL", "SELF", "CUSTOM"],
        "effects": ["ALLOW", "DENY"],
        "dimension_types": ["store", "department", "group", "floor", "unit", "supplier", "brand", "category"],
        "users": [{"id": user.user_id, "name": user.real_name or user.username} for user in db.query(User).order_by(User.user_id.asc()).all()],
        "roles": [{"id": role.id, "name": role.role_name} for role in db.query(Role).filter(Role.is_active == True).order_by(Role.role_level.desc()).all()],
    }


@router.get("/health", response_model=BaseResponse)
async def system_management_health():
    return BaseResponse(message="系统管理模块可用")
