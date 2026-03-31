from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.youtube import YouTubeChannel, YouTubeChannelHistory, YouTubeVideo, UserCompetitorPool


async def upsert_channel(
    session: AsyncSession,
    *,
    yt_channel_id: str,
    title: str,
    description: str,
    thumbnail_url: str | None,
    subscriber_count: int,
    total_views: int,
    video_count: int,
    published_at,
) -> YouTubeChannel:
    result = await session.execute(
        select(YouTubeChannel).where(YouTubeChannel.yt_channel_id == yt_channel_id)
    )
    channel = result.scalar_one_or_none()
    if channel is None:
        channel = YouTubeChannel(
            yt_channel_id=yt_channel_id,
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            subscriber_count=subscriber_count,
            total_views=total_views,
            video_count=video_count,
            published_at=published_at,
        )
        session.add(channel)
    else:
        channel.title = title
        channel.description = description
        channel.thumbnail_url = thumbnail_url
        channel.subscriber_count = subscriber_count
        channel.total_views = total_views
        channel.video_count = video_count
        channel.published_at = published_at
    await session.flush()
    return channel


async def upsert_videos(
    session: AsyncSession,
    *,
    channel_id: int,
    videos: list[dict],
) -> list[YouTubeVideo]:
    saved: list[YouTubeVideo] = []
    for item in videos:
        yt_video_id = item.get("id")
        if not yt_video_id:
            continue
        result = await session.execute(
            select(YouTubeVideo).where(YouTubeVideo.yt_video_id == yt_video_id)
        )
        video = result.scalar_one_or_none()
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        if video is None:
            video = YouTubeVideo(
                yt_video_id=yt_video_id,
                channel_id=channel_id,
                title=snippet.get("title", ""),
                thumbnail_url=(snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                published_at=item.get("_parsed_published_at"),
                view_count=int(statistics.get("viewCount", 0)),
                like_count=int(statistics.get("likeCount", 0)),
                comment_count=int(statistics.get("commentCount", 0)),
            )
            session.add(video)
        else:
            video.channel_id = channel_id
            video.title = snippet.get("title", "")
            video.thumbnail_url = (snippet.get("thumbnails", {}).get("high", {}) or {}).get("url")
            video.published_at = item.get("_parsed_published_at")
            video.view_count = int(statistics.get("viewCount", 0))
            video.like_count = int(statistics.get("likeCount", 0))
            video.comment_count = int(statistics.get("commentCount", 0))
        saved.append(video)
    await session.flush()
    return saved


async def ensure_competitor_pool(
    session: AsyncSession,
    *,
    user_id: int,
    channel_id: int,
    group_name: str,
) -> UserCompetitorPool:
    result = await session.execute(
        select(UserCompetitorPool).where(
            UserCompetitorPool.user_id == user_id, UserCompetitorPool.channel_id == channel_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserCompetitorPool(user_id=user_id, channel_id=channel_id, group_name=group_name)
        session.add(row)
    else:
        row.group_name = group_name
    await session.flush()
    return row


async def list_user_competitor_channels(session: AsyncSession, user_id: int) -> list[UserCompetitorPool]:
    result = await session.execute(
        select(UserCompetitorPool)
        .options(selectinload(UserCompetitorPool.channel))
        .where(UserCompetitorPool.user_id == user_id)
        .join(UserCompetitorPool.channel)
        .order_by(UserCompetitorPool.added_at.desc())
    )
    return list(result.scalars().unique().all())


async def list_distinct_monitored_channels(session: AsyncSession) -> list[YouTubeChannel]:
    result = await session.execute(
        select(YouTubeChannel)
        .join(UserCompetitorPool, UserCompetitorPool.channel_id == YouTubeChannel.id)
        .distinct()
        .order_by(YouTubeChannel.id.asc())
    )
    return list(result.scalars().all())


async def upsert_channel_history(
    session: AsyncSession,
    *,
    channel_id: int,
    record_date: date,
    subscriber_count: int,
    total_views: int,
    video_count: int,
) -> YouTubeChannelHistory:
    result = await session.execute(
        select(YouTubeChannelHistory).where(
            YouTubeChannelHistory.channel_id == channel_id,
            YouTubeChannelHistory.record_date == record_date,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = YouTubeChannelHistory(
            channel_id=channel_id,
            record_date=record_date,
            subscriber_count=subscriber_count,
            total_views=total_views,
            video_count=video_count,
        )
        session.add(row)
    else:
        row.subscriber_count = subscriber_count
        row.total_views = total_views
        row.video_count = video_count
    await session.flush()
    return row


async def get_channel_histories_for_compare(
    session: AsyncSession,
    *,
    channel_ids: list[int],
    start_date: date,
) -> list[YouTubeChannelHistory]:
    if not channel_ids:
        return []
    result = await session.execute(
        select(YouTubeChannelHistory)
        .where(
            YouTubeChannelHistory.channel_id.in_(channel_ids),
            YouTubeChannelHistory.record_date >= start_date,
        )
        .order_by(YouTubeChannelHistory.record_date.asc(), YouTubeChannelHistory.channel_id.asc())
    )
    return list(result.scalars().all())

