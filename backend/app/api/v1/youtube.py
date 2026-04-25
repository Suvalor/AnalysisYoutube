from datetime import date, timedelta
from datetime import datetime, timezone
import mimetypes
import secrets
import tempfile
from urllib.parse import urlencode
import logging

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
import httpx
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.db.session import AsyncSessionLocal
from app.core.config import settings
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
    list_distinct_monitored_channels_for_org,
    query_videos,
    upsert_channel,
    upsert_channel_history,
    upsert_videos,
)
from app.crud.quota import get_quota_by_date, list_quota_recent_days
from app.models.youtube import YouTubeChannel, YouTubeComment, YouTubeVideo
from app.schemas.youtube import (
    CompetitorAiInsightRequest,
    CommentScrapeRequest,
    CommentScrapeResponse,
    QuotaDashboardResponse,
    UserCompetitorChannelItem,
    SubmitTaskResponse,
    YouTubeAnalyzeRequest,
    YouTubeAnalyzeResponse,
    YouTubeBatchAnalyzeRequest,
    YouTubeBatchAnalyzeResponse,
    YouTubeChannelAIAnalyzeResponse,
    YouTubeChannelAiAnalyzeRequest,
    YouTubeChannelRead,
    YouTubeVideoPageResponse,
    YouTubeVideoRead,
)
from app.schemas.youtube_oauth import (
    YouTubeOAuthCallbackRequest,
    YouTubeOAuthStatusResponse,
    YouTubeOAuthUrlResponse,
    YouTubePublishRequest,
    YouTubePublishResponse,
)
from app.services.field_encryption import encrypt_plaintext, try_decrypt
from app.services.youtube_channel_enrich import (
    channel_needs_ai_tag_fill,
    enrich_youtube_channel_ai,
    enrich_youtube_channel_ai_sync,
    enrich_youtube_channel_info_ai_sync,
    run_channel_detail_ai_analysis,
)
from app.services.youtube_service import (
    calc_recent_avg_views,
    fetch_channel_info,
    fetch_comment_threads_with_search,
    fetch_recent_videos,
    parse_datetime,
    parse_youtube_identifier,
    run_bulk_analyze_pipeline,
    run_refresh_pipeline_for_youtube_channel_ids,
    split_url_segments,
)
from app.services.quota_service import record_api_quota_usage, record_bulk_pipeline_quota
from app.services.config_manager import resolve_integration_config
from app.services.llm_conversation_service import (
    load_conversation_messages,
    save_conversation_turn,
)


router = APIRouter()
logger = logging.getLogger(__name__)


def _video_to_read(x: YouTubeVideo) -> YouTubeVideoRead:
    base = YouTubeVideoRead.model_validate(x)
    return base.model_copy(update={"tags": x.tags or []})


