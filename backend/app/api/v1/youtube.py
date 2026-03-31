from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.youtube import (
    ensure_competitor_pool,
    get_channel_histories_for_compare,
    list_user_competitor_channels,
    upsert_channel,
    upsert_channel_history,
    upsert_videos,
)
from app.models.youtube import YouTubeChannel, YouTubeVideo
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
    await upsert_channel_history(
        session=db,
        channel_id=channel.id,
        record_date=date.today(),
        subscriber_count=channel.subscriber_count,
        total_views=channel.total_views,
        video_count=channel.video_count,
    )
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


@router.get(
    "/competitors/compare",
    summary="获取监控频道历史对比数据",
)
async def competitors_compare(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    channel_ids: list[int] = Query(..., description="频道ID列表"),
    days: int = Query(30, ge=1, le=180, description="回溯天数"),
) -> list[dict]:
    # 权限过滤：只能比较当前用户监控池里的频道
    user_rows = await list_user_competitor_channels(db, current_user.id)
    allowed_ids = {row.channel_id for row in user_rows}
    filtered_ids = [cid for cid in channel_ids if cid in allowed_ids]
    if len(filtered_ids) < 1:
        raise HTTPException(status_code=400, detail="没有可对比的有效频道")

    channels_result = await db.execute(
        select(YouTubeChannel).where(YouTubeChannel.id.in_(filtered_ids))
    )
    channels = {c.id: c for c in channels_result.scalars().all()}
    start_date = date.today() - timedelta(days=days - 1)
    histories = await get_channel_histories_for_compare(
        db,
        channel_ids=filtered_ids,
        start_date=start_date,
    )

    # 输出格式示例：
    # [{"date":"2023-10-01","A_views":1000,"A_subscriber":100,...}, ...]
    result_map: dict[str, dict] = {}
    for row in histories:
        d = row.record_date.isoformat()
        if d not in result_map:
            result_map[d] = {"date": d}
        channel = channels.get(row.channel_id)
        if channel is None:
            continue
        key_base = channel.title.strip() or channel.yt_channel_id
        result_map[d][f"{key_base}_views"] = row.total_views
        result_map[d][f"{key_base}_subscriber_count"] = row.subscriber_count
        result_map[d][f"{key_base}_video_count"] = row.video_count

    return [result_map[k] for k in sorted(result_map.keys())]

