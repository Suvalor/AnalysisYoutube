from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.youtube import (
    YouTubeChannel,
    YouTubeChannelHistory,
    YouTubeChannelInsight,
    YouTubeComment,
    YouTubeVideoAnalysis,
    YouTubeVideo,
    UserCompetitorPool,
)
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
                description=snippet.get("description", "") or "",
                thumbnail_url=(snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                published_at=item.get("_parsed_published_at"),
                duration_sec=int(item.get("_duration_sec", 0)),
                duration_str=item.get("_duration_str", "00:00"),
                definition=content_details.get("definition", "sd"),
                privacy_status=status.get("privacyStatus", "public"),
                category_id=snippet.get("categoryId"),
                tags=snippet.get("tags") or [],
                view_count=int(statistics.get("viewCount", 0)),
                like_count=int(statistics.get("likeCount", 0)),
                comment_count=int(statistics.get("commentCount", 0)),
            )
            session.add(video)
        else:
            video.channel_id = channel_id
            video.title = snippet.get("title", "")
            video.description = snippet.get("description", "") or ""
            video.thumbnail_url = (snippet.get("thumbnails", {}).get("high", {}) or {}).get("url")
            video.published_at = item.get("_parsed_published_at")
            video.duration_sec = int(item.get("_duration_sec", 0))
            video.duration_str = item.get("_duration_str", "00:00")
            video.definition = content_details.get("definition", "sd")
            video.privacy_status = status.get("privacyStatus", "public")
            video.category_id = snippet.get("categoryId")
            video.tags = snippet.get("tags") or []
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
                "description": snippet.get("description", "") or "",
                "thumbnail_url": (snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                "published_at": item.get("_parsed_published_at"),
                "duration_sec": int(item.get("_duration_sec", 0)),
                "duration_str": item.get("_duration_str", "00:00"),
                "definition": content_details.get("definition", "sd"),
                "privacy_status": status.get("privacyStatus", "public"),
                "category_id": snippet.get("categoryId"),
                "tags": snippet.get("tags") or [],
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
        description=stmt.inserted.description,
        thumbnail_url=stmt.inserted.thumbnail_url,
        published_at=stmt.inserted.published_at,
        duration_sec=stmt.inserted.duration_sec,
        duration_str=stmt.inserted.duration_str,
        definition=stmt.inserted.definition,
        privacy_status=stmt.inserted.privacy_status,
        category_id=stmt.inserted.category_id,
        tags=stmt.inserted.tags,
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


async def list_user_competitor_channels(
    session: AsyncSession,
    user_id: int,
    *,
    sort_by: str = "added_desc",
) -> list[UserCompetitorPool]:
    """监控池频道列表，支持按频道指标排序。"""
    stmt = (
        select(UserCompetitorPool)
        .options(selectinload(UserCompetitorPool.channel))
        .where(UserCompetitorPool.user_id == user_id)
        .join(YouTubeChannel, UserCompetitorPool.channel_id == YouTubeChannel.id)
    )
    if sort_by == "subscriber_desc":
        stmt = stmt.order_by(YouTubeChannel.subscriber_count.desc())
    elif sort_by == "subscriber_asc":
        stmt = stmt.order_by(YouTubeChannel.subscriber_count.asc())
    elif sort_by == "total_views_desc":
        stmt = stmt.order_by(YouTubeChannel.total_views.desc())
    elif sort_by == "total_views_asc":
        stmt = stmt.order_by(YouTubeChannel.total_views.asc())
    elif sort_by == "video_count_desc":
        stmt = stmt.order_by(YouTubeChannel.video_count.desc())
    elif sort_by == "video_count_asc":
        stmt = stmt.order_by(YouTubeChannel.video_count.asc())
    else:
        stmt = stmt.order_by(UserCompetitorPool.added_at.desc())

    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_channel_for_user(
    session: AsyncSession,
    *,
    user_id: int,
    channel_id: int,
) -> YouTubeChannel | None:
    """当前用户监控池内是否包含该频道。"""
    stmt = (
        select(YouTubeChannel)
        .join(UserCompetitorPool, UserCompetitorPool.channel_id == YouTubeChannel.id)
        .where(UserCompetitorPool.user_id == user_id, YouTubeChannel.id == channel_id)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def update_channel_ai_insight(
    session: AsyncSession,
    *,
    channel: YouTubeChannel,
    ai_tags: list[str],
    ai_audience_age: str,
    ai_summary: str,
    ai_expertise: str | None = None,
) -> YouTubeChannel:
    channel.ai_tags = ai_tags
    channel.ai_audience_age = ai_audience_age
    channel.ai_summary = ai_summary
    if ai_expertise is not None:
        channel.ai_expertise = ai_expertise
    await session.flush()
    return channel


async def create_youtube_channel_insight(
    session: AsyncSession,
    *,
    channel_id: int,
    user_id: int,
    model_library_id: int | None,
    llm_model_name: str,
    agent_id: int | None,
    ai_tags: list[str],
    ai_expertise: str,
    ai_audience_age: str,
    ai_summary: str,
) -> YouTubeChannelInsight:
    row = YouTubeChannelInsight(
        channel_id=channel_id,
        user_id=user_id,
        model_library_id=model_library_id,
        llm_model_name=llm_model_name,
        agent_id=agent_id,
        ai_tags=ai_tags,
        ai_expertise=ai_expertise,
        ai_audience_age=ai_audience_age,
        ai_summary=ai_summary,
    )
    session.add(row)
    await session.flush()
    return row


async def get_video_for_user(
    session: AsyncSession,
    *,
    user_id: int,
    video_id: int,
) -> YouTubeVideo | None:
    """当前用户监控池内可访问的视频。"""
    stmt = (
        select(YouTubeVideo)
        .join(YouTubeChannel, YouTubeChannel.id == YouTubeVideo.channel_id)
        .join(UserCompetitorPool, UserCompetitorPool.channel_id == YouTubeChannel.id)
        .where(UserCompetitorPool.user_id == user_id, YouTubeVideo.id == video_id)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def get_video_analysis_for_org(
    session: AsyncSession,
    *,
    org_id: int,
    video_id: int,
) -> YouTubeVideoAnalysis | None:
    stmt = (
        select(YouTubeVideoAnalysis)
        .where(YouTubeVideoAnalysis.org_id == org_id, YouTubeVideoAnalysis.video_id == video_id)
    )
    r = await session.execute(stmt)
    return r.scalar_one_or_none()


async def upsert_video_analysis(
    session: AsyncSession,
    *,
    org_id: int,
    video_id: int,
    model_id: str,
    agent_id: int | None,
    content: str,
) -> YouTubeVideoAnalysis:
    row = await get_video_analysis_for_org(session, org_id=org_id, video_id=video_id)
    if row is None:
        row = YouTubeVideoAnalysis(
            video_id=video_id,
            org_id=org_id,
            model_id=model_id,
            agent_id=agent_id,
            content=content,
        )
        session.add(row)
    else:
        row.model_id = model_id
        row.agent_id = agent_id
        row.content = content
    await session.flush()
    try:
        await session.refresh(row)
    except Exception:
        # refresh 失败不影响写入结果；updated_at 字段可能是旧值
        pass
    return row


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


async def list_distinct_monitored_channels_for_org(session: AsyncSession, org_id: int) -> list[YouTubeChannel]:
    """某组织下：所有已加入监控池的频道（去重）。"""
    result = await session.execute(
        select(YouTubeChannel)
        .join(UserCompetitorPool, UserCompetitorPool.channel_id == YouTubeChannel.id)
        .join(User, User.id == UserCompetitorPool.user_id)
        .where(User.org_id == org_id)
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
    min_view_count: int | None = None,
    max_view_count: int | None = None,
    min_like_count: int | None = None,
    max_like_count: int | None = None,
    min_comment_count: int | None = None,
    max_comment_count: int | None = None,
    sort_by: str = "publish_time_desc",
    publish_time_sort: str | None = None,
    view_count_sort: str | None = None,
    like_count_sort: str | None = None,
    comment_count_sort: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[YouTubeVideo], int]:
    stmt: Select = (
        select(YouTubeVideo)
        .join(YouTubeChannel, YouTubeChannel.id == YouTubeVideo.channel_id)
        .join(UserCompetitorPool, UserCompetitorPool.channel_id == YouTubeChannel.id)
        .where(UserCompetitorPool.user_id == user_id)
        .options(selectinload(YouTubeVideo.channel))
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
    if min_view_count is not None:
        stmt = stmt.where(YouTubeVideo.view_count >= min_view_count)
    if max_view_count is not None:
        stmt = stmt.where(YouTubeVideo.view_count <= max_view_count)
    if min_like_count is not None:
        stmt = stmt.where(YouTubeVideo.like_count >= min_like_count)
    if max_like_count is not None:
        stmt = stmt.where(YouTubeVideo.like_count <= max_like_count)
    if min_comment_count is not None:
        stmt = stmt.where(YouTubeVideo.comment_count >= min_comment_count)
    if max_comment_count is not None:
        stmt = stmt.where(YouTubeVideo.comment_count <= max_comment_count)

    def _order_clause(col, direction: str | None):
        if direction == "asc":
            return col.asc()
        if direction == "desc":
            return col.desc()
        return None

    multi_parts: list = []
    for d, col in (
        (publish_time_sort, YouTubeVideo.published_at),
        (view_count_sort, YouTubeVideo.view_count),
        (like_count_sort, YouTubeVideo.like_count),
        (comment_count_sort, YouTubeVideo.comment_count),
    ):
        oc = _order_clause(col, d if d in ("asc", "desc") else None)
        if oc is not None:
            multi_parts.append(oc)

    if multi_parts:
        stmt = stmt.order_by(*multi_parts)
    elif sort_by == "publish_time_asc":
        stmt = stmt.order_by(YouTubeVideo.published_at.asc())
    elif sort_by == "view_count_desc":
        stmt = stmt.order_by(YouTubeVideo.view_count.desc())
    elif sort_by == "view_count_asc":
        stmt = stmt.order_by(YouTubeVideo.view_count.asc())
    elif sort_by == "like_count_desc":
        stmt = stmt.order_by(YouTubeVideo.like_count.desc())
    elif sort_by == "like_count_asc":
        stmt = stmt.order_by(YouTubeVideo.like_count.asc())
    elif sort_by == "comment_count_desc":
        stmt = stmt.order_by(YouTubeVideo.comment_count.desc())
    elif sort_by == "comment_count_asc":
        stmt = stmt.order_by(YouTubeVideo.comment_count.asc())
    else:
        stmt = stmt.order_by(YouTubeVideo.published_at.desc())

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int((await session.execute(count_stmt)).scalar_one())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all()), total


async def bulk_upsert_youtube_comments(
    session: AsyncSession,
    *,
    rows: list[dict],
) -> int:
    """批量 UPSERT 评论，按 yt_comment_id 去重。"""
    if not rows:
        return 0

    stmt = mysql_insert(YouTubeComment.__table__).values(rows)
    stmt = stmt.on_duplicate_key_update(
        author_name=stmt.inserted.author_name,
        author_avatar=stmt.inserted.author_avatar,
        text_original=stmt.inserted.text_original,
        like_count=stmt.inserted.like_count,
        published_at=stmt.inserted.published_at,
        keyword_used=stmt.inserted.keyword_used,
    )
    await session.execute(stmt)
    await session.flush()
    return len(rows)


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

