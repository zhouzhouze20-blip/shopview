from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from requests import exceptions as request_exceptions


DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.7"
DEFAULT_MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"


def generate_ai_report(payload: dict[str, Any], instructions: str | None = None) -> dict[str, Any]:
    config = _load_ai_config()
    if not config["api_key"]:
        return {
            "enabled": True,
            "status": "not_configured",
            "report": None,
            "provider": config["provider"],
            "model": config["model"],
            "error": f"未配置 {config['api_key_env']}，已返回规则分析结果。",
        }

    try:
        if config["api_style"] == "responses":
            report = _call_responses_api(payload, config, instructions)
        else:
            report = _call_chat_completions_api(payload, config, instructions)
        return {
            "enabled": True,
            "status": "success" if report else "empty",
            "provider": config["provider"],
            "model": config["model"],
            "report": report,
        }
    except Exception as exc:
        return {
            "enabled": True,
            "status": "failed",
            "provider": config["provider"],
            "model": config["model"],
            "report": None,
            "error": f"AI 服务暂不可用，已返回规则分析结果。{_friendly_error(exc)}",
        }


def _load_ai_config() -> dict[str, Any]:
    provider = _env("SALES_ANALYSIS_AI_PROVIDER", "").lower()
    if provider == "minimax":
        return _minimax_config()
    if provider in {"openai_compatible", "chat_completions"}:
        return _openai_compatible_config(provider)
    if not provider and _env("MINIMAX_API_KEY", "") and not _env("OPENAI_API_KEY", ""):
        return _minimax_config()
    return _openai_config()


def _openai_config() -> dict[str, Any]:
    return {
        "provider": "openai",
        "api_style": _env("SALES_ANALYSIS_AI_API_STYLE", "responses"),
        "base_url": _env("SALES_ANALYSIS_AI_BASE_URL", _env("OPENAI_BASE_URL", "https://api.openai.com/v1")),
        "api_key": _env("SALES_ANALYSIS_AI_API_KEY", _env("OPENAI_API_KEY", "")),
        "api_key_env": "SALES_ANALYSIS_AI_API_KEY 或 OPENAI_API_KEY",
        "model": _env("SALES_ANALYSIS_AI_MODEL", _env("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)),
        "timeout": _env_float("SALES_ANALYSIS_AI_TIMEOUT_SECONDS", _env_float("OPENAI_TIMEOUT_SECONDS", 30.0)),
        "max_output_tokens": _env_int("SALES_ANALYSIS_AI_MAX_OUTPUT_TOKENS", 1200),
    }


def _minimax_config() -> dict[str, Any]:
    return {
        "provider": "minimax",
        "api_style": "chat_completions",
        "base_url": _env("SALES_ANALYSIS_AI_BASE_URL", _env("MINIMAX_BASE_URL", DEFAULT_MINIMAX_BASE_URL)),
        "api_key": _env("SALES_ANALYSIS_AI_API_KEY", _env("MINIMAX_API_KEY", "")),
        "api_key_env": "SALES_ANALYSIS_AI_API_KEY 或 MINIMAX_API_KEY",
        "model": _env("SALES_ANALYSIS_AI_MODEL", _env("MINIMAX_MODEL", DEFAULT_MINIMAX_MODEL)),
        "timeout": _env_float("SALES_ANALYSIS_AI_TIMEOUT_SECONDS", _env_float("MINIMAX_TIMEOUT_SECONDS", 90.0)),
        "max_output_tokens": _env_int("SALES_ANALYSIS_AI_MAX_OUTPUT_TOKENS", 800),
    }


def _openai_compatible_config(provider: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "api_style": "chat_completions",
        "base_url": _env("SALES_ANALYSIS_AI_BASE_URL", ""),
        "api_key": _env("SALES_ANALYSIS_AI_API_KEY", ""),
        "api_key_env": "SALES_ANALYSIS_AI_API_KEY",
        "model": _env("SALES_ANALYSIS_AI_MODEL", ""),
        "timeout": _env_float("SALES_ANALYSIS_AI_TIMEOUT_SECONDS", 30.0),
        "max_output_tokens": _env_int("SALES_ANALYSIS_AI_MAX_OUTPUT_TOKENS", 1200),
    }


def _call_responses_api(payload: dict[str, Any], config: dict[str, Any], instructions: str | None = None) -> str | None:
    body = {
        "model": config["model"],
        "instructions": instructions or _analysis_instructions(),
        "input": json.dumps(payload, ensure_ascii=False),
        "max_output_tokens": config["max_output_tokens"],
    }
    response = requests.post(
        f"{config['base_url'].rstrip('/')}/responses",
        headers=_auth_headers(config),
        json=body,
        timeout=config["timeout"],
    )
    response.raise_for_status()
    return _extract_responses_output_text(response.json())


def _call_chat_completions_api(payload: dict[str, Any], config: dict[str, Any], instructions: str | None = None) -> str | None:
    if not config["base_url"] or not config["model"]:
        raise ValueError("chat_completions 模式需要配置 SALES_ANALYSIS_AI_BASE_URL 和 SALES_ANALYSIS_AI_MODEL")
    body = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": instructions or _analysis_instructions()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "max_tokens": config["max_output_tokens"],
    }
    response = requests.post(
        f"{config['base_url'].rstrip('/')}/chat/completions",
        headers=_auth_headers(config),
        json=body,
        timeout=config["timeout"],
    )
    response.raise_for_status()
    return _extract_chat_completion_text(response.json())


def _analysis_instructions() -> str:
    return (
        "你是百货商场销售经营分析助手。"
        "请基于结构化规则结果生成面向营运人员的销售分析。"
        "不要编造数据，不要推断未提供的原因。"
        "不要输出思考过程、推理过程或 <think> 标签。"
        "输出分为：核心结论、重点异常、可能原因线索、建议动作。"
        "语言简洁，控制在 500 字以内，保留关键金额、比例和柜组名称。"
    )


def _auth_headers(config: dict[str, Any]) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }


def _extract_responses_output_text(data: dict[str, Any]) -> str | None:
    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()
    parts: list[str] = []
    for item in data.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    text = "\n".join(part.strip() for part in parts if part and part.strip())
    return text or None


def _extract_chat_completion_text(data: dict[str, Any]) -> str | None:
    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return _strip_reasoning(content)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        text = "\n".join(part.strip() for part in parts if part and part.strip())
        return _strip_reasoning(text) if text else None
    return None


def _strip_reasoning(text: str) -> str | None:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    return cleaned or None


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, request_exceptions.Timeout):
        return "AI 生成超时，请稍后重试或缩小分析范围。"
    if isinstance(exc, request_exceptions.HTTPError) and exc.response is not None:
        return f"AI 接口返回 {exc.response.status_code}。"
    return "请稍后重试。"


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default
