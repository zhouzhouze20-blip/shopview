"""
Shared authorization helpers.
"""
from dataclasses import dataclass, field
from typing import Iterable

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from models.models import DataPolicy, DataPolicyItem, Permission, Role, RolePermission, User, UserRole
from models.database import SessionLocal, get_db
from routers.auth import get_current_user


ADMIN_ROLE_CODES = {"super_admin", "system_admin"}
DEFAULT_VIEW_ONLY_ROLE_CODES = {
    "store_admin",
    "dept_manager",
    "group_manager",
    "finance",
    "viewer",
    "contract_viewer",
}

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
    ("contract.edit", "维护合同", "contract", "edit"),
    ("contract.unit_binding.edit", "编辑合同柜位号", "contract", "unit_binding_edit"),
    ("sales.view", "查看销售", "sales", "view"),
    (
        "sales.category_performance.view",
        "查看品类主管绩效",
        "sales",
        "category_performance_view",
    ),
    (
        "sales.category_performance.manage",
        "维护品类主管绩效",
        "sales",
        "category_performance_manage",
    ),
    (
        "sales.brand_member_analysis.view",
        "查看品牌会员分析",
        "sales",
        "brand_member_analysis_view",
    ),
    ("sales.od0002.view", "查看OD0002门店销售毛利汇总表", "sales", "od0002_view"),
    (
        "sales.commodity_detail.view",
        "查看商品销售明细",
        "sales",
        "commodity_detail_view",
    ),
    (
        "sales.settled_gross_profit.view",
        "查看结算后销售毛利排行表",
        "sales",
        "settled_gross_profit_view",
    ),
    (
        "sales.od0001.view",
        "查看OD0001销售逐日跟进表",
        "sales",
        "od0001_view",
    ),
    (
        "sales.od0003.view",
        "查看OD0003中心销售跟进表",
        "sales",
        "od0003_view",
    ),
    (
        "sales.od0004.view",
        "查看OD0004销售逐月跟进表",
        "sales",
        "od0004_view",
    ),
    (
        "sales.od0005.view",
        "查看OD0005微商城品牌销售统计",
        "sales",
        "od0005_view",
    ),
    (
        "sales.hy0001.view",
        "查看HY0001重点品牌会员消费情况",
        "sales",
        "hy0001_view",
    ),
    (
        "sales.non_rental_monthly_revenue.view",
        "查看非租赁品牌月度收益表",
        "sales",
        "non_rental_monthly_revenue_view",
    ),
    ("sales.hdyy01.view", "查看HDYY01柜组经营分析表", "sales", "hdyy01_view"),
    ("sales.inventory.view", "查看实时库存查询", "sales", "inventory_view"),
    ("sales.inventory_history.view", "查看历史库存明细报表", "sales", "inventory_history_view"),
    ("sales.inventory_movement.view", "查看进销存明细报表", "sales", "inventory_movement_view"),
    ("mobile.sales.view", "查看手机端销售看板", "mobile", "sales_view"),
    ("mobile.contracts.view", "查看手机端合同台账", "mobile", "contracts_view"),
    ("mobile.inventory.view", "查看手机端实时库存查询", "mobile", "inventory_view"),
    (
        "mobile.revenue_dashboard.view",
        "查看手机端收益看板",
        "mobile",
        "revenue_dashboard_view",
    ),
    ("activity_analysis.view", "查看活动分析", "activity_analysis", "view"),
    ("activity_analysis.points.view", "查看积分活动核对", "activity_analysis", "points_view"),
    ("activity_analysis.star_diamond.view", "查看中心星钻会员", "activity_analysis", "star_diamond_view"),
    ("activity_settlement.voucher_match.view", "查看凭证匹配", "activity_settlement", "voucher_match_view"),
    ("activity_settlement.voucher_match.confirm", "确认凭证匹配", "activity_settlement", "voucher_match_confirm"),
    ("activity_settlement.voucher_match.reject", "驳回凭证匹配", "activity_settlement", "voucher_match_reject"),
    ("activity_settlement.coupon_monthly.view", "查看卡券月结", "activity_settlement", "coupon_monthly_view"),
    ("activity_settlement.coupon_monthly.rebuild", "重建卡券月结", "activity_settlement", "coupon_monthly_rebuild"),
    ("activity_settlement.coupon_monthly.confirm", "确认卡券月结", "activity_settlement", "coupon_monthly_confirm"),
    ("activity_settlement.coupon_monthly.carryover_create", "新增卡券NC结转", "activity_settlement", "coupon_monthly_carryover_create"),
    ("activity_settlement.confirmed_revenue.view", "查看确认收入占比", "activity_settlement", "confirmed_revenue_view"),
    ("settlement.view", "查看结算单", "settlement", "view"),
    ("revenue.view", "查看收益", "revenue", "view"),
    ("revenue.dashboard.view", "查看收益看板", "revenue", "dashboard_view"),
    ("revenue.recalculate", "重算收益汇总", "revenue", "recalculate"),
    ("revenue.extra.create", "创建收益补录", "revenue", "extra_create"),
    ("revenue.extra.edit", "编辑收益补录", "revenue", "extra_edit"),
    ("revenue.extra.confirm", "确认收益补录", "revenue", "extra_confirm"),
    ("revenue.extra.void", "作废收益补录", "revenue", "extra_void"),
    ("merchant_planning.view", "查看招商规划", "merchant_planning", "view"),
    ("merchant_planning.manage", "管理招商规划", "merchant_planning", "manage"),
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


def is_view_permission_code(permission_code: str) -> bool:
    return str(permission_code or "").strip().endswith(".view")


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


def get_authz_subject(db: Session, user: User) -> User:
    """Return the user whose permissions/data scope should be evaluated.

    In admin view mode the login identity remains the administrator, but module
    permissions and data ranges are evaluated as the selected target user.
    """
    target_user_id = getattr(user, "admin_view_user_id", None)
    if not target_user_id or not is_admin(db, user):
        return user

    target = (
        db.query(User)
        .filter(
            User.user_id == target_user_id,
            User.is_active == True,
            or_(User.status.is_(None), User.status.notin_(["DISABLED", "LOCKED"])),
        )
        .first()
    )
    return target or user


def require_permission(db: Session, user: User, permission_code: str) -> None:
    authz_user = get_authz_subject(db, user)
    if is_admin(db, authz_user):
        return

    exists = (
        db.query(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.user_id == authz_user.user_id,
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


def ensure_default_roles_are_view_only() -> None:
    """Remove operation permissions from default business roles.

    New module view permissions remain selectable in role management because this
    only removes non-*.view permissions from the built-in business/viewer roles.
    """
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                DELETE FROM role_permissions rp
                USING roles r, permissions p
                WHERE rp.role_id = r.id
                  AND rp.permission_id = p.id
                  AND r.role_code = ANY(:role_codes)
                  AND p.permission_code NOT LIKE '%.view'
                """
            ),
            {"role_codes": sorted(DEFAULT_VIEW_ONLY_ROLE_CODES)},
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
    authz_user = get_authz_subject(db, user)
    if is_admin(db, authz_user):
        return DataScope(all_access=True)

    return _load_scope_from_policies(db, authz_user, resource_code, action_code)


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
    """Load user-level business data scope used by contracts, sales, settlements and revenue."""
    authz_user = get_authz_subject(db, user)
    if is_admin(db, authz_user):
        return DataScope(all_access=True)

    return _load_scope_from_policies(
        db,
        authz_user,
        "business_scope",
        "view",
        user_only=True,
    )


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
