"""游客会话 CRUD 操作。"""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest_session import GuestSession


async def get_guest_session(
    session: AsyncSession,
    guest_id: str,
    *,
    for_update: bool = False,
) -> GuestSession | None:
    """根据 guest_id 查询游客会话。for_update=True 时加行级锁防止并发竞态。"""
    stmt = select(GuestSession).where(GuestSession.guest_id == guest_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_guest_session(
    session: AsyncSession,
    *,
    guest_id: str,
    ip_address: str | None = None,
) -> GuestSession:
    """创建游客会话记录，初始化当日配额。"""
    today_str = date.today().isoformat()
    guest = GuestSession(
        guest_id=guest_id,
        ip_address=ip_address,
        daily_quotas={
            "youtube_api": 0,
            "llm_api": 0,
            "cv_api": 0,
            "date": today_str,
        },
        last_active_at=datetime.now(timezone.utc),
    )
    session.add(guest)
    await session.flush()
    await session.refresh(guest)
    return guest


async def increment_guest_quota(
    session: AsyncSession,
    guest: GuestSession,
    api_type: str,
    count: int = 1,
) -> GuestSession:
    """增加游客指定 API 类型的当日使用计数，如果日期变更则重置。"""
    today_str = date.today().isoformat()
    quotas = guest.daily_quotas or {}

    # 日期变更时重置所有计数
    if quotas.get("date") != today_str:
        quotas = {
            "youtube_api": 0,
            "llm_api": 0,
            "cv_api": 0,
            "date": today_str,
        }

    quotas[api_type] = quotas.get(api_type, 0) + count
    guest.daily_quotas = quotas
    guest.last_active_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(guest)
    return guest


async def get_guest_daily_usage(
    session: AsyncSession,
    guest_id: str,
) -> dict:
    """获取游客当日配额使用情况，日期不匹配时返回零值。"""
    guest = await get_guest_session(session, guest_id)
    if guest is None:
        return {"youtube_api": 0, "llm_api": 0, "cv_api": 0}

    today_str = date.today().isoformat()
    quotas = guest.daily_quotas or {}
    if quotas.get("date") != today_str:
        return {"youtube_api": 0, "llm_api": 0, "cv_api": 0}

    return {
        "youtube_api": quotas.get("youtube_api", 0),
        "llm_api": quotas.get("llm_api", 0),
        "cv_api": quotas.get("cv_api", 0),
    }
