"""从用户设置中解析剧本生成所需的模型列表与提示词/风格文案。"""

from __future__ import annotations

import json
from typing import Any

from app.models.user import User
from app.services.field_encryption import try_decrypt

# 与历史前端默认保持一致，便于未配置时使用
DEFAULT_MODEL_OPTIONS: list[dict[str, str]] = [
    {"value": "gemini-1.5-pro", "label": "Gemini 1.5 Pro（环境默认）"},
    {"value": "claude-3-5-sonnet", "label": "Claude 3.5 Sonnet（环境默认）"},
]


def parse_models_from_user_json(raw: str | None) -> list[dict[str, str]]:
    """解析用户保存的模型 JSON，返回 {value,label} 列表。"""
    if not raw or not str(raw).strip():
        return list(DEFAULT_MODEL_OPTIONS)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return list(DEFAULT_MODEL_OPTIONS)
    if not isinstance(data, list):
        return list(DEFAULT_MODEL_OPTIONS)
    out: list[dict[str, str]] = []
    for item in data:
        if isinstance(item, str) and item.strip():
            out.append({"value": item.strip(), "label": item.strip()})
        elif isinstance(item, dict):
            v = item.get("value") or item.get("id") or item.get("model")
            if v is None:
                continue
            v_str = str(v).strip()
            if not v_str:
                continue
            lab = item.get("label") or item.get("name") or v_str
            out.append({"value": v_str, "label": str(lab)})
    return out or list(DEFAULT_MODEL_OPTIONS)


def resolve_prompt_and_style(
    user: User,
    prompt_key: str,
    style_key: str,
) -> tuple[str, str]:
    """
    根据用户 ai_prompt_config_json 将前端传入的选项 value 展开为实际模板文案。
    未配置或找不到时保留原字符串（兼容旧行为）。
    """
    p_out, s_out = prompt_key, style_key
    raw = (user.ai_prompt_config_json or "").strip()
    if not raw:
        return p_out, s_out
    try:
        cfg: Any = json.loads(raw)
    except json.JSONDecodeError:
        return p_out, s_out
    if not isinstance(cfg, dict):
        return p_out, s_out

    for item in cfg.get("prompts") or []:
        if isinstance(item, dict) and str(item.get("value", "")) == str(prompt_key):
            t = item.get("template") or item.get("content") or item.get("text")
            if t is not None and str(t).strip():
                p_out = str(t).strip()
            break

    for item in cfg.get("styles") or []:
        if isinstance(item, dict) and str(item.get("value", "")) == str(style_key):
            h = item.get("hint") or item.get("description") or item.get("label")
            if h is not None and str(h).strip():
                s_out = str(h).strip()
            break

    return p_out, s_out


def user_custom_openai_credentials(user: User) -> tuple[str, str] | None:
    """
    若用户已配置自建 API 地址与可解密密钥，返回 (api_key, base_url)；否则返回 None。
    """
    base = (user.ai_api_base_url or "").strip()
    if not base:
        return None
    key = try_decrypt(user.ai_api_key_encrypted)
    if not key:
        return None
    return key, base.rstrip("/")
