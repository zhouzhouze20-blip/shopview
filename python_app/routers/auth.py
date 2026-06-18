"""
认证 API
"""
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy import or_
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from models.database import SessionLocal, get_db
from models.models import LoginLog, Permission, Role, RolePermission, User, UserIdentity, UserRole
from schemas.schemas import AuthUserSchema, LoginRequest, LoginResponse
from services.wecom_client import (
    WeComApiError,
    WeComConfigError,
    build_qr_login_url,
    get_userinfo_by_code,
    require_wecom_config,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "shopview-dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("AUTH_TOKEN_EXPIRE_HOURS", "12"))
AUTH_COOKIE_NAME = "shopview_auth_token"
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "123456")
PASSWORD_ITERATIONS = 390000
WECOM_STATE_EXPIRE_MINUTES = 10
WECOM_LOGIN_RESULT_DIR = Path(os.getenv("WECOM_LOGIN_RESULT_DIR", "/tmp/shopview-wecom-login"))
ADMIN_ROLE_CODES = {"super_admin", "system_admin"}


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else None


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(digest).decode("utf-8"),
    )


def _verify_password(plain_password: str, password_hash: str) -> bool:
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
            salt = base64.b64decode(salt_b64.encode("utf-8"))
            expected = base64.b64decode(digest_b64.encode("utf-8"))
            calculated = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, int(iterations))
            return hmac.compare_digest(calculated, expected)
        except Exception:
            return False
    return False


def _create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_access_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        return int(subject) if subject is not None else None
    except (JWTError, ValueError):
        return None


def _safe_next_path(value: str | None) -> str:
    if not value:
        return "/"
    value = value.strip()
    if not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


def _create_wecom_state(next_path: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=WECOM_STATE_EXPIRE_MINUTES)
    payload = {"typ": "wecom_login", "next": _safe_next_path(next_path), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_wecom_state(state_token: str) -> dict:
    try:
        payload = jwt.decode(state_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="企业微信登录状态已失效")
    if payload.get("typ") != "wecom_login":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="企业微信登录状态无效")
    return payload


def _cleanup_wecom_login_results() -> None:
    if not WECOM_LOGIN_RESULT_DIR.exists():
        return
    now = datetime.utcnow()
    for result_file in WECOM_LOGIN_RESULT_DIR.glob("*.json"):
        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
            expires_at = datetime.fromisoformat(payload["expires_at"])
        except Exception:
            result_file.unlink(missing_ok=True)
            continue
        if expires_at <= now:
            result_file.unlink(missing_ok=True)


def _wecom_login_result_path(state_token: str) -> Path:
    state_hash = hashlib.sha256(state_token.encode("utf-8")).hexdigest()
    return WECOM_LOGIN_RESULT_DIR / f"{state_hash}.json"


def _store_wecom_login_success(state_token: str, user_id: int, token: str) -> None:
    _cleanup_wecom_login_results()
    WECOM_LOGIN_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    result_path = _wecom_login_result_path(state_token)
    payload = {
        "status": "success",
        "user_id": user_id,
        "token": token,
        "expires_at": (datetime.utcnow() + timedelta(minutes=WECOM_STATE_EXPIRE_MINUTES)).isoformat(),
    }
    temp_path = result_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(result_path)


def _pop_wecom_login_result(state_token: str) -> dict | None:
    _cleanup_wecom_login_results()
    result_path = _wecom_login_result_path(state_token)
    if not result_path.exists():
        return None
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    finally:
        result_path.unlink(missing_ok=True)


def _frontend_redirect_url(path: str = "/", **params: str) -> str:
    frontend_base_url = os.getenv("WECOM_FRONTEND_BASE_URL", "").strip().rstrip("/")
    target_path = _safe_next_path(path)
    query = urlencode({key: value for key, value in params.items() if value})
    suffix = f"{target_path}{'&' if '?' in target_path and query else '?' if query else ''}{query}"
    if frontend_base_url:
        return f"{frontend_base_url}{suffix}"
    return suffix


def _set_auth_cookie(response: Response, token: str) -> None:
    secure_cookie = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


def _find_wecom_user(db: Session, corp_id: str, wecom_user_id: str) -> tuple[UserIdentity | None, User | None]:
    identity = (
        db.query(UserIdentity)
        .filter(
            UserIdentity.identity_type == "wecom",
            UserIdentity.corp_id == corp_id,
            UserIdentity.wecom_user_id == wecom_user_id,
        )
        .first()
    )
    if not identity:
        identifier_values = [f"{corp_id}:{wecom_user_id}", wecom_user_id]
        identity = (
            db.query(UserIdentity)
            .filter(
                UserIdentity.identity_type == "wecom",
                UserIdentity.identifier.in_(identifier_values),
            )
            .first()
        )

    if not identity:
        return None, None
    user = db.query(User).filter(User.user_id == identity.user_id).first()
    return identity, user


