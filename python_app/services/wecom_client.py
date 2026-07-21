"""
Enterprise WeChat API client helpers.
"""
from __future__ import annotations

import os
import hashlib
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests


WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"
WECOM_QR_CONNECT_URL = "https://open.work.weixin.qq.com/wwopen/sso/qrConnect"
WECOM_MOBILE_OAUTH_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
DEFAULT_TIMEOUT_SECONDS = 8

_token_cache: dict[str, tuple[str, float]] = {}


class WeComConfigError(RuntimeError):
    pass


class WeComApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class WeComConfig:
    enabled: bool
    corp_id: str
    agent_id: str
    app_secret: str
    redirect_base_url: str
    frontend_base_url: str


def get_wecom_config() -> WeComConfig:
    enabled = os.getenv("WECOM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    frontend_base_url = os.getenv("WECOM_FRONTEND_BASE_URL", "").strip()
    redirect_base_url = os.getenv("WECOM_REDIRECT_BASE_URL", "").strip().rstrip("/")
    return WeComConfig(
        enabled=enabled,
        corp_id=os.getenv("WECOM_CORP_ID", "").strip(),
        agent_id=os.getenv("WECOM_AGENT_ID", "").strip(),
        app_secret=os.getenv("WECOM_APP_SECRET", "").strip(),
        redirect_base_url=redirect_base_url,
        frontend_base_url=frontend_base_url.rstrip("/") if frontend_base_url else "",
    )


def require_wecom_config() -> WeComConfig:
    config = get_wecom_config()
    if not config.enabled:
        raise WeComConfigError("企业微信登录未启用")
    missing = [
        name
        for name, value in (
            ("WECOM_CORP_ID", config.corp_id),
            ("WECOM_AGENT_ID", config.agent_id),
            ("WECOM_APP_SECRET", config.app_secret),
            ("WECOM_REDIRECT_BASE_URL", config.redirect_base_url),
        )
        if not value
    ]
    if missing:
        raise WeComConfigError(f"企业微信登录缺少配置: {', '.join(missing)}")
    return config


def build_callback_url(config: WeComConfig) -> str:
    return f"{config.redirect_base_url}/api/auth/wecom/callback"


def build_qr_login_url(config: WeComConfig, *, state: str) -> str:
    query = urlencode(
        {
            "appid": config.corp_id,
            "agentid": config.agent_id,
            "redirect_uri": build_callback_url(config),
            "state": state,
        }
    )
    return f"{WECOM_QR_CONNECT_URL}?{query}"


def build_mobile_login_url(config: WeComConfig, *, state: str) -> str:
    """Build the silent OAuth entry used inside the Enterprise WeChat mobile app."""
    query = urlencode(
        {
            "appid": config.corp_id,
            "redirect_uri": build_callback_url(config),
            "response_type": "code",
            "scope": "snsapi_base",
            "agentid": config.agent_id,
            "state": state,
        }
    )
    return f"{WECOM_MOBILE_OAUTH_URL}?{query}#wechat_redirect"


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WeComApiError(f"企业微信接口请求失败: {exc}") from exc

    payload = response.json()
    errcode = int(payload.get("errcode", 0) or 0)
    if errcode != 0:
        errmsg = payload.get("errmsg") or "unknown error"
        raise WeComApiError(f"企业微信接口返回错误: {errcode} {errmsg}")
    return payload


def get_app_access_token(config: WeComConfig) -> str:
    cache_key = f"app:{config.corp_id}:{config.app_secret}"
    cached = _token_cache.get(cache_key)
    now = time.time()
    if cached and cached[1] > now:
        return cached[0]

    payload = _request_json(
        f"{WECOM_API_BASE}/gettoken",
        {"corpid": config.corp_id, "corpsecret": config.app_secret},
    )
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise WeComApiError("企业微信接口未返回 access_token")

    expires_in = int(payload.get("expires_in", 7200) or 7200)
    _token_cache[cache_key] = (access_token, now + max(expires_in - 300, 60))
    return access_token


def get_jsapi_ticket(config: WeComConfig) -> str:
    cache_key = f"jsapi:{config.corp_id}:{config.agent_id}"
    cached = _token_cache.get(cache_key)
    now = time.time()
    if cached and cached[1] > now:
        return cached[0]

    access_token = get_app_access_token(config)
    payload = _request_json(
        f"{WECOM_API_BASE}/get_jsapi_ticket",
        {"access_token": access_token},
    )
    ticket = str(payload.get("ticket") or "")
    if not ticket:
        raise WeComApiError("企业微信接口未返回 jsapi_ticket")

    expires_in = int(payload.get("expires_in", 7200) or 7200)
    _token_cache[cache_key] = (ticket, now + max(expires_in - 300, 60))
    return ticket


def build_js_sdk_signature(
    ticket: str,
    *,
    nonce_str: str,
    timestamp: int,
    url: str,
) -> str:
    signed_url = url.split("#", 1)[0]
    canonical = (
        f"jsapi_ticket={ticket}&noncestr={nonce_str}"
        f"&timestamp={timestamp}&url={signed_url}"
    )
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def get_userinfo_by_code(config: WeComConfig, code: str) -> dict[str, Any]:
    access_token = get_app_access_token(config)
    return _request_json(
        f"{WECOM_API_BASE}/user/getuserinfo",
        {"access_token": access_token, "code": code},
    )


def get_user_detail(config: WeComConfig, userid: str) -> dict[str, Any]:
    access_token = get_app_access_token(config)
    return _request_json(
        f"{WECOM_API_BASE}/user/get",
        {"access_token": access_token, "userid": userid},
    )


def get_department_paths(config: WeComConfig) -> dict[int, str]:
    access_token = get_app_access_token(config)
    payload = _request_json(f"{WECOM_API_BASE}/department/list", {"access_token": access_token})
    department_names: dict[int, str] = {}
    parent_ids: dict[int, int] = {}
    ids: list[int] = []
    for item in payload.get("department", []):
        if item.get("id") is None:
            continue
        department_id = int(item["id"])
        ids.append(department_id)
        department_names[department_id] = str(item.get("name") or item.get("name_en") or department_id).strip()
        if item.get("parentid") is not None:
            parent_ids[department_id] = int(item.get("parentid") or 0)

    def department_path(department_id: int) -> str:
        path: list[str] = []
        seen: set[int] = set()
        current_id = department_id
        while current_id and current_id not in seen:
            seen.add(current_id)
            name = department_names.get(current_id, "").strip()
            if name:
                path.append(name)
            current_id = parent_ids.get(current_id, 0)
        path.reverse()
        return "/".join(path)

    return {
        department_id: department_path(department_id) or department_names.get(department_id, str(department_id))
        for department_id in ids
    }
