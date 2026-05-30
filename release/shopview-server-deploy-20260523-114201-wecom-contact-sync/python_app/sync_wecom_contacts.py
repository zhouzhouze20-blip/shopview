#!/usr/bin/env python3
"""
Sync Enterprise WeChat contacts into ShopView users and wecom identities.

Default mode is dry-run. Add --apply to write changes.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

sys.path.append(str(Path(__file__).resolve().parent))

from models.database import SessionLocal
from models.models import User, UserIdentity, UserRole
from routers.auth import DEFAULT_ADMIN_PASSWORD, _hash_password
from routers.system_management import _ensure_contract_viewer_role


WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"
DEFAULT_TIMEOUT_SECONDS = 12


class WeComSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class WeComMember:
    userid: str
    name: str
    mobile: str
    email: str
    status: int
    raw: dict[str, Any]


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WeComSyncError(f"企业微信接口请求失败: {exc}") from exc

    payload = response.json()
    errcode = int(payload.get("errcode", 0) or 0)
    if errcode != 0:
        errmsg = payload.get("errmsg") or "unknown error"
        raise WeComSyncError(f"企业微信接口返回错误: {errcode} {errmsg}")
    return payload


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def get_access_token(corp_id: str, secret: str) -> str:
    payload = _request_json(
        f"{WECOM_API_BASE}/gettoken",
        {"corpid": corp_id, "corpsecret": secret},
    )
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise WeComSyncError("企业微信接口未返回 access_token")
    return access_token


def list_department_ids(access_token: str) -> list[int]:
    payload = _request_json(f"{WECOM_API_BASE}/department/list", {"access_token": access_token})
    ids = [int(item["id"]) for item in payload.get("department", []) if item.get("id") is not None]
    return ids or [1]


def list_members(access_token: str, department_ids: list[int]) -> list[WeComMember]:
    members_by_userid: dict[str, WeComMember] = {}
    for department_id in department_ids:
        payload = _request_json(
            f"{WECOM_API_BASE}/user/list",
            {
                "access_token": access_token,
                "department_id": department_id,
                "fetch_child": 0,
            },
        )
        for row in payload.get("userlist", []):
            userid = str(row.get("userid") or "").strip()
            if not userid:
                continue
            members_by_userid[userid] = WeComMember(
                userid=userid,
                name=str(row.get("name") or "").strip(),
                mobile=str(row.get("mobile") or "").strip(),
                email=str(row.get("email") or "").strip(),
                status=int(row.get("status", 1) or 1),
                raw=row,
            )
    return sorted(members_by_userid.values(), key=lambda item: item.userid)


def _is_active_status(status: int) -> bool:
    return status == 1


def _find_user_for_member(db, member: WeComMember) -> User | None:
    user = db.query(User).filter(User.username == member.userid).first()
    if user:
        return user
    return db.query(User).filter(User.employee_no == member.userid).first()


def _upsert_user(db, member: WeComMember, default_password: str) -> tuple[User, bool]:
    user = _find_user_for_member(db, member)
    active = _is_active_status(member.status)
    if user:
        user.real_name = member.name or user.real_name
        user.phone = member.mobile or user.phone
        user.email = member.email or user.email
        user.employee_no = member.userid
        user.status = "ACTIVE" if active else "DISABLED"
        user.is_active = active
        user.updated_at = datetime.now()
        return user, False

    user = User(
        username=member.userid,
        password_hash=_hash_password(default_password),
        real_name=member.name or member.userid,
        phone=member.mobile or None,
        email=member.email or None,
        employee_no=member.userid,
        role="user",
        status="ACTIVE" if active else "DISABLED",
        is_active=active,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(user)
    db.flush()
    return user, True


def _upsert_wecom_identity(db, user: User, corp_id: str, member: WeComMember) -> bool:
    identity = (
        db.query(UserIdentity)
        .filter(
            UserIdentity.identity_type == "wecom",
            UserIdentity.corp_id == corp_id,
            UserIdentity.wecom_user_id == member.userid,
        )
        .first()
    )
    created = False
    if not identity:
        identity = UserIdentity(
            user_id=user.user_id,
            identity_type="wecom",
            identifier=f"{corp_id}:{member.userid}",
            corp_id=corp_id,
            wecom_user_id=member.userid,
            is_primary=False,
            created_at=datetime.now(),
        )
        db.add(identity)
        created = True

    identity.user_id = user.user_id
    identity.identifier = f"{corp_id}:{member.userid}"
    identity.updated_at = datetime.now()
    return created


def _ensure_viewer_role(db, user_id: int) -> bool:
    role = _ensure_contract_viewer_role(db)
    exists = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role.id).first()
    if exists:
        return False
    db.add(UserRole(user_id=user_id, role_id=role.id, created_at=datetime.now()))
    return True


def sync_wecom_contacts(
    *,
    apply: bool,
    reset_wecom_identities: bool,
    disable_missing_wecom_users: bool,
    grant_viewer_role: bool,
    default_password: str,
) -> int:
    corp_id = _get_env("WECOM_CORP_ID")
    secret = _get_env("WECOM_CONTACT_SECRET") or _get_env("WECOM_APP_SECRET")
    if not corp_id:
        raise WeComSyncError("缺少 WECOM_CORP_ID")
    if not secret:
        raise WeComSyncError("缺少 WECOM_CONTACT_SECRET 或 WECOM_APP_SECRET")

    access_token = get_access_token(corp_id, secret)
    department_ids = list_department_ids(access_token)
    members = list_members(access_token, department_ids)
    active_userids = {member.userid for member in members if _is_active_status(member.status)}

    db = SessionLocal()
    stats = Counter()
    try:
        stats["departments_seen"] = len(department_ids)
        stats["members_seen"] = len(members)
        stats["members_active"] = len(active_userids)

        if apply and reset_wecom_identities:
            deleted = db.query(UserIdentity).filter(UserIdentity.identity_type == "wecom").delete(synchronize_session=False)
            stats["wecom_identities_deleted"] = deleted

        for member in members:
            if not _is_active_status(member.status):
                stats["members_inactive"] += 1

            if not apply:
                user = _find_user_for_member(db, member)
                stats["users_matched" if user else "users_would_create"] += 1
                continue

            user, created = _upsert_user(db, member, default_password)
            stats["users_created" if created else "users_updated"] += 1
            if _upsert_wecom_identity(db, user, corp_id, member):
                stats["wecom_identities_created"] += 1
            else:
                stats["wecom_identities_updated"] += 1
            if grant_viewer_role and _ensure_viewer_role(db, user.user_id):
                stats["viewer_roles_added"] += 1

        if apply and disable_missing_wecom_users:
            identities = (
                db.query(UserIdentity)
                .filter(UserIdentity.identity_type == "wecom", UserIdentity.corp_id == corp_id)
                .all()
            )
            for identity in identities:
                if identity.wecom_user_id in active_userids:
                    continue
                user = db.query(User).filter(User.user_id == identity.user_id).first()
                if user and user.username != "admin":
                    user.status = "DISABLED"
                    user.is_active = False
                    user.updated_at = datetime.now()
                    stats["users_disabled_missing_wecom"] += 1

        if apply:
            db.commit()
        else:
            db.rollback()

        print("Enterprise WeChat contacts sync summary")
        print(f"mode: {'APPLY' if apply else 'DRY-RUN'}")
        print(f"corp_id: {corp_id}")
        print(f"reset_wecom_identities: {reset_wecom_identities}")
        print(f"disable_missing_wecom_users: {disable_missing_wecom_users}")
        print(f"grant_viewer_role: {grant_viewer_role}")
        print("stats: " + (", ".join(f"{key}={value}" for key, value in sorted(stats.items())) or "none"))
        if not apply:
            print("dry-run only; add --apply to write changes")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Enterprise WeChat contacts into ShopView users.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Omit for dry-run.")
    parser.add_argument("--reset-wecom-identities", action="store_true", help="Delete existing wecom identities before syncing.")
    parser.add_argument("--disable-missing-wecom-users", action="store_true", help="Disable users bound to wecom ids no longer active.")
    parser.add_argument("--grant-viewer-role", action="store_true", help="Grant the contract viewer role to synced users.")
    parser.add_argument("--default-password", default=DEFAULT_ADMIN_PASSWORD, help="Initial password for newly-created users.")
    args = parser.parse_args()

    try:
        return sync_wecom_contacts(
            apply=args.apply,
            reset_wecom_identities=args.reset_wecom_identities,
            disable_missing_wecom_users=args.disable_missing_wecom_users,
            grant_viewer_role=args.grant_viewer_role,
            default_password=args.default_password,
        )
    except WeComSyncError as exc:
        print(f"同步失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
