"""配额检查与计数服务：根据用户角色和订阅状态执行分层限额管控。"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.guest_session_crud import get_guest_daily_usage, get_guest_session
from app.crud.subscription_crud import get_active_user_subscription
from app.models.user import UserRole

logger = logging.getLogger(__name__)

# 各角色默认每日配额上限
DEFAULT_QUOTAS: dict[str, dict[str, int]] = {
    UserRole.GUEST: {"youtube_api": 5, "llm_api": 0, "cv_api": 0},
    UserRole.USER: {"youtube_api": 20, "llm_api": 10, "cv_api": 5},
    UserRole.SUBSCRIBER: {"youtube_api": 100, "llm_api": 50, "cv_api": 20},
    UserRole.ADMIN: {"youtube_api": -1, "llm_api": -1, "cv_api": -1},  # -1 表示无限制
}

# 用户每日配额使用量缓存 key 前缀（存入 guest_sessions.daily_quotas 格式）
_USER_QUOTA_KEY_PREFIX = "user_daily_quota"


def get_role_limits(role: str, subscription_quotas: dict | None = None) -> dict[str, int]:
    """获取指定角色的配额上限，订阅用户优先使用订阅套餐配额。"""
    if role == UserRole.ADMIN:
        return DEFAULT_QUOTAS[UserRole.ADMIN]

    if role == UserRole.SUBSCRIBER and subscription_quotas:
        return subscription_quotas

    return DEFAULT_QUOTAS.get(role, DEFAULT_QUOTAS[UserRole.USER])


async def check_quota(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    role: str = UserRole.GUEST,
    guest_id: str | None = None,
    api_type: str = "youtube_api",
    subscription_quotas: dict | None = None,
) -> tuple[bool, int, int]:
    """检查配额是否允许本次 API 调用。

    返回 (allowed, used, limit)：
    - allowed: 是否允许
    - used: 当日已用量
    - limit: 每日限额（-1 表示无限制）
    """
    limits = get_role_limits(role, subscription_quotas)
    limit = limits.get(api_type, 0)

    # 管理员无限制
    if limit == -1:
        return True, 0, -1

    # 游客从 guest_sessions 读取使用量
    if role == UserRole.GUEST and guest_id:
        usage = await get_guest_daily_usage(session, guest_id)
        used = usage.get(api_type, 0)
        allowed = used < limit
        if not allowed:
            logger.warning("配额超限: role=%s guest_id=%s api_type=%s used=%d limit=%d", role, guest_id, api_type, used, limit)
        return allowed, used, limit

    # 已登录用户从 guest_sessions 的 daily_quotas 字段读取（复用结构）
    # 这里用 user_id + date 作为 key 存入 guest_sessions
    if user_id:
        user_guest_id = f"{_USER_QUOTA_KEY_PREFIX}:{user_id}"
        usage = await get_guest_daily_usage(session, user_guest_id)
        used = usage.get(api_type, 0)
        allowed = used < limit
        if not allowed:
            logger.warning("配额超限: role=%s user_id=%s api_type=%s used=%d limit=%d", role, user_id, api_type, used, limit)
        return allowed, used, limit

    # 无用户信息时默认不允许
    return False, 0, limit


async def increment_usage(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    role: str = UserRole.GUEST,
    guest_id: str | None = None,
    api_type: str = "youtube_api",
    count: int = 1,
) -> None:
    """记录一次 API 调用的配额消耗。使用 SELECT ... FOR UPDATE 行级锁防止并发竞态。"""
    from app.crud.guest_session_crud import (
        create_guest_session,
        increment_guest_quota,
    )

    # 游客
    if role == UserRole.GUEST and guest_id:
        guest = await get_guest_session(session, guest_id, for_update=True)
        if guest is None:
            guest = await create_guest_session(session, guest_id=guest_id)
        await increment_guest_quota(session, guest, api_type, count)
        return

    # 已登录用户
    if user_id:
        user_guest_id = f"{_USER_QUOTA_KEY_PREFIX}:{user_id}"
        guest = await get_guest_session(session, user_guest_id, for_update=True)
        if guest is None:
            guest = await create_guest_session(session, guest_id=user_guest_id)
        await increment_guest_quota(session, guest, api_type, count)


async def get_user_quota_usage(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    role: str = UserRole.GUEST,
    guest_id: str | None = None,
) -> dict:
    """获取用户当日配额使用情况，返回各 API 类型的 used/limit。"""
    subscription_quotas = None
    if role == UserRole.SUBSCRIBER and user_id:
        sub = await get_active_user_subscription(session, user_id)
        if sub and sub.plan:
            subscription_quotas = sub.plan.quotas_json

    limits = get_role_limits(role, subscription_quotas)

    # 获取已用量
    if role == UserRole.GUEST and guest_id:
        usage = await get_guest_daily_usage(session, guest_id)
    elif user_id:
        user_guest_id = f"{_USER_QUOTA_KEY_PREFIX}:{user_id}"
        usage = await get_guest_daily_usage(session, user_guest_id)
    else:
        usage = {"youtube_api": 0, "llm_api": 0, "cv_api": 0}

    return {
        "role": role,
        "youtube_api_used": usage.get("youtube_api", 0),
        "youtube_api_limit": limits.get("youtube_api", 0),
        "llm_api_used": usage.get("llm_api", 0),
        "llm_api_limit": limits.get("llm_api", 0),
        "cv_api_used": usage.get("cv_api", 0),
        "cv_api_limit": limits.get("cv_api", 0),
    }
