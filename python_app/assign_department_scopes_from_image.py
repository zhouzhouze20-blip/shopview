#!/usr/bin/env python3
"""
Assign business data scopes from the department/user list provided by the user.

Default mode is dry-run. Add --apply to write changes.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from models.database import SessionLocal
from models.models import DataPolicy, DataPolicyItem, Role, User, UserRole


BUSINESS_SCOPE_RESOURCE = "business_scope"
BUSINESS_SCOPE_ACTION = "view"
SOURCE_TYPE = "WECOM"
SOURCE_SYSTEM = "wecom"
EXTERNAL_SCOPE_PREFIX = "manual-image-department"
DEPARTMENT_MANAGER_ROLE_CODE = "dept_manager"


DEPARTMENT_USERS: dict[str, list[str]] = {
    # 购物中心
    "中心B部(超市)": ["黄莉倩", "丁娅", "何蕾"],
    "中心B部(生鲜)": ["高敏"],
    "中心一部(化妆)": ["陈晓楠", "薛涌", "花玲"],
    "中心一部(名品)": ["黄欣怡"],
    "中心二部(女装)": ["于云", "凡水晶", "潘婷"],
    "中心三部(女装)": ["隆晓蓉", "孙琴莹", "陈蓉", "王科涵"],
    "中心四部(男装)": ["蒋佳卫"],
    "中心五部(运动)": ["谈菲"],
    "中心六部(儿童)": ["谈菲", "吴炯萱", "吴彪"],
    "中心七部(家居)": ["贺丽", "宋军"],
    "中心市场部--营运": ["蒋昊", "程益"],
    "中心市场部--客服": ["徐丹妮"],
    "中心市场部--企划": ["俞陈", "丁丽娜"],
    # 大楼
    "营运一部": ["丁岚"],
    "营运二部": ["刘露露"],
    "营运三部": ["王南"],
    "大楼营运": ["屠云"],
    # 新世纪
    "新世纪一部(化妆)": ["周霞", "赵靓"],
    "新世纪二部": ["金艳", "毛红霞"],
    "新世纪三部": ["朱丽华", "孙丽萍"],
    "新世纪四部": ["刘烨丹", "余坚"],
    "新世纪五部(运休)": ["姜榆芳", "李美芳"],
    "新世纪六部(男装)": ["赵佳", "顾红年"],
    "新世纪八部(儿童)": ["范梦茜", "刘莉"],
    "新世纪九部(超市)": ["张文伟", "蒋雪梅"],
    "新世纪十部(特业)": ["王劲斐"],
}


def _build_user_departments() -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for department, names in DEPARTMENT_USERS.items():
        for name in names:
            clean_name = name.strip()
            if clean_name and department not in result[clean_name]:
                result[clean_name].append(department)
    return dict(result)


def _find_user(db, name: str) -> User | None:
    return (
        db.query(User)
        .filter(User.real_name == name)
        .order_by(User.is_active.desc(), User.user_id.asc())
        .first()
    ) or (
        db.query(User)
        .filter(User.username == name)
        .order_by(User.is_active.desc(), User.user_id.asc())
        .first()
    )


def _ensure_department_manager_role(db) -> Role:
    role = db.query(Role).filter(Role.role_code == DEPARTMENT_MANAGER_ROLE_CODE).first()
    if role:
        role.role_name = "部门经理"
        role.is_active = True
        return role
    role = Role(
        role_code=DEPARTMENT_MANAGER_ROLE_CODE,
        role_name="部门经理",
        role_level=700,
        is_system=True,
        is_active=True,
    )
    db.add(role)
    db.flush()
    return role


def _replace_user_scope(db, user: User, departments: list[str]) -> int:
    existing_policy_ids = [
        row[0]
        for row in db.query(DataPolicy.id)
        .filter(
            DataPolicy.subject_type == "USER",
            DataPolicy.subject_id == user.user_id,
            DataPolicy.resource_code == BUSINESS_SCOPE_RESOURCE,
            DataPolicy.action_code == BUSINESS_SCOPE_ACTION,
            DataPolicy.source_type == SOURCE_TYPE,
            DataPolicy.source_system == SOURCE_SYSTEM,
        )
        .all()
    ]
    if existing_policy_ids:
        db.query(DataPolicyItem).filter(DataPolicyItem.policy_id.in_(existing_policy_ids)).delete(synchronize_session=False)
        db.query(DataPolicy).filter(DataPolicy.id.in_(existing_policy_ids)).delete(synchronize_session=False)

    now = datetime.now()
    policy = DataPolicy(
        subject_type="USER",
        subject_id=user.user_id,
        resource_code=BUSINESS_SCOPE_RESOURCE,
        action_code=BUSINESS_SCOPE_ACTION,
        scope_mode="CUSTOM",
        effect="ALLOW",
        priority=50,
        is_active=True,
        source_type=SOURCE_TYPE,
        source_system=SOURCE_SYSTEM,
        external_scope_id=f"{EXTERNAL_SCOPE_PREFIX}:{user.user_id}",
        external_scope_name=f"{user.real_name or user.username} 图片部门数据范围",
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
                dimension_value=department,
                include_children=False,
                created_at=now,
            )
        )
    return len(existing_policy_ids)


def _ensure_user_role(db, user: User, role: Role) -> bool:
    exists = db.query(UserRole).filter(UserRole.user_id == user.user_id, UserRole.role_id == role.id).first()
    if exists:
        return False
    db.add(UserRole(user_id=user.user_id, role_id=role.id, created_at=datetime.now()))
    return True


def assign_department_scopes(*, apply: bool) -> int:
    user_departments = _build_user_departments()
    db = SessionLocal()
    try:
        role = _ensure_department_manager_role(db)
        matched = 0
        missing: list[str] = []
        role_added = 0
        scopes_replaced = 0

        for name, departments in user_departments.items():
            user = _find_user(db, name)
            if not user:
                missing.append(name)
                print(f"未找到用户: {name} -> {', '.join(departments)}")
                continue
            matched += 1
            print(f"匹配用户: {name} user_id={user.user_id} -> {', '.join(departments)}")
            if not apply:
                continue
            scopes_replaced += _replace_user_scope(db, user, departments)
            if _ensure_user_role(db, user, role):
                role_added += 1

        if apply:
            db.commit()
        else:
            db.rollback()

        print("图片部门数据范围分配汇总")
        print(f"mode: {'APPLY' if apply else 'DRY-RUN'}")
        print(f"matched_users: {matched}")
        print(f"missing_users: {len(missing)}")
        print(f"existing_scopes_replaced: {scopes_replaced}")
        print(f"dept_manager_roles_added: {role_added}")
        if missing:
            print("missing_user_names: " + "、".join(missing))
        if not apply:
            print("dry-run only; add --apply to write changes")
        return 0 if not missing else 2
    except Exception as exc:
        db.rollback()
        print(f"分配失败: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Assign department business scopes from the provided image list.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Omit for dry-run.")
    args = parser.parse_args()
    return assign_department_scopes(apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
