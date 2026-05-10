from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.yt_channel import YtChannel


async def get_channel_by_channel_id(session: AsyncSession, channel_id: str) -> YtChannel | None:
    result = await session.execute(
        select(YtChannel).where(YtChannel.channel_id == channel_id)
    )
    return result.scalar_one_or_none()


async def upsert_channel(
    session: AsyncSession,
    *,
    channel_id: str,
    title: str,
    description: str,
    thumbnail_url: str | None,
    subscriber_count: int,
    video_count: int,
    view_count: int,
    published_at,
    raw_data: dict,
) -> YtChannel:
    existing = await get_channel_by_channel_id(session, channel_id)
    if existing is None:
        existing = YtChannel(
            channel_id=channel_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            subscriber_count=subscriber_count,
            video_count=video_count,
            view_count=view_count,
            published_at=published_at,
            raw_data=raw_data,
        )
        session.add(existing)
    else:
        existing.title = title
        existing.description = description
        existing.thumbnail_url = thumbnail_url
        existing.subscriber_count = subscriber_count
        existing.video_count = video_count
        existing.view_count = view_count
        existing.published_at = published_at
        existing.raw_data = raw_data

    await session.commit()
    await session.refresh(existing)
    return existing

