from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.youtube import YouTubeChannel, YouTubeChannelHistory, YouTubeVideo, UserCompetitorPool
from app.services.youtube_service import parse_datetime


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
        content_details = item.get("contentDetails", {})
        status = item.get("status", {})
        if video is None:
            video = YouTubeVideo(
                yt_video_id=yt_video_id,
                channel_id=channel_id,
                title=snippet.get("title", ""),
                thumbnail_url=(snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                published_at=item.get("_parsed_published_at"),
                duration_sec=int(item.get("_duration_sec", 0)),
                duration_str=item.get("_duration_str", "00:00"),
                definition=content_details.get("definition", "sd"),
                privacy_status=status.get("privacyStatus", "public"),
                category_id=snippet.get("categoryId"),
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
            video.duration_sec = int(item.get("_duration_sec", 0))
            video.duration_str = item.get("_duration_str", "00:00")
            video.definition = content_details.get("definition", "sd")
            video.privacy_status = status.get("privacyStatus", "public")
            video.category_id = snippet.get("categoryId")
            video.view_count = int(statistics.get("viewCount", 0))
            video.like_count = int(statistics.get("likeCount", 0))
            video.comment_count = int(statistics.get("commentCount", 0))
        saved.append(video)
    await session.flush()
    return saved


async def bulk_upsert_channels_from_api_items(
    session: AsyncSession,
    channel_items: list[dict],
) -> dict[str, int]:
    """
    根据 YouTube Data API 返回的 channels 条目批量 UPSERT。
    返回 yt_channel_id -> 数据库主键 id。
    """
    if not channel_items:
        return {}

    rows: list[dict] = []
    for item in channel_items:
        yt_id = item.get("id")
        if not yt_id:
            continue
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        rows.append(
            {
                "yt_channel_id": yt_id,
                "title": snippet.get("title", "") or "",
                "description": snippet.get("description", "") or "",
                "thumbnail_url": (snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                "subscriber_count": int(statistics.get("subscriberCount", 0)),
                "total_views": int(statistics.get("viewCount", 0)),
                "video_count": int(statistics.get("videoCount", 0)),
                "published_at": parse_datetime(snippet.get("publishedAt")),
            }
        )

    if not rows:
        return {}

    t = YouTubeChannel.__table__
    stmt = mysql_insert(t).values(rows)
    stmt = stmt.on_duplicate_key_update(
        title=stmt.inserted.title,
        description=stmt.inserted.description,
        thumbnail_url=stmt.inserted.thumbnail_url,
        subscriber_count=stmt.inserted.subscriber_count,
        total_views=stmt.inserted.total_views,
        video_count=stmt.inserted.video_count,
        published_at=stmt.inserted.published_at,
        updated_at=func.now(),
    )
    await session.execute(stmt)
    await session.flush()

    yt_ids = [r["yt_channel_id"] for r in rows]
    res = await session.execute(select(YouTubeChannel).where(YouTubeChannel.yt_channel_id.in_(yt_ids)))
    mapping: dict[str, int] = {}
    for ch in res.scalars().all():
        mapping[ch.yt_channel_id] = ch.id
    return mapping


async def bulk_upsert_videos_from_api_items(
    session: AsyncSession,
    video_items: list[dict],
    yt_channel_id_to_db_id: dict[str, int],
) -> int:
    """批量 UPSERT 视频，返回写入条数（含更新）。"""
    rows: list[dict] = []
    for item in video_items:
        yt_video_id = item.get("id")
        if not yt_video_id:
            continue
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})
        status = item.get("status", {})
        ch_yt = snippet.get("channelId")
        db_cid = yt_channel_id_to_db_id.get(ch_yt or "")
        if not db_cid:
            continue
        rows.append(
            {
                "yt_video_id": yt_video_id,
                "channel_id": db_cid,
                "title": snippet.get("title", "") or "",
                "thumbnail_url": (snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                "published_at": item.get("_parsed_published_at"),
                "duration_sec": int(item.get("_duration_sec", 0)),
                "duration_str": item.get("_duration_str", "00:00"),
                "definition": content_details.get("definition", "sd"),
                "privacy_status": status.get("privacyStatus", "public"),
                "category_id": snippet.get("categoryId"),
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)),
                "comment_count": int(statistics.get("commentCount", 0)),
            }
        )

    if not rows:
        return 0

    vt = YouTubeVideo.__table__
    stmt = mysql_insert(vt).values(rows)
    stmt = stmt.on_duplicate_key_update(
        channel_id=stmt.inserted.channel_id,
        title=stmt.inserted.title,
        thumbnail_url=stmt.inserted.thumbnail_url,
        published_at=stmt.inserted.published_at,
        duration_sec=stmt.inserted.duration_sec,
        duration_str=stmt.inserted.duration_str,
        definition=stmt.inserted.definition,
        privacy_status=stmt.inserted.privacy_status,
        category_id=stmt.inserted.category_id,
        view_count=stmt.inserted.view_count,
        like_count=stmt.inserted.like_count,
        comment_count=stmt.inserted.comment_count,
        updated_at=func.now(),
    )
    await session.execute(stmt)
    await session.flush()
    return len(rows)


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


