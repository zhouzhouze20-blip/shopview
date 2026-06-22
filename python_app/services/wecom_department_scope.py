"""
Enterprise WeChat department to ShopView business-scope helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models.models import DataPolicy, DataPolicyItem, Department


BUSINESS_SCOPE_RESOURCE = "business_scope"
BUSINESS_SCOPE_ACTION = "view"
WECOM_SOURCE_TYPE = "WECOM"
WECOM_SOURCE_SYSTEM = "wecom"
AUTO_SCOPE_EXTERNAL_PREFIX = "wecom-auto-department"

DEPARTMENT_ALIASES: dict[str, str] = {
    "中心B部(超市)": "中心BF部(超市)",
    "中心B部(生鲜)": "中心BF部(生鲜)",
    "中心五部(运动)": "中心五部(运休)",
    "中心市场部--营运": "中心营运部",
    "中心市场部--客服": "中心企划客服部",
    "中心市场部--企划": "中心企划执行部",
    "大楼营运": "营运四部",
}


@dataclass(frozen=True)
class DepartmentScopeRefreshResult:
    updated: bool
    department_code: str = ""
    department_name: str = ""
    reason: str = ""


def normalize_department_name(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .replace("（", "(")
        .replace("）", ")")
        .replace("\\", "/")
    )


def department_leaf_names(department_path: str) -> list[str]:
    names: list[str] = []
    chunks = [
        chunk.strip()
        for chunk in str(department_path or "").replace("；", ";").replace("，", ";").replace(",", ";").split(";")
        if chunk.strip()
    ]
    for chunk in chunks:
        parts = [normalize_department_name(part) for part in chunk.split("/") if normalize_department_name(part)]
        if parts and parts[-1] not in names:
            names.append(parts[-1])
    return names


def _department_rows(db) -> list[Any]:
    query = db.query(Department)
    try:
        query = query.filter(Department.is_active == True)
    except Exception:
        pass
    return query.all()


def resolve_business_department(db, department_path: str):
    leaves = department_leaf_names(department_path)
    if not leaves:
        return None

    departments = _department_rows(db)
    by_name = {
        normalize_department_name(getattr(department, "dept_name", "")): department
        for department in departments
        if normalize_department_name(getattr(department, "dept_name", ""))
    }
    by_code = {
        normalize_department_name(getattr(department, "dept_code", "")): department
        for department in departments
        if normalize_department_name(getattr(department, "dept_code", ""))
    }

    for leaf in leaves:
        normalized_leaf = normalize_department_name(leaf)
        alias = DEPARTMENT_ALIASES.get(normalized_leaf)
        if alias and normalize_department_name(alias) in by_name:
            return by_name[normalize_department_name(alias)]
        if normalized_leaf in by_name:
            return by_name[normalized_leaf]
        if normalized_leaf in by_code:
            return by_code[normalized_leaf]
    return None


def _auto_external_scope_id(user_id: int) -> str:
    return f"{AUTO_SCOPE_EXTERNAL_PREFIX}:{user_id}"


def _delete_auto_scope(db, user_id: int) -> int:
    external_scope_id = _auto_external_scope_id(user_id)
    existing = [
        policy
        for policy in db.query(DataPolicy)
        .filter(
            DataPolicy.subject_type == "USER",
            DataPolicy.subject_id == user_id,
            DataPolicy.resource_code == BUSINESS_SCOPE_RESOURCE,
            DataPolicy.action_code == BUSINESS_SCOPE_ACTION,
            DataPolicy.source_type == WECOM_SOURCE_TYPE,
            DataPolicy.source_system == WECOM_SOURCE_SYSTEM,
            DataPolicy.external_scope_id == external_scope_id,
        )
        .all()
    ]
    policy_ids = [policy.id for policy in existing if getattr(policy, "id", None) is not None]
    if not policy_ids:
        return 0
    db.query(DataPolicyItem).filter(DataPolicyItem.policy_id.in_(policy_ids)).delete(synchronize_session=False)
    db.query(DataPolicy).filter(DataPolicy.id.in_(policy_ids)).delete(synchronize_session=False)
    return len(policy_ids)


def refresh_auto_department_scope(
    db,
    *,
    user,
    wecom_user_id: str,
    department_path: str,
) -> DepartmentScopeRefreshResult:
    department = resolve_business_department(db, department_path)
    if not department:
        return DepartmentScopeRefreshResult(updated=False, reason="department_mapping_missing")

    user_id = int(user.user_id)
    _delete_auto_scope(db, user_id)
    now = datetime.now()
    policy = DataPolicy(
        subject_type="USER",
        subject_id=user_id,
        resource_code=BUSINESS_SCOPE_RESOURCE,
        action_code=BUSINESS_SCOPE_ACTION,
        scope_mode="CUSTOM",
        effect="ALLOW",
        priority=55,
        is_active=True,
        source_type=WECOM_SOURCE_TYPE,
        source_system=WECOM_SOURCE_SYSTEM,
        external_scope_id=_auto_external_scope_id(user_id),
        external_scope_name=f"{getattr(user, 'real_name', None) or wecom_user_id} 企业微信自动部门范围",
        synced_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(policy)
    db.flush()
    db.add(
        DataPolicyItem(
            policy_id=policy.id,
            dimension_type="department",
            dimension_value=str(department.dept_code),
            include_children=False,
            created_at=now,
        )
    )
    return DepartmentScopeRefreshResult(
        updated=True,
        department_code=str(department.dept_code),
        department_name=str(department.dept_name),
    )
