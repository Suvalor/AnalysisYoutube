from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.youtube import (
    bulk_upsert_channels_from_api_items,
    bulk_upsert_videos_from_api_items,
    bulk_upsert_youtube_comments,
    delete_user_competitor_channel,
    ensure_competitor_pool,
    get_channel_for_user,
    get_channel_histories_for_compare,
    get_video_for_user,
    list_user_competitor_channels,
    list_distinct_monitored_channels,
    query_videos,
    update_channel_ai_insight,
    upsert_channel,
    upsert_channel_history,
    upsert_videos,
)
from app.crud.quota import get_quota_by_date, list_quota_recent_days
from app.models.youtube import YouTubeChannel, YouTubeComment, YouTubeVideo
from app.schemas.youtube import (
    CommentScrapeRequest,
    CommentScrapeResponse,
    QuotaDashboardResponse,
    UserCompetitorChannelItem,
    YouTubeAnalyzeRequest,
    YouTubeAnalyzeResponse,
    YouTubeBatchAnalyzeRequest,
    YouTubeBatchAnalyzeResponse,
    YouTubeChannelAIAnalyzeResponse,
    YouTubeChannelRead,
    YouTubeVideoPageResponse,
    YouTubeVideoRead,
)
from app.services.youtube_ai_service import analyze_channel_ai_insight, build_channel_ai_messages
from app.services.youtube_service import (
    calc_recent_avg_views,
    fetch_channel_info,
    fetch_comment_threads_with_search,
    fetch_recent_videos,
    parse_datetime,
    parse_youtube_identifier,
    run_bulk_analyze_pipeline,
    run_refresh_pipeline_for_youtube_channel_ids,
)
from app.services.quota_service import record_api_quota_usage, record_bulk_pipeline_quota


router = APIRouter()


def _video_to_read(x: YouTubeVideo) -> YouTubeVideoRead:
    base = YouTubeVideoRead.model_validate(x)
    return base.model_copy(update={"tags": x.tags or []})


def _videos_to_read(rows: list[YouTubeVideo]) -> list[YouTubeVideoRead]:
    items: list[YouTubeVideoRead] = []
    for x in rows:
        ch = getattr(x, "channel", None)
        ch_title = ch.title if ch is not None else None
        base = _video_to_read(x)
        items.append(base.model_copy(update={"channel_title": ch_title}))
    return items


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
    await record_api_quota_usage(db, "channels")

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

    recent_videos_raw, fr_quota = await fetch_recent_videos(
        channel_id=channel_id, limit=10, return_quota=True
    )
    await record_bulk_pipeline_quota(
        db,
        for_handle_calls=0,
        channels_list_calls=fr_quota.channels_calls,
        playlist_items_calls=fr_quota.playlist_items_calls,
        videos_list_calls=fr_quota.videos_list_calls,
    )
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
        videos=[_video_to_read(v) for v in videos],
    )