async def delete_user_competitor_channel(session: AsyncSession, *, user_id: int, pool_id: int) -> bool:
    result = await session.execute(
        select(UserCompetitorPool).where(
            UserCompetitorPool.id == pool_id,
            UserCompetitorPool.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def list_distinct_monitored_channels(session: AsyncSession) -> list[YouTubeChannel]:
    result = await session.execute(
        select(YouTubeChannel)
        .join(UserCompetitorPool, UserCompetitorPool.channel_id == YouTubeChannel.id)
        .distinct()
        .order_by(YouTubeChannel.id.asc())
    )
    return list(result.scalars().all())


async def query_videos(
    session: AsyncSession,
    *,
    user_id: int,
    keyword: str | None = None,
    start_date=None,
    end_date=None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    channel_id: int | None = None,
    definition: str | None = None,
    privacy_status: str | None = None,
    sort_by: str = "publish_time_desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[YouTubeVideo], int]:
    stmt: Select = (
        select(YouTubeVideo)
        .join(YouTubeChannel, YouTubeChannel.id == YouTubeVideo.channel_id)
        .join(UserCompetitorPool, UserCompetitorPool.channel_id == YouTubeChannel.id)
        .where(UserCompetitorPool.user_id == user_id)
    )

    if keyword:
        stmt = stmt.where(YouTubeVideo.title.ilike(f"%{keyword}%"))
    if start_date:
        stmt = stmt.where(YouTubeVideo.published_at >= start_date)
    if end_date:
        stmt = stmt.where(YouTubeVideo.published_at <= end_date)
    if min_duration is not None:
        stmt = stmt.where(YouTubeVideo.duration_sec >= min_duration)
    if max_duration is not None:
        stmt = stmt.where(YouTubeVideo.duration_sec <= max_duration)
    if channel_id is not None:
        stmt = stmt.where(YouTubeVideo.channel_id == channel_id)
    if definition:
        stmt = stmt.where(YouTubeVideo.definition == definition)
    if privacy_status:
        stmt = stmt.where(YouTubeVideo.privacy_status == privacy_status)

    if sort_by == "publish_time_asc":
        stmt = stmt.order_by(YouTubeVideo.published_at.asc())
    elif sort_by == "view_count_desc":
        stmt = stmt.order_by(YouTubeVideo.view_count.desc())
    elif sort_by == "view_count_asc":
        stmt = stmt.order_by(YouTubeVideo.view_count.asc())
    else:
        stmt = stmt.order_by(YouTubeVideo.published_at.desc())

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int((await session.execute(count_stmt)).scalar_one())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all()), total


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

