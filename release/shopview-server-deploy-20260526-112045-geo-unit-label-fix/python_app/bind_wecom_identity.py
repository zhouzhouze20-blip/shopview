#!/usr/bin/env python3
"""
Bind an existing ShopView user to an Enterprise WeChat userid.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from models.database import SessionLocal
from models.models import User, UserIdentity


def bind_wecom_identity(username: str, wecom_user_id: str, corp_id: str) -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"用户不存在: {username}", file=sys.stderr)
            return 1

        identity = (
            db.query(UserIdentity)
            .filter(
                UserIdentity.identity_type == "wecom",
                UserIdentity.corp_id == corp_id,
                UserIdentity.wecom_user_id == wecom_user_id,
            )
            .first()
        )
        if identity and identity.user_id != user.user_id:
            print(
                f"企业微信 userid 已绑定其他用户: user_id={identity.user_id}",
                file=sys.stderr,
            )
            return 1

        now = datetime.now()
        if identity:
            identity.user_id = user.user_id
            identity.identifier = f"{corp_id}:{wecom_user_id}"
            identity.updated_at = now
            action = "updated"
        else:
            db.add(
                UserIdentity(
                    user_id=user.user_id,
                    identity_type="wecom",
                    identifier=f"{corp_id}:{wecom_user_id}",
                    corp_id=corp_id,
                    wecom_user_id=wecom_user_id,
                    is_primary=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            action = "created"

        db.commit()
        print(f"{action}: username={username}, user_id={user.user_id}, wecom_user_id={wecom_user_id}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"绑定失败: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind ShopView user to Enterprise WeChat userid.")
    parser.add_argument("--username", required=True, help="ShopView username")
    parser.add_argument("--wecom-user-id", required=True, help="Enterprise WeChat userid")
    parser.add_argument("--corp-id", default=os.getenv("WECOM_CORP_ID", ""), help="Enterprise WeChat CorpID")
    args = parser.parse_args()

    corp_id = args.corp_id.strip()
    if not corp_id:
        print("缺少 corp_id，请传 --corp-id 或设置 WECOM_CORP_ID", file=sys.stderr)
        return 1
    return bind_wecom_identity(args.username.strip(), args.wecom_user_id.strip(), corp_id)


if __name__ == "__main__":
    raise SystemExit(main())
