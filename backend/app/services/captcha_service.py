"""图形验证码服务：生成+校验+过期清理。"""

from __future__ import annotations

import base64
import io
import random  # 用于图片噪点/干扰线（非安全敏感）
import secrets  # 用于验证码字符生成（密码学安全）
import string
import uuid
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont


# 内存存储：{captcha_id: {"code": "abc123", "expires_at": datetime}}
_captcha_store: dict[str, dict] = {}

# 验证码有效期（秒）
CAPTCHA_TTL_SECONDS = 300  # 5分钟


def _cleanup_expired() -> None:
    """清理过期的验证码。"""
    now = datetime.now(timezone.utc)
    expired_keys = [k for k, v in _captcha_store.items() if v["expires_at"] < now]
    for k in expired_keys:
        del _captcha_store[k]


def generate_captcha() -> tuple[str, str]:
    """生成图形验证码，返回 (captcha_id, base64_image)。"""
    _cleanup_expired()

    # 生成4位随机验证码（字母+数字，排除易混淆字符）
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "").replace("L", "")
    code = "".join(secrets.choice(chars) for _ in range(4))

    captcha_id = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=CAPTCHA_TTL_SECONDS)
    _captcha_store[captcha_id] = {"code": code, "expires_at": expires_at}

    # 生成图片
    width, height = 120, 40
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)

    # 绘制验证码文字
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # 每个字符随机偏移和旋转
    x_offset = 10
    for ch in code:
        y_offset = random.randint(2, 8)
        draw.text((x_offset, y_offset), ch, fill=random_color(), font=font)
        x_offset += 26

    # 添加干扰线
    for _ in range(4):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=random_color(), width=1)

    # 添加噪点
    for _ in range(60):
        x, y = random.randint(0, width - 1), random.randint(0, height - 1)
        draw.point((x, y), fill=random_color())

    # 转为 Base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return captcha_id, b64_image


def verify_captcha(captcha_id: str, user_input: str) -> bool:
    """校验验证码，正确或过期后删除（一次性使用）。"""
    _cleanup_expired()

    entry = _captcha_store.pop(captcha_id, None)
    if not entry:
        return False

    # 不区分大小写
    return entry["code"].upper() == user_input.strip().upper()


def random_color() -> tuple[int, int, int]:
    """生成随机颜色（深色，确保在浅背景上可见）。"""
    return (random.randint(30, 150), random.randint(30, 150), random.randint(30, 150))
