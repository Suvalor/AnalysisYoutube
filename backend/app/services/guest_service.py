"""游客识别服务：通过 Cookie guest_id + IP 地址识别游客，MySQL 存储配额。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.guest_session_crud import create_guest_session, get_guest_session

_GUEST_COOKIE_NAME = "guest_id"
_GUEST_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 天


@dataclass
class GuestInfo:
    """游客识别信息。"""

    guest_id: str
    ip_address: str | None
    is_new: bool


def _extract_client_ip(request: Request) -> str | None:
    """从请求中提取客户端 IP 地址，优先读取反向代理头。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return None


def generate_guest_id() -> str:
    """生成唯一游客标识 UUID。"""
    return str(uuid.uuid4())


async def identify_guest(
    request: Request,
    session: AsyncSession,
) -> GuestInfo:
    """识别游客：从 Cookie 读取 guest_id，不存在则生成新 ID 并写入 Cookie。

    返回 GuestInfo 包含 guest_id、IP 地址和是否为新游客。
    """
    guest_id = request.cookies.get(_GUEST_COOKIE_NAME)
    ip_address = _extract_client_ip(request)

    if guest_id:
        # 已有 Cookie，检查数据库中是否存在
        existing = await get_guest_session(session, guest_id)
        if existing:
            return GuestInfo(guest_id=guest_id, ip_address=ip_address, is_new=False)
        # Cookie 存在但数据库无记录，复用 guest_id 创建新记录
        await create_guest_session(session, guest_id=guest_id, ip_address=ip_address)
        await session.commit()
        return GuestInfo(guest_id=guest_id, ip_address=ip_address, is_new=True)

    # 无 Cookie，生成新 guest_id
    new_guest_id = generate_guest_id()
    await create_guest_session(session, guest_id=new_guest_id, ip_address=ip_address)
    await session.commit()
    return GuestInfo(guest_id=new_guest_id, ip_address=ip_address, is_new=True)


def set_guest_cookie(response, guest_id: str) -> None:
    """在响应中设置游客 Cookie，启用 HttpOnly、Secure（生产环境）、SameSite=Lax 安全属性。"""
    response.set_cookie(
        key=_GUEST_COOKIE_NAME,
        value=guest_id,
        max_age=_GUEST_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