def _videos_to_read(rows: list[tuple[YouTubeVideo, bool]]) -> list[YouTubeVideoRead]:
    items: list[YouTubeVideoRead] = []
    for x, has_analysis in rows:
        ch = getattr(x, "channel", None)
        ch_title = ch.title if ch is not None else None
        base = _video_to_read(x)
        items.append(base.model_copy(update={"channel_title": ch_title, "has_analysis": has_analysis}))
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
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    identifier = parse_youtube_identifier(payload.youtube_url)
    item = await fetch_channel_info(identifier, youtube_api_key=icfg.youtube_api_key)
    await record_api_quota_usage(db, "channels", part_count=2)

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
        channel_id=channel_id,
        limit=10,
        youtube_api_key=icfg.youtube_api_key,
        return_quota=True,
    )
    await record_bulk_pipeline_quota(
        db,
        for_handle_calls=0,
        channels_list_calls=fr_quota.channels_calls,
        channels_part_count=1,
        playlist_items_calls=fr_quota.playlist_items_calls,
        playlist_items_part_count=1,
        videos_list_calls=fr_quota.videos_list_calls,
        videos_part_count=4,
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

    if await enrich_youtube_channel_ai(db, channel):
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


async def _process_analyze_youtube_batch_task(
    *,
    urls: list[str],
    group_name: str,
    user_id: int,
    org_id: int,
) -> None:
    """后台任务：批量添加关注（YouTube + AI 都在后台执行）。"""
    async with AsyncSessionLocal() as session:
        icfg = await resolve_integration_config(session, org_id=org_id)
        youtube_api_key = (icfg.youtube_api_key or "").strip()
        if not youtube_api_key:
            logger.warning("后台批量添加失败：未配置 YouTube Data API Key org_id=%s", org_id)
            return

        processed_count = 0
        for raw_url in urls:
            channel: YouTubeChannel | None = None
            try:
                identifier = parse_youtube_identifier(raw_url)
                item = await fetch_channel_info(identifier, youtube_api_key=youtube_api_key)

                await record_api_quota_usage(session, "channels", part_count=2)

                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                yt_channel_id = item.get("id", "") or ""
                if not yt_channel_id:
                    logger.warning("后台批量添加：未解析到频道 ID raw_url=%r", raw_url)
                    continue

                channel = await upsert_channel(
                    session=session,
                    yt_channel_id=yt_channel_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    thumbnail_url=(snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                    subscriber_count=int(statistics.get("subscriberCount", 0)),
                    total_views=int(statistics.get("viewCount", 0)),
                    video_count=int(statistics.get("videoCount", 0)),
                    published_at=parse_datetime(snippet.get("publishedAt")),
                )
                await session.commit()
                await session.refresh(channel)

                # AI 非流式打标签：失败也不应中断该 URL
                try:
                    await enrich_youtube_channel_info_ai_sync(session, channel, user_id=user_id)
                except Exception:  # noqa: BLE001
                    await session.rollback()
                    logger.exception("后台批量添加：AI 打标签失败 raw_url=%r", raw_url)

                recent_videos_raw, fr_quota = await fetch_recent_videos(
                    channel_id=yt_channel_id,
                    limit=10,
                    youtube_api_key=youtube_api_key,
                    return_quota=True,
                )

                _ = await record_bulk_pipeline_quota(
                    session,
                    for_handle_calls=0,
                    channels_list_calls=fr_quota.channels_calls,
                    channels_part_count=1,
                    playlist_items_calls=fr_quota.playlist_items_calls,
                    playlist_items_part_count=1,
                    videos_list_calls=fr_quota.videos_list_calls,
                    videos_part_count=4,
                )

                for video in recent_videos_raw:
                    video.setdefault("_parsed_published_at", parse_datetime(video.get("snippet", {}).get("publishedAt")))

                _ = await upsert_videos(
                    session=session,
                    channel_id=channel.id,
                    videos=recent_videos_raw,
                )

                await upsert_channel_history(
                    session=session,
                    channel_id=channel.id,
                    record_date=date.today(),
                    subscriber_count=channel.subscriber_count,
                    total_views=channel.total_views,
                    video_count=channel.video_count,
                )
                await ensure_competitor_pool(
                    session=session,
                    user_id=user_id,
                    channel_id=channel.id,
                    group_name=group_name,
                )

                # 强制更新时间戳：便于前端展示“后台已完成”的信号
                channel.updated_at = datetime.now(timezone.utc)
                await session.commit()
                processed_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("后台批量添加失败 raw_url=%r: %s", raw_url, exc)
                await session.rollback()
                continue

        logger.info(
            "后台批量添加任务完成 org_id=%s submitted_urls=%s processed=%s",
            org_id,
            len(urls),
            processed_count,
        )


async def _process_batch_update_channels_task(
    *,
    user_id: int,
    org_id: int,
) -> None:
    """后台任务：一键更新（YouTube + AI 都在后台执行）。"""
    async with AsyncSessionLocal() as session:
        icfg = await resolve_integration_config(session, org_id=org_id)
        youtube_api_key = (icfg.youtube_api_key or "").strip()
        if not youtube_api_key:
            logger.warning("后台一键更新失败：未配置 YouTube Data API Key org_id=%s", org_id)
            return

        channels = await list_distinct_monitored_channels_for_org(session, org_id)
        if not channels:
            logger.info("后台一键更新：org_id=%s 无监控频道", org_id)
            return

        yt_channel_ids = [c.yt_channel_id for c in channels]
        try:
            pipeline = await run_refresh_pipeline_for_youtube_channel_ids(
                yt_channel_ids,
                youtube_api_key=youtube_api_key,
            )

            await record_bulk_pipeline_quota(
                session,
                for_handle_calls=0,
                channels_list_calls=pipeline.channels_list_calls,
                channels_part_count=3,
                playlist_items_calls=pipeline.playlist_items_calls,
                playlist_items_part_count=1,
                videos_list_calls=pipeline.videos_list_calls,
                videos_part_count=4,
            )

            yt_to_db = await bulk_upsert_channels_from_api_items(session, pipeline.channel_items)
            _updated_videos = await bulk_upsert_videos_from_api_items(session, pipeline.video_items, yt_to_db)

            for item in pipeline.channel_items:
                yt_id = item.get("id")
                db_id = yt_to_db.get(yt_id or "")
                if not db_id:
                    continue
                statistics = item.get("statistics", {})
                await upsert_channel_history(
                    session=session,
                    channel_id=db_id,
                    record_date=date.today(),
                    subscriber_count=int(statistics.get("subscriberCount", 0)),
                    total_views=int(statistics.get("viewCount", 0)),
                    video_count=int(statistics.get("videoCount", 0)),
                )

            await session.commit()

            # 基础数据抓取完成：先把 updated_at 刷到“刚刚更新过”
            now = datetime.now(timezone.utc)
            for db_id in yt_to_db.values():
                ch = await session.get(YouTubeChannel, db_id)
                if ch is not None:
                    ch.updated_at = now
            await session.commit()

            # 再做 AI 补全：单频道失败不应影响其他频道
            monitored = await list_distinct_monitored_channels_for_org(session, org_id)
            for ch in monitored:
                if not channel_needs_ai_tag_fill(ch):
                    continue
                try:
                    await enrich_youtube_channel_info_ai_sync(session, ch, user_id=user_id)
                    ch.updated_at = datetime.now(timezone.utc)
                    await session.commit()
                except Exception:  # noqa: BLE001
                    await session.rollback()
                    ch.updated_at = datetime.now(timezone.utc)
                    await session.commit()

            logger.info("后台一键更新任务完成 org_id=%s", org_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("后台一键更新任务异常 org_id=%s: %s", org_id, exc)
            return


@router.post(
    "/analyze/batch",
    response_model=SubmitTaskResponse,
    summary="后台批量分析并导入 YouTube 频道（省流：无 Search API）",
    status_code=202,
)
async def analyze_youtube_batch(
    payload: YouTubeBatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SubmitTaskResponse:
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    urls = split_url_segments(payload.urls)
    if not urls:
        raise HTTPException(
            status_code=400,
            detail="urls 为空或解析失败：请使用分号（;）或换行分隔 YouTube 频道链接",
        )

    if not (icfg.youtube_api_key or "").strip():
        raise HTTPException(status_code=400, detail="未配置 YouTube Data API Key（检查设置中心或环境变量 YOUTUBE_API_KEY）")

    # 入队后台任务：控制器不再进行 YouTube/LLM 调用，避免 HTTP 超时
    background_tasks.add_task(
        _process_analyze_youtube_batch_task,
        urls=urls,
        group_name=payload.group_name,
        user_id=current_user.id,
        org_id=current_user.org_id,
    )
    return SubmitTaskResponse(code=200, message="任务已提交至后台处理，请稍后刷新查看。")


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
        org_id=current_user.org_id,
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

    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    parsed, api_calls = await fetch_comment_threads_with_search(
        video.yt_video_id,
        payload.keyword,
        youtube_api_key=icfg.youtube_api_key,
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
    summary="对频道执行 AI 深度洞察分析（配置中心模型 + 可选智能体）",
)
async def analyze_channel_ai(
    channel_id: int,
    body: YouTubeChannelAiAnalyzeRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubeChannelAIAnalyzeResponse:
    channel = await get_channel_for_user(db, user_id=current_user.id, channel_id=channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="频道不存在或无权访问")

    try:
        result = await run_channel_detail_ai_analysis(
            db,
            channel=channel,
            user_id=current_user.id,
            org_id=current_user.org_id,
            model_library_id=body.model_library_id,
            llm_model_name=body.llm_model_name.strip(),
            agent_id=body.agent_id,
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        logger.exception("AI 分析失败 channel_id=%s", channel_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 分析服务异常，请稍后重试",
        ) from exc

    await db.commit()
    await db.refresh(channel)

    # 保存对话记忆：频道 AI 分析结果
    try:
        await save_conversation_turn(
            db,
            user_id=current_user.id,
            entity_type="channel_ai",
            entity_id=str(channel_id),
            user_content=f"分析频道：{channel.title or channel.yt_channel_id}",
            assistant_content=str(result),
            model_name=result.get("llm_model_name"),
        )
        await db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("保存频道 AI 分析对话历史失败 channel_id=%s", channel_id)
        await db.rollback()

    return YouTubeChannelAIAnalyzeResponse(
        tags=result["tags"],
        expertise=result["expertise"],
        age_group=result["age_group"],
        summary=result["summary"],
        analyzed_at=result["analyzed_at"],
        model_library_id=result["model_library_id"],
        llm_model_name=result["llm_model_name"],
        agent_id=result["agent_id"],
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


@router.post("/channels/batch-update", response_model=SubmitTaskResponse, status_code=202)
async def batch_update_channels(
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SubmitTaskResponse:
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    channels = await list_distinct_monitored_channels_for_org(db, current_user.org_id)
    if not channels:
        return SubmitTaskResponse(code=200, message="没有需要更新的频道（已跳过）")

    if not (icfg.youtube_api_key or "").strip():
        raise HTTPException(status_code=400, detail="未配置 YouTube Data API Key（检查设置中心或环境变量 YOUTUBE_API_KEY）")

    background_tasks.add_task(
        _process_batch_update_channels_task,
        user_id=current_user.id,
        org_id=current_user.org_id,
    )
    return SubmitTaskResponse(code=200, message="一键更新任务已提交至后台处理，请稍后刷新查看。")


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


@router.post("/competitors/ai-insight", summary="AI 竞争格局分析")
async def competitors_ai_insight(
    body: CompetitorAiInsightRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """基于选中的频道数据，调用 LLM 生成竞争格局分析。"""
    from app.services.competitor_ai_service import generate_competitor_ai_insight
    from app.services.llm_conversation_service import load_conversation_messages, save_conversation_turn

    result = await generate_competitor_ai_insight(
        db,
        user_id=current_user.id,
        channel_ids=body.channel_ids,
        model_library_id=body.model_library_id,
        llm_model_name=body.llm_model_name,
        agent_id=body.agent_id,
    )

    # 保存对话历史
    entity_type = "competitor_insight"
    entity_id = ":".join(str(cid) for cid in sorted(body.channel_ids))
    if result.get("_user_prompt") and result.get("_assistant_content"):
        try:
            await save_conversation_turn(
                db,
                user_id=current_user.id,
                entity_type=entity_type,
                entity_id=entity_id,
                user_content=result["_user_prompt"],
                assistant_content=result["_assistant_content"],
                system_content=result.get("_system_prompt"),
                model_name=body.llm_model_name,
            )
            await db.commit()
        except Exception:  # noqa: BLE001
            import logging as _logging
            _logging.getLogger(__name__).exception("保存竞对洞察对话历史失败")
            await db.rollback()

    return {
        "insight": result.get("insight", {}),
        "conversation_id": f"{entity_type}:{entity_id}",
    }


@router.get("/oauth/url", response_model=YouTubeOAuthUrlResponse, summary="生成 Google OAuth 授权地址")
async def get_youtube_oauth_url(current_user: CurrentUserDep) -> YouTubeOAuthUrlResponse:
    _ = current_user
    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=500, detail="未配置 GOOGLE_OAUTH_CLIENT_ID")
    redirect_uri = (settings.google_oauth_redirect_uri or "").strip()
    if not redirect_uri:
        raise HTTPException(status_code=500, detail="未配置 GOOGLE_OAUTH_REDIRECT_URI")

    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
        "state": state,
        "include_granted_scopes": "true",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return YouTubeOAuthUrlResponse(auth_url=auth_url, state=state)


@router.post("/oauth/callback", response_model=YouTubeOAuthStatusResponse, summary="OAuth 回调后兑换并加密保存 token")
async def youtube_oauth_callback(
    payload: YouTubeOAuthCallbackRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubeOAuthStatusResponse:
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth 配置不完整")
    # 强制使用服务端配置的 redirect_uri，不接受客户端传入（防止开放重定向攻击）
    redirect_uri = (settings.google_oauth_redirect_uri or "").strip()
    if not redirect_uri:
        raise HTTPException(status_code=500, detail="服务端未配置 GOOGLE_OAUTH_REDIRECT_URI")

    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": payload.code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code >= 400:
            logger.warning("OAuth token 兑换失败 status=%s", token_resp.status_code)
            raise HTTPException(status_code=400, detail="OAuth token 兑换失败，请重新授权")
        token_data = token_resp.json()
        access_token = str(token_data.get("access_token") or "").strip()
        refresh_token = str(token_data.get("refresh_token") or "").strip()
        if not access_token:
            raise HTTPException(status_code=400, detail="未获取到 access_token")

        expires_in = int(token_data.get("expires_in") or 0)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in > 0 else None

        channel_id: str | None = None
        ch_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "id", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if ch_resp.status_code < 400:
            items = (ch_resp.json() or {}).get("items") or []
            if items and isinstance(items, list):
                channel_id = str((items[0] or {}).get("id") or "").strip() or None

    current_user.youtube_access_token_encrypted = encrypt_plaintext(access_token)
    if refresh_token:
        current_user.youtube_refresh_token_encrypted = encrypt_plaintext(refresh_token)
    current_user.youtube_token_expires_at = expires_at
    current_user.youtube_channel_id = channel_id
    # OAuth 回调中调用了 channels.list(mine=true)，记录配额消耗
    await record_api_quota_usage(db, "channels", part_count=1)
    await db.commit()
    await db.refresh(current_user)

    return YouTubeOAuthStatusResponse(
        connected=bool(current_user.youtube_access_token_encrypted),
        channel_id=current_user.youtube_channel_id,
        expires_at=current_user.youtube_token_expires_at,
    )


@router.get("/oauth/status", response_model=YouTubeOAuthStatusResponse, summary="YouTube OAuth 连接状态")
async def youtube_oauth_status(current_user: CurrentUserDep) -> YouTubeOAuthStatusResponse:
    return YouTubeOAuthStatusResponse(
        connected=bool(current_user.youtube_access_token_encrypted),
        channel_id=current_user.youtube_channel_id,
        expires_at=current_user.youtube_token_expires_at,
    )


@router.post("/publish", response_model=YouTubePublishResponse, summary="发布视频到 YouTube")
async def youtube_publish(
    payload: YouTubePublishRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubePublishResponse:
    if not payload.media_url.strip():
        raise HTTPException(status_code=422, detail="media_url 不能为空")
    access_token = await _get_valid_youtube_access_token(db, current_user)
    if not access_token:
        raise HTTPException(status_code=400, detail="请先完成 YouTube OAuth 授权")

    async with httpx.AsyncClient(timeout=120.0, trust_env=False, follow_redirects=True) as client:
        media_resp = await client.get(payload.media_url)
        if media_resp.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"媒体下载失败: {media_resp.status_code}")

        content_type = (
            str(media_resp.headers.get("content-type") or "").split(";")[0].strip()
            or mimetypes.guess_type(payload.media_url)[0]
            or "video/mp4"
        )

        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            written = 0
            async for chunk in media_resp.aiter_bytes(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                tmp_file.write(chunk)
                written += len(chunk)
            if written <= 0:
                raise HTTPException(status_code=400, detail="媒体内容为空，无法发布")
            tmp_file.flush()

            init_resp = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos",
                params={"uploadType": "resumable", "part": "snippet,status"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Length": str(written),
                    "X-Upload-Content-Type": content_type,
                },
                json={
                    "snippet": {
                        "title": payload.title,
                        "description": payload.description,
                    },
                    "status": {
                        "privacyStatus": payload.privacy_status,
                    },
                },
            )
            if init_resp.status_code >= 400:
                raise HTTPException(status_code=400, detail=f"创建上传会话失败: {init_resp.text}")
            upload_url = str(init_resp.headers.get("Location") or "").strip()
            if not upload_url:
                raise HTTPException(status_code=400, detail="未获取到 YouTube 上传会话地址")

            chunk_size = 8 * 1024 * 1024
            start = 0
            video_id: str | None = None
            tmp_file.seek(0)
            while start < written:
                data_chunk = tmp_file.read(min(chunk_size, written - start))
                if not data_chunk:
                    break
                end = start + len(data_chunk) - 1
                upload_resp = await client.put(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": content_type,
                        "Content-Length": str(len(data_chunk)),
                        "Content-Range": f"bytes {start}-{end}/{written}",
                    },
                    content=data_chunk,
                )
                # 308 表示分块续传中，最终分片会返回 200/201。
                if upload_resp.status_code == 308:
                    start = end + 1
                    continue
                if upload_resp.status_code >= 400:
                    raise HTTPException(status_code=400, detail=f"上传视频失败: {upload_resp.text}")
                data = upload_resp.json() if upload_resp.text else {}
                video_id = str(data.get("id") or "").strip() or None
                start = end + 1

            if not video_id:
                raise HTTPException(status_code=400, detail="上传完成但未返回 video_id")

    return YouTubePublishResponse(status="published", video_id=video_id, message="已成功发布到 YouTube")


async def _get_valid_youtube_access_token(db: DBSessionDep, current_user: CurrentUserDep) -> str | None:
    access_token = try_decrypt(current_user.youtube_access_token_encrypted)
    now = datetime.now(timezone.utc)
    expires_at = current_user.youtube_token_expires_at
    if access_token and (expires_at is None or expires_at > now + timedelta(seconds=60)):
        return access_token

    refresh_token = try_decrypt(current_user.youtube_refresh_token_encrypted)
    if not refresh_token:
        return access_token
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth 配置不完整，无法刷新 token")

    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"刷新 access_token 失败: {resp.text}")
        token_data = resp.json()
        new_access = str(token_data.get("access_token") or "").strip()
        if not new_access:
            raise HTTPException(status_code=400, detail="刷新 token 成功但未返回 access_token")
        expires_in = int(token_data.get("expires_in") or 0)

    current_user.youtube_access_token_encrypted = encrypt_plaintext(new_access)
    if expires_in > 0:
        current_user.youtube_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    await db.commit()
    await db.refresh(current_user)
    return new_access