def _serialize_auth_user(db: Session, user: User) -> dict:
    role_rows = (
        db.query(Role.role_code, Role.role_name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(
            UserRole.user_id == user.user_id,
            Role.is_active == True,
            or_(UserRole.expires_at.is_(None), UserRole.expires_at > func.now()),
        )
        .all()
    )
    role_codes = [row.role_code for row in role_rows]
    if {"super_admin", "system_admin"} & set(role_codes):
        permission_rows = db.query(Permission.permission_code).all()
    else:
        permission_rows = (
            db.query(Permission.permission_code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .join(Role, Role.id == UserRole.role_id)
            .filter(
                UserRole.user_id == user.user_id,
                Role.is_active == True,
                or_(UserRole.expires_at.is_(None), UserRole.expires_at > func.now()),
            )
            .distinct()
            .all()
        )

    return {
        "user_id": user.user_id,
        "username": user.username,
        "real_name": user.real_name,
        "employee_no": getattr(user, "employee_no", None),
        "status": getattr(user, "status", "ACTIVE") or "ACTIVE",
        "is_active": user.is_active,
        "role_codes": role_codes,
        "role_names": [row.role_name for row in role_rows],
        "permission_codes": sorted(row.permission_code for row in permission_rows),
    }


def _is_admin_user(db: Session, user: User) -> bool:
    role_codes = {
        row.role_code
        for row in (
            db.query(Role.role_code)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(
                UserRole.user_id == user.user_id,
                Role.is_active == True,
                or_(UserRole.expires_at.is_(None), UserRole.expires_at > func.now()),
            )
            .all()
        )
    }
    return bool(role_codes & ADMIN_ROLE_CODES)


def ensure_default_admin() -> None:
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            return

        admin_user = User(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
            real_name="系统管理员",
            role="admin",
            status="ACTIVE",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(admin_user)
        db.flush()

        db.add(UserIdentity(
            user_id=admin_user.user_id,
            identity_type="password",
            identifier=DEFAULT_ADMIN_USERNAME,
            credential_hash=admin_user.password_hash,
            is_primary=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ))

        super_admin_role = db.query(Role).filter(Role.role_code == "super_admin").first()
        if super_admin_role:
            db.add(UserRole(
                user_id=admin_user.user_id,
                role_id=super_admin_role.id,
                created_at=datetime.now(),
            ))

        db.commit()
        print(f"已创建默认管理员账号: {DEFAULT_ADMIN_USERNAME}")
    except ProgrammingError:
        db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def reset_all_passwords(password: str = DEFAULT_ADMIN_PASSWORD) -> None:
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            password_hash = _hash_password(password)
            user.password_hash = password_hash
            user.updated_at = datetime.now()

            password_identities = (
                db.query(UserIdentity)
                .filter(
                    UserIdentity.user_id == user.user_id,
                    UserIdentity.identity_type == "password",
                )
                .all()
            )
            if password_identities:
                for identity in password_identities:
                    identity.credential_hash = password_hash
                    identity.updated_at = datetime.now()
            else:
                db.add(UserIdentity(
                    user_id=user.user_id,
                    identity_type="password",
                    identifier=user.username,
                    credential_hash=password_hash,
                    is_primary=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                ))

        db.commit()
        if users:
            print(f"已重置 {len(users)} 个后台账号密码")
    except ProgrammingError:
        db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(
    request: Request,
    auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    user_id = _decode_access_token(auth_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")

    admin_view_user_id = (request.headers.get("x-shopview-admin-view-user-id") or "").strip()
    if admin_view_user_id and _is_admin_user(db, user):
        try:
            target_user_id = int(admin_view_user_id)
        except ValueError:
            target_user_id = 0
        if target_user_id and target_user_id != user.user_id:
            target = (
                db.query(User)
                .filter(
                    User.user_id == target_user_id,
                    User.is_active == True,
                    or_(User.status.is_(None), User.status.notin_(["DISABLED", "LOCKED"])),
                )
                .first()
            )
            if target:
                setattr(user, "admin_view_user_id", target.user_id)
    return user


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not _verify_password(payload.password, user.password_hash):
        db.add(LoginLog(
            user_id=user.user_id if user else None,
            identity_type="password",
            identifier=payload.username,
            login_result="FAILED",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            created_at=datetime.now(),
        ))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    if not user.is_active or getattr(user, "status", "ACTIVE") in {"DISABLED", "LOCKED"}:
        db.add(LoginLog(
            user_id=user.user_id,
            identity_type="password",
            identifier=payload.username,
            login_result="FAILED",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            created_at=datetime.now(),
        ))
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用或锁定")

    token = _create_access_token(user.user_id)
    _set_auth_cookie(response, token)
    user.last_login = datetime.now()
    db.add(LoginLog(
        user_id=user.user_id,
        identity_type="password",
        identifier=payload.username,
        login_result="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(),
    ))
    db.commit()
    db.refresh(user)
    return {"message": "登录成功", "user": _serialize_auth_user(db, user)}


@router.get("/wecom/login-url")
async def get_wecom_login_url(next: str = Query("/", alias="next")):
    try:
        config = require_wecom_config()
    except WeComConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    state_token = _create_wecom_state(next)
    return {
        "login_url": build_qr_login_url(config, state=state_token),
        "state": state_token,
    }


@router.get("/wecom/status")
async def get_wecom_login_status(
    response: Response,
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    try:
        _decode_wecom_state(state)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="企业微信登录状态已失效")

    result = _pop_wecom_login_result(state)
    if not result:
        return {"status": "pending"}

    if result.get("status") != "success":
        return {"status": result.get("status", "failed"), "error": result.get("error", "企业微信登录失败")}

    user = db.query(User).filter(User.user_id == result.get("user_id")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")

    _set_auth_cookie(response, result["token"])
    return {"status": "success", "user": _serialize_auth_user(db, user)}


@router.get("/wecom/callback")
async def wecom_callback(
    request: Request,
    response: Response,
    code: str | None = Query(None),
    state: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if not code or not state:
        return RedirectResponse(_frontend_redirect_url("/", auth_error="wecom_missing_code"))

    try:
        state_payload = _decode_wecom_state(state)
        config = require_wecom_config()
        userinfo = get_userinfo_by_code(config, code)
    except HTTPException:
        return RedirectResponse(_frontend_redirect_url("/", auth_error="wecom_state_invalid"))
    except (WeComConfigError, WeComApiError) as exc:
        detail = str(exc)
        print(f"企业微信登录接口调用失败: {detail}")
        return RedirectResponse(_frontend_redirect_url("/", auth_error="wecom_api_failed", wecom_detail=detail))

    wecom_user_id = str(userinfo.get("UserId") or userinfo.get("userid") or "").strip()
    if not wecom_user_id:
        return RedirectResponse(_frontend_redirect_url("/", auth_error="wecom_no_userid"))

    identity, user = _find_wecom_user(db, config.corp_id, wecom_user_id)
    if not identity or not user:
        db.add(LoginLog(
            user_id=None,
            identity_type="wecom",
            identifier=f"{config.corp_id}:{wecom_user_id}",
            login_result="FAILED",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            created_at=datetime.now(),
        ))
        db.commit()
        return RedirectResponse(_frontend_redirect_url("/", auth_error="wecom_unbound"))

    if not user.is_active or getattr(user, "status", "ACTIVE") in {"DISABLED", "LOCKED"}:
        db.add(LoginLog(
            user_id=user.user_id,
            identity_type="wecom",
            identifier=f"{config.corp_id}:{wecom_user_id}",
            login_result="FAILED",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            created_at=datetime.now(),
        ))
        db.commit()
        return RedirectResponse(_frontend_redirect_url("/", auth_error="wecom_disabled"))

    token = _create_access_token(user.user_id)
    _store_wecom_login_success(state, user.user_id, token)
    redirect = RedirectResponse(_frontend_redirect_url(state_payload.get("next") or "/"))
    _set_auth_cookie(redirect, token)
    user.last_login = datetime.now()
    identity.last_used_at = datetime.now()
    db.add(LoginLog(
        user_id=user.user_id,
        identity_type="wecom",
        identifier=f"{config.corp_id}:{wecom_user_id}",
        login_result="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        created_at=datetime.now(),
    ))
    db.commit()
    return redirect


@router.get("/me", response_model=AuthUserSchema)
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _serialize_auth_user(db, current_user)


@router.get("/admin-view/users", response_model=list[AuthUserSchema])
async def get_admin_view_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _is_admin_user(db, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可使用代看模式")

    users = (
        db.query(User)
        .filter(
            User.is_active == True,
            or_(User.status.is_(None), User.status.notin_(["DISABLED", "LOCKED"])),
        )
        .order_by(User.real_name.asc().nullslast(), User.username.asc())
        .all()
    )
    return [_serialize_auth_user(db, user) for user in users]


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE_NAME)
    return {"message": "已退出登录"}
