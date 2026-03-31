from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.youtube import ensure_competitor_pool, list_user_competitor_channels, upsert_channel, upsert_videos
from app.models.youtube import YouTubeVideo
from app.schemas.youtube import (
    UserCompetitorChannelItem,
    YouTubeAnalyzeRequest,
    YouTubeAnalyzeResponse,
    YouTubeChannelRead,
    YouTubeVideoRead,
)
from app.services.youtube_service import (
    calc_recent_avg_views,
    fetch_channel_info,
    fetch_recent_videos,
    parse_datetime,
    parse_youtube_identifier,
)


router = APIRouter()

@router.post(
    "/analyze",
    response_model=YouTubeAnalyzeResponse,
    summary="分析并导入 YouTube 频道",
)
async def analyze_youtube_channel(
    payload: YouTubeAnalyzeRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubeAnalyzeResponse:
    identifier = parse_youtube_identifier(payload.youtube_url)
    item = await fetch_channel_info(identifier)

    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})
    channel_id = item.get("id", "")

    channel = await upsert_channel(
        session=db,
        yt_channel_id=channel_id,
        title=snippet.get("title", ""),
        description=snippet.get("description", ""),
        thumbnail_url=(snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
        subscriber_count=int(statistics.get("subscriberCount", 0)),
        total_views=int(statistics.get("viewCount", 0)),
        video_count=int(statistics.get("videoCount", 0)),
        published_at=parse_datetime(snippet.get("publishedAt")),
    )

    recent_videos_raw = await fetch_recent_videos(channel_id=channel_id, limit=10)
    for video in recent_videos_raw:
        video.setdefault("_parsed_published_at", parse_datetime(video.get("snippet", {}).get("publishedAt")))

    await upsert_videos(session=db, channel_id=channel.id, videos=recent_videos_raw)
    await ensure_competitor_pool(
        session=db,
        user_id=current_user.id,
        channel_id=channel.id,
        group_name=payload.group_name,
    )
    await db.commit()
    await db.refresh(channel)

    videos_query = await db.execute(
        select(YouTubeVideo)
        .where(YouTubeVideo.channel_id == channel.id)
        .order_by(YouTubeVideo.published_at.desc())
        .limit(10)
    )
    videos = list(videos_query.scalars().all())
    return YouTubeAnalyzeResponse(
        channel=YouTubeChannelRead.model_validate(channel),
        recent_avg_views=calc_recent_avg_views(recent_videos_raw),
        videos=[YouTubeVideoRead.model_validate(v) for v in videos],
    )


@router.get(
    "/channels",
    response_model=list[UserCompetitorChannelItem],
    summary="获取当前用户监控池频道",
)
async def list_channels(
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> list[UserCompetitorChannelItem]:
    rows = await list_user_competitor_channels(db, current_user.id)
    results: list[UserCompetitorChannelItem] = []
    for row in rows:
        results.append(
            UserCompetitorChannelItem(
                pool_id=row.id,
                group_name=row.group_name,
                added_at=row.added_at,
                channel=YouTubeChannelRead.model_validate(row.channel),
            )
        )
    return results