@router.post(
    "/analyze/batch",
    response_model=YouTubeBatchAnalyzeResponse,
    summary="批量分析并导入 YouTube 频道（省流：无 Search API）",
)
async def analyze_youtube_batch(
    payload: YouTubeBatchAnalyzeRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubeBatchAnalyzeResponse:
    pipeline = await run_bulk_analyze_pipeline(payload.urls)
    if not pipeline.channel_items:
        raise HTTPException(
            status_code=400,
            detail="; ".join(pipeline.errors) if pipeline.errors else "未能获取任何频道数据",
        )

    quota_used = await record_bulk_pipeline_quota(
        db,
        for_handle_calls=pipeline.for_handle_calls,
        channels_list_calls=pipeline.channels_list_calls,
        playlist_items_calls=pipeline.playlist_items_calls,
        videos_list_calls=pipeline.videos_list_calls,
    )

    yt_to_db = await bulk_upsert_channels_from_api_items(db, pipeline.channel_items)
    videos_count = await bulk_upsert_videos_from_api_items(
        db, pipeline.video_items, yt_to_db
    )

    for item in pipeline.channel_items:
        yt_id = item.get("id")
        db_id = yt_to_db.get(yt_id or "")
        if not db_id:
            continue
        statistics = item.get("statistics", {})
        await upsert_channel_history(
            session=db,
            channel_id=db_id,
            record_date=date.today(),
            subscriber_count=int(statistics.get("subscriberCount", 0)),
            total_views=int(statistics.get("viewCount", 0)),
            video_count=int(statistics.get("videoCount", 0)),
        )
        await ensure_competitor_pool(
            session=db,
            user_id=current_user.id,
            channel_id=db_id,
            group_name=payload.group_name,
        )

    await db.commit()

    return YouTubeBatchAnalyzeResponse(
        channels_count=len(yt_to_db),
        videos_count=videos_count,
        quota_used=quota_used,
        errors=pipeline.errors,
    )


@router.get("/quota-dashboard", response_model=QuotaDashboardResponse)
async def quota_dashboard(db: DBSessionDep, current_user: CurrentUserDep) -> QuotaDashboardResponse:
    _ = current_user
    today_total = 10000
    today_row = await get_quota_by_date(db, date.today())
    today_used = int(today_row.points_used if today_row else 0)
    history_rows = await list_quota_recent_days(db, 7)
    history = [{"date": r.record_date.isoformat(), "points_used": int(r.points_used)} for r in history_rows]
    return QuotaDashboardResponse(
        today_total=today_total,
        today_used=today_used,
        today_remaining=max(0, today_total - today_used),
        history=history,
    )


async def _list_videos_impl(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    *,
    keyword: str | None,
    start_date: str | None,
    end_date: str | None,
    min_duration: int | None,
    max_duration: int | None,
    channel_id: int | None,
    definition: str | None,
    privacy_status: str | None,
    min_view_count: int | None,
    max_view_count: int | None,
    min_like_count: int | None,
    max_like_count: int | None,
    min_comment_count: int | None,
    max_comment_count: int | None,
    sort_by: str,
    publish_time_sort: str | None,
    view_count_sort: str | None,
    like_count_sort: str | None,
    comment_count_sort: str | None,
    page: int,
    page_size: int,
) -> YouTubeVideoPageResponse:
    start_dt = None
    end_dt = None
    if start_date:
        start_dt = parse_datetime(f"{start_date}T00:00:00Z")
    if end_date:
        end_dt = parse_datetime(f"{end_date}T23:59:59Z")
    rows, total = await query_videos(
        db,
        user_id=current_user.id,
        keyword=keyword,
        start_date=start_dt,
        end_date=end_dt,
        min_duration=min_duration,
        max_duration=max_duration,
        channel_id=channel_id,
        definition=definition,
        privacy_status=privacy_status,
        min_view_count=min_view_count,
        max_view_count=max_view_count,
        min_like_count=min_like_count,
        max_like_count=max_like_count,
        min_comment_count=min_comment_count,
        max_comment_count=max_comment_count,
        sort_by=sort_by,
        publish_time_sort=publish_time_sort,
        view_count_sort=view_count_sort,
        like_count_sort=like_count_sort,
        comment_count_sort=comment_count_sort,
        page=page,
        page_size=page_size,
    )
    return YouTubeVideoPageResponse(
        items=_videos_to_read(rows),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/videos/all",
    response_model=YouTubeVideoPageResponse,
    summary="跨频道全局视频列表（与 /videos 同参，语义明确）",
)
async def list_videos_all(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    keyword: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    min_duration: int | None = Query(None),
    max_duration: int | None = Query(None),
    channel_id: int | None = Query(None),
    definition: str | None = Query(None),
    privacy_status: str | None = Query(None),
    min_view_count: int | None = Query(None),
    max_view_count: int | None = Query(None),
    min_like_count: int | None = Query(None),
    max_like_count: int | None = Query(None),
    min_comment_count: int | None = Query(None),
    max_comment_count: int | None = Query(None),
    sort_by: str = Query("publish_time_desc"),
    publish_time_sort: str | None = Query(None, description="asc/desc，与多列排序；未传则按 sort_by 或与其它列组合"),
    view_count_sort: str | None = Query(None),
    like_count_sort: str | None = Query(None),
    comment_count_sort: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> YouTubeVideoPageResponse:
    return await _list_videos_impl(
        db,
        current_user,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        min_duration=min_duration,
        max_duration=max_duration,
        channel_id=channel_id,
        definition=definition,
        privacy_status=privacy_status,
        min_view_count=min_view_count,
        max_view_count=max_view_count,
        min_like_count=min_like_count,
        max_like_count=max_like_count,
        min_comment_count=min_comment_count,
        max_comment_count=max_comment_count,
        sort_by=sort_by,
        publish_time_sort=publish_time_sort,
        view_count_sort=view_count_sort,
        like_count_sort=like_count_sort,
        comment_count_sort=comment_count_sort,
        page=page,
        page_size=page_size,
    )


@router.get("/videos", response_model=YouTubeVideoPageResponse)
async def list_videos(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    keyword: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    min_duration: int | None = Query(None),
    max_duration: int | None = Query(None),
    channel_id: int | None = Query(None),
    definition: str | None = Query(None),
    privacy_status: str | None = Query(None),
    min_view_count: int | None = Query(None),
    max_view_count: int | None = Query(None),
    min_like_count: int | None = Query(None),
    max_like_count: int | None = Query(None),
    min_comment_count: int | None = Query(None),
    max_comment_count: int | None = Query(None),
    sort_by: str = Query("publish_time_desc"),
    publish_time_sort: str | None = Query(None, description="asc/desc，与多列排序；未传则按 sort_by 或与其它列组合"),
    view_count_sort: str | None = Query(None),
    like_count_sort: str | None = Query(None),
    comment_count_sort: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> YouTubeVideoPageResponse:
    return await _list_videos_impl(
        db,
        current_user,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        min_duration=min_duration,
        max_duration=max_duration,
        channel_id=channel_id,
        definition=definition,
        privacy_status=privacy_status,
        min_view_count=min_view_count,
        max_view_count=max_view_count,
        min_like_count=min_like_count,
        max_like_count=max_like_count,
        min_comment_count=min_comment_count,
        max_comment_count=max_comment_count,
        sort_by=sort_by,
        publish_time_sort=publish_time_sort,
        view_count_sort=view_count_sort,
        like_count_sort=like_count_sort,
        comment_count_sort=comment_count_sort,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/videos/{video_id}/comments/scrape",
    response_model=CommentScrapeResponse,
    summary="按关键字定向抓取评论（commentThreads + searchTerms）",
)
async def scrape_video_comments(
    video_id: int,
    payload: CommentScrapeRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> CommentScrapeResponse:
    video = await get_video_for_user(db, user_id=current_user.id, video_id=video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="视频不存在或无权访问")

    parsed, api_calls = await fetch_comment_threads_with_search(
        video.yt_video_id,
        payload.keyword,
        max_total=100,
    )
    quota_used = await record_api_quota_usage(db, "commentThreads", times=api_calls)

    rows: list[dict] = []
    for row in parsed:
        rows.append(
            {
                "yt_comment_id": row["yt_comment_id"],
                "video_id": video.id,
                "channel_id": video.channel_id,
                "author_name": row["author_name"],
                "author_avatar": row["author_avatar"],
                "text_original": row["text_original"],
                "like_count": row["like_count"],
                "published_at": parse_datetime(row.get("published_at_raw")),
                "keyword_used": payload.keyword.strip(),
            }
        )

    await bulk_upsert_youtube_comments(db, rows=rows)
    await db.commit()

    return CommentScrapeResponse(scraped_count=len(rows), quota_used=quota_used)


@router.get(
    "/channels/detail/{channel_id}",
    response_model=YouTubeChannelRead,
    summary="获取单个监控频道详情（数据库 channel 主键）",
)
async def get_channel_detail(
    channel_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubeChannelRead:
    ch = await get_channel_for_user(db, user_id=current_user.id, channel_id=channel_id)
    if ch is None:
        raise HTTPException(status_code=404, detail="频道不存在或无权访问")
    return YouTubeChannelRead.model_validate(ch)


@router.post(
    "/channels/{channel_id}/ai-analyze",
    response_model=YouTubeChannelAIAnalyzeResponse,
    summary="对频道执行 AI 深度洞察分析",
)
async def analyze_channel_ai(
    channel_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubeChannelAIAnalyzeResponse:
    channel = await get_channel_for_user(db, user_id=current_user.id, channel_id=channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="频道不存在或无权访问")

    top_videos_query = await db.execute(
        select(YouTubeVideo)
        .where(YouTubeVideo.channel_id == channel.id)
        .order_by(YouTubeVideo.view_count.desc())
        .limit(10)
    )
    top_videos = list(top_videos_query.scalars().all())
    top_video_titles = [x.title for x in top_videos if x.title]

    merged_tags: list[str] = []
    seen_tags: set[str] = set()
    for video in top_videos:
        for tag in video.tags or []:
            t = str(tag).strip()
            if not t or t in seen_tags:
                continue
            seen_tags.add(t)
            merged_tags.append(t)
    merged_tags = merged_tags[:80]

    comments_query = await db.execute(
        select(YouTubeComment.text_original)
        .where(YouTubeComment.channel_id == channel.id)
        .order_by(YouTubeComment.like_count.desc(), YouTubeComment.created_at.desc())
        .limit(20)
    )
    hot_comments = [str(x[0]).strip() for x in comments_query.all() if x and str(x[0]).strip()]

    messages = build_channel_ai_messages(
        channel_title=channel.title,
        channel_description=channel.description,
        top_video_titles=top_video_titles,
        merged_tags=merged_tags,
        hot_comments=hot_comments,
    )
    ai_result = await analyze_channel_ai_insight(messages)

    await update_channel_ai_insight(
        db,
        channel=channel,
        ai_tags=list(ai_result["tags"]) if isinstance(ai_result.get("tags"), list) else [],
        ai_audience_age=str(ai_result["age_group"]),
        ai_summary=str(ai_result["summary"]),
    )
    await db.commit()

    return YouTubeChannelAIAnalyzeResponse(
        tags=channel.ai_tags or [],
        age_group=channel.ai_audience_age or "",
        summary=channel.ai_summary or "",
    )


@router.get(
    "/channels",
    response_model=list[UserCompetitorChannelItem],
    summary="获取当前用户监控池频道",
)
async def list_channels(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    sort_by: str = Query(
        "added_desc",
        description="排序：subscriber_desc/asc, total_views_desc/asc, video_count_desc/asc, added_desc",
    ),
) -> list[UserCompetitorChannelItem]:
    rows = await list_user_competitor_channels(db, current_user.id, sort_by=sort_by)
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


@router.delete("/channels/{pool_id}")
async def delete_channel_from_pool(
    pool_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    ok = await delete_user_competitor_channel(db, user_id=current_user.id, pool_id=pool_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.commit()
    return {"success": True}


@router.post("/channels/batch-update")
async def batch_update_channels(
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    _ = current_user
    channels = await list_distinct_monitored_channels(db)
    if not channels:
        return {"estimated_points": 0, "updated_channels": 0, "updated_videos": 0, "quota_used": 0}

    n = len(channels)
    # 最坏情况：channels 分块 + 每频道 playlistItems + 视频按 50 分块
    estimated_points = (n + 49) // 50 + 2 * n

    pipeline = await run_refresh_pipeline_for_youtube_channel_ids([c.yt_channel_id for c in channels])

    quota_used = await record_bulk_pipeline_quota(
        db,
        for_handle_calls=0,
        channels_list_calls=pipeline.channels_list_calls,
        playlist_items_calls=pipeline.playlist_items_calls,
        videos_list_calls=pipeline.videos_list_calls,
    )

    yt_to_db = await bulk_upsert_channels_from_api_items(db, pipeline.channel_items)
    updated_videos = await bulk_upsert_videos_from_api_items(db, pipeline.video_items, yt_to_db)

    for item in pipeline.channel_items:
        yt_id = item.get("id")
        db_id = yt_to_db.get(yt_id or "")
        if not db_id:
            continue
        statistics = item.get("statistics", {})
        await upsert_channel_history(
            session=db,
            channel_id=db_id,
            record_date=date.today(),
            subscriber_count=int(statistics.get("subscriberCount", 0)),
            total_views=int(statistics.get("viewCount", 0)),
            video_count=int(statistics.get("videoCount", 0)),
        )

    await db.commit()
    return {
        "estimated_points": estimated_points,
        "updated_channels": len(yt_to_db),
        "updated_videos": updated_videos,
        "quota_used": quota_used,
    }


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

