#!/usr/bin/env python3
"""
Read-only diagnostics for Enterprise WeChat automatic department scopes.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from models.database import SessionLocal
from models.models import Department, User, UserDepartmentPost, UserIdentity
from services.wecom_department_scope import resolve_business_department


def diagnose(limit_failures: int = 80) -> int:
    db = SessionLocal()
    stats = Counter()
    failures: list[str] = []
    try:
        rows = (
            db.query(User, UserIdentity)
            .join(UserIdentity, UserIdentity.user_id == User.user_id)
            .filter(
                UserIdentity.identity_type == "wecom",
                User.is_active == True,
            )
            .order_by(User.real_name.asc().nullslast(), User.username.asc())
            .all()
        )
        stats["wecom_users"] = len(rows)
        for user, identity in rows:
            post = (
                db.query(UserDepartmentPost, Department)
                .join(Department, Department.id == UserDepartmentPost.department_id)
                .filter(
                    UserDepartmentPost.user_id == user.user_id,
                    UserDepartmentPost.is_active == True,
                    Department.is_active == True,
                )
                .order_by(UserDepartmentPost.is_primary.desc(), UserDepartmentPost.id.asc())
                .first()
            )
            if not post:
                stats["missing_synced_department"] += 1
                if len(failures) < limit_failures:
                    failures.append(f"{user.real_name or user.username}({identity.wecom_user_id}): missing_synced_department")
                continue

            _user_department_post, wecom_department = post
            department_path = wecom_department.dept_name or wecom_department.dept_code
            business_department = resolve_business_department(db, department_path)
            if not business_department:
                stats["missing_business_mapping"] += 1
                if len(failures) < limit_failures:
                    failures.append(
                        f"{user.real_name or user.username}({identity.wecom_user_id}): "
                        f"department={department_path} missing_business_mapping"
                    )
                continue

            stats["mapped"] += 1

        print("Enterprise WeChat department scope diagnostic")
        print("mode: READ-ONLY")
        print("stats: " + ", ".join(f"{key}={value}" for key, value in sorted(stats.items())))
        if failures:
            print("sample_failures:")
            for failure in failures:
                print(f"- {failure}")
        return 0
    finally:
        db.close()


def main() -> int:
    return diagnose()


if __name__ == "__main__":
    raise SystemExit(main())
