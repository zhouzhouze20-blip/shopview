#!/usr/bin/env python3
"""Safely rebind one existing ShopView user to a corrected WeCom UserID.

The command is dry-run by default. Pass ``--apply`` to commit the identity
change. It intentionally does not modify users, roles, department assignments,
or data policies.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

script_directory = Path(__file__).resolve().parent
for import_directory in (script_directory, Path("/app/python_app")):
    if import_directory.exists() and str(import_directory) not in sys.path:
        sys.path.append(str(import_directory))

from models.database import SessionLocal
from models.models import User, UserIdentity


class RebindError(RuntimeError):
    pass


@dataclass(frozen=True)
class RebindResult:
    user_id: int
    username: str
    old_wecom_user_id: str
    new_wecom_user_id: str
    changed: bool
    already_bound: bool = False


def rebind_wecom_identity(
    db,
    *,
    username: str,
    corp_id: str,
    old_wecom_user_id: str,
    new_wecom_user_id: str,
    apply: bool,
) -> RebindResult:
    users = db.query(User).filter(User.username == username).all()
    if len(users) != 1:
        raise RebindError(f"用户 {username} 匹配数必须为 1，实际为 {len(users)}")
    user = users[0]

    target_identity = (
        db.query(UserIdentity)
        .filter(
            UserIdentity.identity_type == "wecom",
            UserIdentity.corp_id == corp_id,
            UserIdentity.wecom_user_id == new_wecom_user_id,
        )
        .first()
    )
    if target_identity:
        if target_identity.user_id == user.user_id:
            return RebindResult(
                user_id=user.user_id,
                username=user.username,
                old_wecom_user_id=old_wecom_user_id,
                new_wecom_user_id=new_wecom_user_id,
                changed=False,
                already_bound=True,
            )
        raise RebindError(
            f"企微 UserID {new_wecom_user_id} 已绑定其他 ShopView 用户，拒绝修改"
        )

    target_identifier = f"{corp_id}:{new_wecom_user_id}"
    identifier_conflict = (
        db.query(UserIdentity)
        .filter(
            UserIdentity.identity_type == "wecom",
            UserIdentity.identifier == target_identifier,
        )
        .first()
    )
    if identifier_conflict:
        raise RebindError(f"登录标识 {target_identifier} 已存在，拒绝修改")

    old_identities = (
        db.query(UserIdentity)
        .filter(
            UserIdentity.user_id == user.user_id,
            UserIdentity.identity_type == "wecom",
            UserIdentity.corp_id == corp_id,
            UserIdentity.wecom_user_id == old_wecom_user_id,
        )
        .all()
    )
    if len(old_identities) != 1:
        raise RebindError(
            f"用户 {username} 的旧企微身份匹配数必须为 1，实际为 {len(old_identities)}"
        )

    identity = old_identities[0]
    if apply:
        identity.wecom_user_id = new_wecom_user_id
        identity.identifier = target_identifier
        identity.updated_at = datetime.now()
        db.commit()
    else:
        db.rollback()

    return RebindResult(
        user_id=user.user_id,
        username=user.username,
        old_wecom_user_id=old_wecom_user_id,
        new_wecom_user_id=new_wecom_user_id,
        changed=apply,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebind one ShopView user to a corrected WeCom UserID.")
    parser.add_argument("--username", required=True, help="Existing ShopView username.")
    parser.add_argument("--old-wecom-userid", required=True, help="Currently bound WeCom UserID.")
    parser.add_argument("--new-wecom-userid", required=True, help="Correct WeCom UserID.")
    parser.add_argument("--apply", action="store_true", help="Commit the change. Omit for dry-run.")
    args = parser.parse_args()

    corp_id = os.getenv("WECOM_CORP_ID", "").strip()
    if not corp_id:
        print("改绑失败: 缺少 WECOM_CORP_ID", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        result = rebind_wecom_identity(
            db,
            username=args.username.strip(),
            corp_id=corp_id,
            old_wecom_user_id=args.old_wecom_userid.strip(),
            new_wecom_user_id=args.new_wecom_userid.strip(),
            apply=args.apply,
        )
        print("ShopView 企微身份改绑检查")
        print(f"mode: {'APPLY' if args.apply else 'DRY-RUN'}")
        print(f"user_id: {result.user_id}")
        print(f"username: {result.username}")
        print(f"old_wecom_user_id: {result.old_wecom_user_id}")
        print(f"new_wecom_user_id: {result.new_wecom_user_id}")
        if result.already_bound:
            print("result: already_bound")
        elif result.changed:
            print("result: rebound")
        else:
            print("result: ready; dry-run only, add --apply to write changes")
        print("roles/data_policies/user_department_posts: unchanged")
        return 0
    except RebindError as exc:
        db.rollback()
        print(f"改绑失败: {exc}", file=sys.stderr)
        return 1
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
