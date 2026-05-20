"""频道缓存 CRUD 操作。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_cache import ChannelCache


async def get_cached_channel(session: AsyncSession, channel_id: str) -> ChannelCache | None:
    """按 channel_id 查询缓存记录。"""
    result = await session.execute(
        select(ChannelCache).where(ChannelCache.channel_id == channel_id)
    )
    return result.scalar_one_or_none()


async def get_cached_channel_if_fresh(
    session: AsyncSession,
    channel_id: str,
    ttl_hours: int = 24,
) -> ChannelCache | None:
    """查询缓存记录，仅在未过期时返回。"""
    cache = await get_cached_channel(session, channel_id)
    if cache is None:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, ttl_hours))
    if cache.cached_at >= cutoff:
        return cache
    return None


async def get_cached_channel_even_if_stale(
    session: AsyncSession,
    channel_id: str,
) -> ChannelCache | None:
    """查询缓存记录，无论是否过期均返回（用于刷新失败时回退旧数据）。"""
    return await get_cached_channel(session, channel_id)


async def batch_get_cached_channels_if_fresh(
    session: AsyncSession,
    channel_ids: list[str],
    ttl_hours: int = 24,
) -> dict[str, ChannelCache]:
    """批量查询缓存记录，仅返回未过期的。"""
    if not channel_ids:
        return {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, ttl_hours))
    result = await session.execute(
        select(ChannelCache)
        .where(
            ChannelCache.channel_id.in_(channel_ids),
            ChannelCache.cached_at >= cutoff,
        )
    )
    rows = result.scalars().all()
    return {row.channel_id: row for row in rows}


async def upsert_channel_cache(
    session: AsyncSession,
    *,
    channel_id: str,
    title: str,
    description: str,
    avatar_url: str | None,
    subscriber_count: int,
    video_count: int,
    view_count: int,
    published_at: datetime | None,
    country: str | None,
    custom_url: str | None,
    refresh_attempted_at: datetime | None = None,
) -> ChannelCache:
    """创建或更新频道缓存记录。"""
    existing = await get_cached_channel(session, channel_id)
    if existing is None:
        existing = ChannelCache(
            channel_id=channel_id,
            title=title,
            description=description,
            avatar_url=avatar_url,
            subscriber_count=subscriber_count,
            video_count=video_count,
            view_count=view_count,
            published_at=published_at,
            country=country,
            custom_url=custom_url,
            refresh_attempted_at=refresh_attempted_at,
        )
        session.add(existing)
    else:
        existing.title = title
        existing.description = description
        existing.avatar_url = avatar_url
        existing.subscriber_count = subscriber_count
        existing.video_count = video_count
        existing.view_count = view_count
        existing.published_at = published_at
        existing.country = country
        existing.custom_url = custom_url
        # 刷新缓存时间戳
        existing.cached_at = datetime.now(timezone.utc)
        existing.refresh_attempted_at = refresh_attempted_at
    await session.flush()
    return existing


async def mark_refresh_attempted(
    session: AsyncSession,
    channel_id: str,
) -> None:
    """标记缓存记录的刷新尝试时间，防止短时间内重复刷新。"""
    cache = await get_cached_channel(session, channel_id)
    if cache is not None:
        cache.refresh_attempted_at = datetime.now(timezone.utc)
        await session.flush()