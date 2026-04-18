"""邮件发送服务：SMTP发送+邮箱验证码管理+密码重置链接。"""

from __future__ import annotations

import logging
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)

# 内存存储：{email: {"code": "123456", "expires_at": datetime, "sent_at": datetime}}
_email_code_store: dict[str, dict] = {}

# 验证码有效期和发送间隔
EMAIL_CODE_TTL_SECONDS = 300  # 5分钟
EMAIL_CODE_INTERVAL_SECONDS = 60  # 60秒内不可重发

# 密码重置Token存储：{token: {"email": "...", "used": False, "expires_at": datetime}}
_reset_token_store: dict[str, dict] = {}
RESET_TOKEN_TTL_SECONDS = 1800  # 30分钟


def _cleanup_expired() -> None:
    """清理过期的验证码和重置Token。"""
    now = datetime.now(timezone.utc)
    expired_emails = [k for k, v in _email_code_store.items() if v["expires_at"] < now]
    for k in expired_emails:
        del _email_code_store[k]
    expired_tokens = [k for k, v in _reset_token_store.items() if v["expires_at"] < now]
    for k in expired_tokens:
        del _reset_token_store[k]


def generate_email_code() -> str:
    """生成6位数字验证码。"""
    return "".join(secrets.choice(string.digits) for _ in range(6))


def can_send_code(email: str) -> tuple[bool, str]:
    """检查是否可以发送验证码（频率限制）。"""
    _cleanup_expired()
    entry = _email_code_store.get(email)
    if entry:
        elapsed = (datetime.now(timezone.utc) - entry["sent_at"]).total_seconds()
        if elapsed < EMAIL_CODE_INTERVAL_SECONDS:
            remaining = int(EMAIL_CODE_INTERVAL_SECONDS - elapsed)
            return False, f"请{remaining}秒后再试"
    return True, ""


def store_email_code(email: str, code: str) -> None:
    """存储邮箱验证码。"""
    now = datetime.now(timezone.utc)
    _email_code_store[email] = {
        "code": code,
        "expires_at": now + timedelta(seconds=EMAIL_CODE_TTL_SECONDS),
        "sent_at": now,
    }


def verify_email_code(email: str, user_input: str) -> bool:
    """校验邮箱验证码。"""
    _cleanup_expired()
    entry = _email_code_store.get(email)
    if not entry:
        return False
    if entry["expires_at"] < datetime.now(timezone.utc):
        del _email_code_store[email]
        return False
    if entry["code"] != user_input.strip():
        return False
    # 验证成功后删除
    del _email_code_store[email]
    return True


def create_reset_token(email: str) -> str:
    """创建密码重置Token。"""
    _cleanup_expired()
    token = uuid.uuid4().hex
    _reset_token_store[token] = {
        "email": email,
        "used": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=RESET_TOKEN_TTL_SECONDS),
    }
    return token


def verify_reset_token(token: str) -> str | None:
    """验证重置Token，返回关联邮箱或None。"""
    _cleanup_expired()
    entry = _reset_token_store.get(token)
    if not entry:
        return None
    if entry["used"]:
        return None
    if entry["expires_at"] < datetime.now(timezone.utc):
        del _reset_token_store[token]
        return None
    # 标记为已使用
    entry["used"] = True
    return entry["email"]


async def send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    """通过 SMTP 发送邮件。"""
    if not settings.smtp_host or not settings.smtp_user:
        logger.warning(
            "SMTP 未配置（SMTP_HOST/SMTP_USER 为空），邮件功能不可用。"
            "请在 .env 中配置 SMTP 相关环境变量，参考 .env.example"
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from_email or settings.smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.smtp_use_ssl:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=True,
            )
        else:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                start_tls=True,
            )
        logger.info("邮件发送成功: to=%s subject=%s", to_email, subject)
        return True
    except Exception:
        logger.error("邮件发送失败: to=%s", to_email, exc_info=True)
        return False


async def send_verification_code_email(
    *,
    to_email: str,
    code: str,
) -> bool:
    """发送邮箱验证码邮件。"""
    subject = "YouTube Compass - 邮箱验证码"
    html = f"""
    <div style="max-width:480px;margin:0 auto;padding:24px;font-family:system-ui,sans-serif">
      <h2 style="color:#0f172a;margin-bottom:16px">YouTube Compass 邮箱验证</h2>
      <p style="color:#475569;font-size:15px">您的验证码为：</p>
      <div style="background:#f1f5f9;border-radius:8px;padding:16px;text-align:center;margin:16px 0">
        <span style="font-size:32px;font-weight:700;letter-spacing:8px;color:#0f172a">{code}</span>
      </div>
      <p style="color:#94a3b8;font-size:13px">验证码5分钟内有效，如非本人操作请忽略。</p>
    </div>
    """
    return await send_email(to_email=to_email, subject=subject, html_body=html)


async def send_reset_password_email(
    *,
    to_email: str,
    reset_url: str,
) -> bool:
    """发送密码重置邮件。"""
    subject = "YouTube Compass - 密码重置"
    html = f"""
    <div style="max-width:480px;margin:0 auto;padding:24px;font-family:system-ui,sans-serif">
      <h2 style="color:#0f172a;margin-bottom:16px">YouTube Compass 密码重置</h2>
      <p style="color:#475569;font-size:15px">您正在重置密码，请点击下方按钮：</p>
      <div style="text-align:center;margin:24px 0">
        <a href="{reset_url}" style="background:#3b82f6;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-size:15px;font-weight:600">重置密码</a>
      </div>
      <p style="color:#94a3b8;font-size:13px">链接30分钟内有效。如非本人操作，请忽略此邮件。</p>
    </div>
    """
    return await send_email(to_email=to_email, subject=subject, html_body=html)
