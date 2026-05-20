"""游客识别服务：通过 IP 地址 + Cookie guest_id 识别游客，MySQL 存储配额。

核心策略：IP 优先于 Cookie。无 Cookie 时先按 IP 查找已有会话，防止清除 Cookie 绕过配额。
IP 提取策略：根据 TRUSTED_PROXY_COUNT 配置决定是否信任 X-Forwarded-For 头，
防止攻击者伪造 IP 绕过配额。
"""

from __future__ import annotations

import ipaddress
import uuid
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.guest_session_crud import (
    create_guest_session,
    get_guest_session,
    get_guest_session_by_ip,
)

_GUEST_COOKIE_NAME = "guest_id"
_GUEST_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 天


@dataclass
class GuestInfo:
    """游客识别信息。"""

    guest_id: str
    ip_address: str | None
    is_new: bool


def _validate_ip_address(ip_str: str) -> bool:
    """验证 IP 地址是否合法且非内网/回环/保留地址，防止伪造 IP 绕过配额。

    拒绝的地址类型：
    - 回环地址（127.0.0.1, ::1）
    - 任意地址（0.0.0.0, ::）
    - 内网地址（10.x, 172.16-31.x, 192.168.x, fc00::/7）
    - 链路本地（169.254.x, fe80::）
    """
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if addr.is_loopback or addr.is_unspecified:
        return False
    if addr.is_private or addr.is_link_local:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.is_site_local:
        return False
    return True


def _extract_client_ip(request: Request) -> str | None:
    """从请求中安全提取客户端真实 IP 地址。

    策略：
    - TRUSTED_PROXY_COUNT == 0：不信任任何代理头，直接使用 request.client.host
    - TRUSTED_PROXY_COUNT > 0：从 X-Forwarded-For 右侧倒数第 N 个位置取 IP，
      并验证格式合法性；无效则回退到 request.client.host
    """
    proxy_count = settings.trusted_proxy_count

    if proxy_count > 0:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # X-Forwarded-For 格式: client, proxy1, proxy2, ...
            # 最右侧的 proxy_count 个是受信任代理添加的，其左侧即为客户端真实 IP
            parts = [p.strip() for p in forwarded.split(",")]
            # 从右侧倒数第 proxy_count 个位置取 IP
            idx = len(parts) - proxy_count
            if idx >= 0:
                candidate = parts[idx]
                if _validate_ip_address(candidate):
                    return candidate
        # X-Forwarded-For 不存在或 IP 无效，回退到直连 IP
        if request.client:
            return request.client.host
        return None

    # 不信任代理头，直接使用直连 IP
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
    """识别游客：IP 优先策略，防止清除 Cookie 绕过配额。

    查找顺序：
    1. Cookie 有效 -> 查 DB 复用已有会话
    2. 无 Cookie -> 按 IP 查找当日已有会话（核心防绕过逻辑）
    3. 均未找到 -> 创建新会话
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

    # 无 Cookie：先按 IP 查找当日已有会话（防止清除 Cookie 绕过配额）
    if ip_address:
        ip_session = await get_guest_session_by_ip(session, ip_address)
        if ip_session:
            return GuestInfo(
                guest_id=ip_session.guest_id, ip_address=ip_address, is_new=False,
            )

    # 未找到 -> 创建新会话
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


async def reserve_guest_quota(
    session: AsyncSession,
    guest_id: str,
    api_type: str = "youtube_api",
) -> tuple[bool, int, int]:
    """预留检查游客配额是否充足，不扣减。用于"先检查后消费"模式。

    返回 (allowed, used, limit)：
    - allowed: 是否允许
    - used: 当日已用量
    - limit: 每日限额
    """
    from app.services.rate_limit_service import check_quota

    allowed, used, limit = await check_quota(
        session,
        user_id=None,
        role="guest",
        guest_id=guest_id,
        api_type=api_type,
        subscription_quotas=None,
    )
    return allowed, used, limit


async def consume_guest_quota(
    session: AsyncSession,
    guest_id: str,
    api_type: str = "youtube_api",
) -> None:
    """实际扣减游客配额，仅在 API 调用成功后调用。"""
    from app.services.rate_limit_service import increment_usage

    await increment_usage(
        session,
        user_id=None,
        role="guest",
        guest_id=guest_id,
        api_type=api_type,
    )
    await session.commit()
