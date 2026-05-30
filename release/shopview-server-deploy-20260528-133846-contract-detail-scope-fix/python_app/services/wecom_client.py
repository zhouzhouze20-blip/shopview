"""
Enterprise WeChat API client helpers.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests


WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"
WECOM_QR_CONNECT_URL = "https://open.work.weixin.qq.com/wwopen/sso/qrConnect"
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


def get_userinfo_by_code(config: WeComConfig, code: str) -> dict[str, Any]:
    access_token = get_app_access_token(config)
    return _request_json(
        f"{WECOM_API_BASE}/user/getuserinfo",
        {"access_token": access_token, "code": code},
    )
