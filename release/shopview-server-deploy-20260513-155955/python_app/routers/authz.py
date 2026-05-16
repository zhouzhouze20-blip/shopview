"""
Shared authorization helpers.
"""
from dataclasses import dataclass, field
from typing import Iterable

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from models.models import DataPolicy, DataPolicyItem, Permission, Role, RolePermission, User, UserRole
from models.database import SessionLocal, get_db
from routers.auth import get_current_user


ADMIN_ROLE_CODES = {"super_admin", "system_admin"}

CORE_PERMISSION_DEFINITIONS = [
    ("dashboard.view", "查看驾驶舱", "dashboard", "view"),
    ("store.view", "查看门店", "store", "view"),
    ("store.create", "创建门店", "store", "create"),
    ("store.edit", "编辑门店", "store", "edit"),
    ("store.delete", "删除门店", "store", "delete"),
    ("floor.view", "查看楼层", "floor", "view"),
    ("floor.create", "创建楼层", "floor", "create"),
    ("floor.edit", "编辑楼层", "floor", "edit"),
    ("floor.delete", "删除楼层", "floor", "delete"),
    ("counter.view", "查看柜位", "counter", "view"),
    ("counter.create", "创建柜位", "counter", "create"),
    ("counter.edit", "编辑柜位", "counter", "edit"),
    ("counter.delete", "删除柜位", "counter", "delete"),
    ("business_unit.view", "查看经营单元", "business_unit", "view"),
    ("counter_group.create", "创建柜组", "counter_group", "create"),
    ("business_unit.create", "创建经营单元", "business_unit", "create"),
    ("business_unit.edit", "编辑经营单元", "business_unit", "edit"),
    ("business_unit.delete", "删除经营单元", "business_unit", "delete"),
    ("tenant.view", "查看商户", "tenant", "view"),
    ("tenant.create", "创建商户", "tenant", "create"),
    ("tenant.edit", "编辑商户", "tenant", "edit"),
    ("tenant.delete", "删除商户", "tenant", "delete"),
    ("supplier.view", "查看供应商", "supplier", "view"),
    ("supplier.create", "创建供应商", "supplier", "create"),
    ("supplier.edit", "编辑供应商", "supplier", "edit"),
    ("supplier.delete", "删除供应商", "supplier", "delete"),
    ("base_map.view", "查看底图", "base_map", "view"),
    ("base_map.create", "创建底图", "base_map", "create"),
    ("base_map.edit", "编辑底图", "base_map", "edit"),
    ("base_map.delete", "删除底图", "base_map", "delete"),
    ("unit_map_version.view", "查看柜位图版本", "unit_map_version", "view"),
    ("unit_map_version.create", "创建柜位图版本", "unit_map_version", "create"),
    ("unit_map_version.edit", "编辑柜位图版本", "unit_map_version", "edit"),
    ("unit_map_version.delete", "删除柜位图版本", "unit_map_version", "delete"),
    ("contract.view", "查看合同", "contract", "view"),
    ("sales.view", "查看销售", "sales", "view"),
    ("settlement.view", "查看结算单", "settlement", "view"),
    ("system.audit_log.view", "查看审计日志", "system", "audit_log_view"),
]


@dataclass
class DataScope:
    all_access: bool = False
    allow: dict[str, set[str]] = field(default_factory=dict)
    deny: dict[str, set[str]] = field(default_factory=dict)

    def has_any_allow(self) -> bool:
        return self.all_access or any(values for values in self.allow.values())


def _norm(value: object) -> str:
    return str(value or "").strip().upper()


def _add_value(target: dict[str, set[str]], dimension: str, value: object) -> None:
    normalized = _norm(value)
    if not normalized:
        return
    target.setdefault(dimension, set()).add(normalized)


def get_role_codes(db: Session, user_id: int) -> set[str]:
    rows = (
        db.query(Role.role_code)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(
            UserRole.user_id == user_id,
            Role.is_active == True,
            or_(UserRole.expires_at.is_(None), UserRole.expires_at > func.now()),
        )
        .all()
    )
    return {row.role_code for row in rows}


def is_admin(db: Session, user: User) -> bool:
    return bool(get_role_codes(db, user.user_id) & ADMIN_ROLE_CODES)


def require_permission(db: Session, user: User, permission_code: str) -> None:
    if is_admin(db, user):
        return

    exists = (
        db.query(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == user.user_id,
            Role.is_active == True,
            Permission.permission_code == permission_code,
            or_(UserRole.expires_at.is_(None), UserRole.expires_at > func.now()),
        )
        .first()
    )
    if not exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无功能权限")


def require_permission_dependency(permission_code: str):
    """Build a FastAPI dependency that requires login and a specific function permission."""

    def dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        require_permission(db, current_user, permission_code)
        return current_user

    return dependency


