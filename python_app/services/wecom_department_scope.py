"""
Enterprise WeChat department to ShopView business-scope helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import or_

from models.models import CounterGroup, DataPolicy, DataPolicyItem, Department


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
    "中心特业部": "中心八部(特业)",
    "大楼营运": "营运四部",
}

DEPARTMENT_SCOPE_EXPANSIONS: dict[str, list[str]] = {
    "中心一部(化妆)": ["中心一部(名品)"],
    "中心一部(名品)": ["中心一部(化妆)"],
}

KNOWN_USER_DEPARTMENTS: dict[str, list[str]] = {
    "黄莉倩": ["中心B部(超市)"],
    "丁娅": ["中心特业部"],
    "何蕾": ["中心B部(超市)"],
    "高敏": ["中心B部(生鲜)"],
    "陈晓楠": ["中心一部(化妆)"],
    "薛涌": ["中心一部(化妆)"],
    "花玲": ["中心一部(化妆)"],
    "黄欣怡": ["中心一部(名品)"],
    "于云": ["中心二部(女装)"],
    "凡水晶": ["中心二部(女装)"],
    "潘婷": ["中心二部(女装)"],
    "隆晓蓉": ["中心三部(女装)"],
    "孙琴莹": ["中心三部(女装)"],
    "孙琴蕾": ["中心三部(女装)"],
    "陈蓉": ["中心三部(女装)"],
    "王科涵": ["中心三部(女装)"],
    "蒋佳卫": ["中心四部(男装)"],
    "谈菲": ["中心五部(运动)", "中心六部(儿童)"],
    "吴炯萱": ["中心六部(儿童)"],
    "吴彪": ["中心六部(儿童)"],
    "贺丽": ["中心七部(家居)"],
    "宋军": ["中心七部(家居)"],
    "蒋昊": ["中心市场部--营运"],
    "程益": ["中心市场部--营运"],
    "徐丹妮": ["中心市场部--客服"],
    "俞陈": ["中心市场部--企划"],
    "丁丽娜": ["中心市场部--企划"],
    "丁岚": ["营运一部"],
    "刘露露": ["营运二部"],
    "王南": ["营运三部"],
    "屠云": ["大楼营运"],
    "周霞": ["新世纪一部(化妆)"],
    "赵靓": ["新世纪一部(化妆)"],
    "金艳": ["新世纪二部"],
    "毛红霞": ["新世纪二部"],
    "朱丽华": ["新世纪三部"],
    "孙丽萍": ["新世纪三部"],
    "刘烨丹": ["新世纪四部"],
    "余坚": ["新世纪四部"],
    "姜榆芳": ["新世纪五部(运休)"],
    "李美芳": ["新世纪五部(运休)"],
    "赵佳": ["新世纪六部(男装)"],
    "顾红年": ["新世纪六部(男装)"],
    "范梦茜": ["新世纪八部(儿童)"],
    "刘莉": ["新世纪八部(儿童)"],
    "张文伟": ["新世纪九部(超市)"],
    "蒋雪梅": ["新世纪九部(超市)"],
    "王劲斐": ["新世纪十部(特业)"],
}


@dataclass(frozen=True)
class DepartmentScopeRefreshResult:
    updated: bool
    department_code: str = ""
    department_name: str = ""
    reason: str = ""


@dataclass(frozen=True)
class BusinessDepartment:
    dept_code: str
    dept_name: str


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


def _counter_group_department_rows(db) -> list[BusinessDepartment]:
    rows = (
        db.query(CounterGroup.department_code, CounterGroup.department_name)
        .filter(
            CounterGroup.department_code.isnot(None),
            CounterGroup.department_name.isnot(None),
        )
        .distinct()
        .all()
    )
    return [
        BusinessDepartment(dept_code=row.department_code, dept_name=row.department_name)
        for row in rows
        if normalize_department_name(row.department_code) and normalize_department_name(row.department_name)
    ]


def resolve_business_department(db, department_path: str):
    leaves = department_leaf_names(department_path)
    if not leaves:
        return None

    departments = [*_department_rows(db), *_counter_group_department_rows(db)]
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


def resolve_business_departments_for_scope(db, department_path: str) -> list[Any]:
    primary = resolve_business_department(db, department_path)
    if not primary:
        return []

    departments = [primary]
    seen_codes = {str(getattr(primary, "dept_code", ""))}
    expansion_names = DEPARTMENT_SCOPE_EXPANSIONS.get(normalize_department_name(getattr(primary, "dept_name", "")), [])
    for department_name in expansion_names:
        department = resolve_business_department(db, department_name)
        dept_code = str(getattr(department, "dept_code", "")) if department else ""
        if department and dept_code and dept_code not in seen_codes:
            departments.append(department)
            seen_codes.add(dept_code)
    return departments


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
            or_(
                DataPolicy.external_scope_id == external_scope_id,
                DataPolicy.external_scope_id.is_(None),
                DataPolicy.external_scope_id == "",
            ),
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
    user_id = int(user.user_id)
    departments = resolve_business_departments_for_scope(db, department_path)
    if not departments:
        _delete_auto_scope(db, user_id)
        return DepartmentScopeRefreshResult(updated=False, reason="department_mapping_missing")
    primary_department = departments[0]

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
    for department in departments:
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
        department_code=str(primary_department.dept_code),
        department_name=str(primary_department.dept_name),
    )


def known_department_names_for_user(user) -> list[str]:
    names: list[str] = []
    for value in (
        getattr(user, "real_name", None),
        getattr(user, "username", None),
        getattr(user, "employee_no", None),
    ):
        key = str(value or "").strip()
        if key and key in KNOWN_USER_DEPARTMENTS:
            for department_name in KNOWN_USER_DEPARTMENTS[key]:
                if department_name not in names:
                    names.append(department_name)
    return names


def refresh_auto_department_scope_from_known_assignment(
    db,
    *,
    user,
    wecom_user_id: str,
) -> DepartmentScopeRefreshResult:
    department_names = known_department_names_for_user(user)
    if not department_names:
        return DepartmentScopeRefreshResult(updated=False, reason="known_department_missing")
    if len(department_names) > 1:
        return DepartmentScopeRefreshResult(updated=False, reason="known_department_ambiguous")
    return refresh_auto_department_scope(
        db,
        user=user,
        wecom_user_id=wecom_user_id,
        department_path=department_names[0],
    )
