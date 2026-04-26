"""
系统管理与权限配置 API
"""
import base64
import hashlib
import os
from collections import defaultdict
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.models import (
    DataPolicy,
    DataPolicyItem,
    Department,
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
            "items": items_map.get(policy.id, []),
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        })
    return result


@router.get("/permissions", response_model=List[PermissionSchema])
async def get_permissions(db: Session = Depends(get_db)):
    permissions = db.query(Permission).order_by(Permission.module_code.asc(), Permission.action_code.asc()).all()
    return permissions


@router.get("/posts", response_model=List[PostSchema])
async def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.is_active == True).order_by(Post.level.desc(), Post.id.asc()).all()
    return posts


@router.get("/roles", response_model=List[RoleSchema])
async def get_roles(db: Session = Depends(get_db)):
    roles = db.query(Role).order_by(Role.role_level.desc(), Role.id.asc()).all()
    return _serialize_roles(db, roles)


@router.post("/roles", response_model=RoleSchema)
async def create_role(payload: RoleCreate, db: Session = Depends(get_db)):
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
async def update_role(role_id: int, payload: RoleUpdate, db: Session = Depends(get_db)):
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
async def get_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).order_by(Department.store_id.asc(), Department.dept_code.asc()).all()
    return _serialize_departments(db, departments)


@router.post("/departments", response_model=DepartmentSchema)
async def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
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
async def update_department(department_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db)):
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


@router.get("/users", response_model=List[SystemUserSchema])
async def get_system_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.user_id.desc()).all()
    return _serialize_users(db, users)


@router.post("/users", response_model=SystemUserSchema)
async def create_system_user(payload: SystemUserCreate, db: Session = Depends(get_db)):
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
async def update_system_user(user_id: int, payload: SystemUserUpdate, db: Session = Depends(get_db)):
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
async def get_data_policies(db: Session = Depends(get_db)):
    policies = db.query(DataPolicy).order_by(DataPolicy.priority.asc(), DataPolicy.id.asc()).all()
    return _serialize_data_policies(db, policies)


@router.post("/data-policies", response_model=DataPolicySchema)
async def create_data_policy(payload: DataPolicyCreate, db: Session = Depends(get_db)):
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
    )
    db.add(policy)
    db.flush()
    _sync_policy_items(db, policy.id, [item.model_dump() for item in payload.items])
    db.commit()
    db.refresh(policy)
    return _serialize_data_policies(db, [policy])[0]


@router.put("/data-policies/{policy_id}", response_model=DataPolicySchema)
async def update_data_policy(policy_id: int, payload: DataPolicyUpdate, db: Session = Depends(get_db)):
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
async def get_system_meta(db: Session = Depends(get_db)):
    return {
        "subject_types": ["ROLE", "USER"],
        "resource_codes": ["counter", "hall", "tenant", "contract", "bill", "revenue"],
        "action_codes": ["view", "edit", "approve", "export"],
        "scope_modes": ["ALL", "SELF", "CUSTOM"],
        "effects": ["ALLOW", "DENY"],
        "dimension_types": ["store", "department", "group", "floor", "unit"],
        "users": [{"id": user.user_id, "name": user.real_name or user.username} for user in db.query(User).order_by(User.user_id.asc()).all()],
        "roles": [{"id": role.id, "name": role.role_name} for role in db.query(Role).filter(Role.is_active == True).order_by(Role.role_level.desc()).all()],
    }


@router.get("/health", response_model=BaseResponse)
async def system_management_health():
    return BaseResponse(message="系统管理模块可用")