def ensure_core_permissions() -> None:
    """Ensure permission rows used by protected business write APIs exist."""
    db = SessionLocal()
    try:
        for permission_code, permission_name, module_code, action_code in CORE_PERMISSION_DEFINITIONS:
            exists = db.query(Permission.id).filter(Permission.permission_code == permission_code).first()
            if exists:
                continue
            db.add(
                Permission(
                    permission_code=permission_code,
                    permission_name=permission_name,
                    module_code=module_code,
                    action_code=action_code,
                )
            )
        db.commit()
    except ProgrammingError:
        db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_data_scope(db: Session, user: User, resource_code: str, action_code: str) -> DataScope:
    if is_admin(db, user):
        return DataScope(all_access=True)

    return _load_scope_from_policies(db, user, resource_code, action_code)


def _load_scope_from_policies(
    db: Session,
    user: User,
    resource_code: str,
    action_code: str,
    *,
    source_type: str | None = None,
    source_system: str | None = None,
    user_only: bool = False,
) -> DataScope:
    role_ids = [
        row.id
        for row in (
            db.query(Role.id)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(
                UserRole.user_id == user.user_id,
                Role.is_active == True,
                or_(UserRole.expires_at.is_(None), UserRole.expires_at > func.now()),
            )
            .all()
        )
    ]

    subject_filters = [(DataPolicy.subject_type == "USER") & (DataPolicy.subject_id == user.user_id)]
    if role_ids and not user_only:
        subject_filters.append((DataPolicy.subject_type == "ROLE") & (DataPolicy.subject_id.in_(role_ids)))

    filters = [
        DataPolicy.resource_code == resource_code,
        DataPolicy.action_code == action_code,
        DataPolicy.is_active == True,
        or_(*subject_filters),
    ]
    if source_type is not None:
        filters.append(DataPolicy.source_type == source_type)
    if source_system is not None:
        filters.append(DataPolicy.source_system == source_system)

    policies = (
        db.query(DataPolicy)
        .filter(*filters)
        .order_by(DataPolicy.priority.asc(), DataPolicy.id.asc())
        .all()
    )

    scope = DataScope()
    for policy in policies:
        effect_target = scope.deny if policy.effect == "DENY" else scope.allow
        if policy.scope_mode == "ALL":
            if policy.effect == "DENY":
                _add_value(effect_target, "__all__", "*")
            else:
                scope.all_access = True
            continue
        if policy.scope_mode == "SELF":
            _add_value(effect_target, "self", user.user_id)
            continue

        items = db.query(DataPolicyItem).filter(DataPolicyItem.policy_id == policy.id).all()
        for item in items:
            _add_value(effect_target, item.dimension_type, item.dimension_value)

    return scope


def load_business_scope(db: Session, user: User, *, fallback_resource_code: str | None = None) -> DataScope:
    """Load the unified business data scope used by contracts, sales, settlements and revenue."""
    if is_admin(db, user):
        return DataScope(all_access=True)

    manual_scope = _load_scope_from_policies(
        db,
        user,
        "business_scope",
        "view",
        source_type="MANUAL",
        source_system="shopview",
        user_only=True,
    )
    if manual_scope.has_any_allow():
        return manual_scope

    scope = load_data_scope(db, user, "business_scope", "view")
    if scope.has_any_allow() or not fallback_resource_code:
        return scope
    return load_data_scope(db, user, fallback_resource_code, "view")


def _matches(values: Iterable[object], allowed: set[str]) -> bool:
    return any(_norm(value) in allowed for value in values)


def scope_allows_business(
    scope: DataScope,
    *,
    store_id: object = None,
    department_code: object = None,
    department_name: object = None,
    group_code: object = None,
    supplier_code: object = None,
    brand_code: object = None,
    brand_name: object = None,
    category_code: object = None,
    category_name: object = None,
) -> bool:
    if "__all__" in scope.deny:
        return False

    if _matches([store_id], scope.deny.get("store", set())):
        return False
    if _matches([department_code, department_name], scope.deny.get("department", set())):
        return False
    if _matches([group_code], scope.deny.get("group", set())):
        return False
    if _matches([supplier_code], scope.deny.get("supplier", set())):
        return False
    if _matches([brand_code, brand_name], scope.deny.get("brand", set())):
        return False
    if _matches([category_code, category_name], scope.deny.get("category", set())):
        return False

    if scope.all_access:
        return True
    if _matches([group_code], scope.allow.get("group", set())):
        return True
    if _matches([department_code, department_name], scope.allow.get("department", set())):
        return True
    if _matches([store_id], scope.allow.get("store", set())):
        return True
    if _matches([supplier_code], scope.allow.get("supplier", set())):
        return True
    if _matches([brand_code, brand_name], scope.allow.get("brand", set())):
        return True
    if _matches([category_code, category_name], scope.allow.get("category", set())):
        return True
    return False


def scope_allows_contract(scope: DataScope, *, store_id: object = None, department_code: object = None, department_name: object = None, group_code: object = None) -> bool:
    return scope_allows_business(
        scope,
        store_id=store_id,
        department_code=department_code,
        department_name=department_name,
        group_code=group_code,
    )
