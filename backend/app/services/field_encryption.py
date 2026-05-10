"""用户敏感字段（如 AI API Key）的服务端对称加密，依赖 SECRET_KEY 或专用环境变量。

安全说明：
  - 使用 Fernet 对称加密，密钥由 SECRET_KEY 或 FIELD_ENCRYPTION_SECRET 派生。
  - 生产环境务必设置独立的 FIELD_ENCRYPTION_SECRET（与 JWT 的 SECRET_KEY 分离），
    以便独立轮换，降低密钥泄露影响面。
  - 数据库泄露 + 密钥泄露 = 所有 API Key 明文暴露，因此密钥管理至关重要。
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


def _fernet_key_material(secret: str) -> bytes:
    """从配置字符串派生 Fernet 所需的 32 字节 URL-Safe Base64 密钥。"""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_secret() -> str:
    """优先使用专用加密盐，否则回退到 JWT 用的 SECRET_KEY。强制最小 32 字符。"""
    raw = (settings.field_encryption_secret or settings.secret_key or "").strip()
    if not raw or len(raw) < 32:
        raise ValueError(
            "SECRET_KEY 或 FIELD_ENCRYPTION_SECRET 必须至少 32 个字符，"
            "否则无法安全加密存储 API Key"
        )
    if not settings.field_encryption_secret:
        logger.warning(
            "FIELD_ENCRYPTION_SECRET 未设置，回退使用 SECRET_KEY 加密字段。"
            "生产环境建议设置独立的 FIELD_ENCRYPTION_SECRET 以支持密钥独立轮换。"
        )
    return raw


def encrypt_plaintext(plain: str) -> str:
    """加密明文，返回可存入数据库的字符串。"""
    f = Fernet(_fernet_key_material(_get_secret()))
    return f.encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_plaintext(token: str) -> str:
    """解密密文；失败时抛出异常由调用方处理。"""
    f = Fernet(_fernet_key_material(_get_secret()))
    return f.decrypt(token.encode("ascii")).decode("utf-8")


def try_decrypt(token: str | None) -> str | None:
    """解密；格式错误或密钥变更时返回 None，避免拖垮业务流程。"""
    if not token or not token.strip():
        return None
    try:
        return decrypt_plaintext(token.strip())
    except (InvalidToken, ValueError, TypeError):
        return None
