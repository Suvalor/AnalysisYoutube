"""频道相关独立路由（与 /api/youtube 解耦）。"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.youtube import YouTubeChannel, UserCompetitorPool
from app.schemas.discovery import (
    BlueOceanChannelItem,
    BlueOceanRadarRequest,
    BlueOceanRadarResponse,
    ChannelDetailResponse,
    ChannelDiscoverRequest,
    ChannelDiscoverResponse,
    DiscoverChannelItem,
    QuickTrackRequest,
    QuickTrackResponse,
)
from app.services.channel_cache_service import enrich_channels_with_cache, get_channel_detail_with_cache
from app.services.config_manager import resolve_integration_config
from app.services.quota_service import record_api_quota_usage
from app.services.youtube_service import blue_ocean_radar_scan, discover_channels_by_keyword, fetch_channel_info
from app.crud.youtube import ensure_competitor_pool, upsert_channel

router = APIRouter()


class AddChannelByIdRequest(BaseModel):
    """通过 channel_id 入库频道。"""
    channel_id: str = Field(..., min_length=1, max_length=64, description="YouTube 频道 ID")
    channel_title: str = Field("", max_length=255, description="频道标题")
    thumbnail_url: str | None = Field(None, description="缩略图 URL")
    subscriber_count: int = Field(0, description="订阅数")
    group_name: str = Field("默认分组", max_length=100, description="分组名称")

    @field_validator("channel_id")
    @classmethod
    def validate_channel_id_format(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("channel_id 仅允许字母、数字、下划线和连字符")
        return v


class AddChannelByIdResponse(BaseModel):
    success: bool
    message: str
    pool_id: int | None = None


@router.post(
    "/add-by-channel-id",
    response_model=AddChannelByIdResponse,
    summary="通过频道ID入库",
)
async def add_channel_by_id(
    body: AddChannelByIdRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> AddChannelByIdResponse:
    """
    通过 YouTube 频道 ID 直接入库到监控池。
    如果频道已存在则复用，不存在则创建。
    如果已在监控池中则返回提示。
    """
    # 查找或创建频道
    stmt = select(YouTubeChannel).where(YouTubeChannel.yt_channel_id == body.channel_id)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()

    if channel is None:
        channel = YouTubeChannel(
            yt_channel_id=body.channel_id,
            title=body.channel_title or body.channel_id,
            thumbnail_url=body.thumbnail_url,
            subscriber_count=body.subscriber_count,
        )
        db.add(channel)
        await db.flush()
    else:
        # 更新标题等信息（如果传入了）
        if body.channel_title and body.channel_title != channel.title:
            channel.title = body.channel_title
        if body.thumbnail_url:
            channel.thumbnail_url = body.thumbnail_url
        if body.subscriber_count > 0:
            channel.subscriber_count = body.subscriber_count
        await db.flush()

    # 检查是否已在监控池
    pool_stmt = select(UserCompetitorPool).where(
        UserCompetitorPool.user_id == current_user.id,
        UserCompetitorPool.channel_id == channel.id,
    )
    pool_result = await db.execute(pool_stmt)
    existing_pool = pool_result.scalar_one_or_none()

    if existing_pool:
        return AddChannelByIdResponse(
            success=True,
            message=f"频道「{channel.title}」已在监控池中",
            pool_id=existing_pool.id,
        )

    # 添加到监控池
    pool = await ensure_competitor_pool(
        session=db,
        user_id=current_user.id,
        channel_id=channel.id,
        group_name=body.group_name,
    )
    await db.commit()

    return AddChannelByIdResponse(
        success=True,
        message=f"频道「{channel.title}」已入库",
        pool_id=pool.id,
    )


@router.post(
    "/discover",
    response_model=ChannelDiscoverResponse,
    summary="潜力频道挖掘（仅查询，不落库）",
)
async def discover_channels(
    body: ChannelDiscoverRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ChannelDiscoverResponse:
    """
    调用 YouTube search.list（高配额）+ channels.list，按订阅上限过滤。
    成功后会记入当日 API 配额用量。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    result = await discover_channels_by_keyword(
        keyword=body.keyword,
        published_after_days=body.published_after,
        max_subscribers=body.max_subscribers,
        max_results=body.max_results,
        youtube_api_key=icfg.youtube_api_key,
    )
    if result.search_calls > 0:
        await record_api_quota_usage(db, "search", times=result.search_calls)
    if result.channels_list_calls > 0:
        await record_api_quota_usage(db, "channels", times=result.channels_list_calls, part_count=2)
    await db.commit()

    items = [DiscoverChannelItem.model_validate(x) for x in result.items]

    # 利用频道缓存批量增强搜索结果（补充 avatar_url、description 等字段）
    channel_ids = [item.yt_channel_id for item in items]
    if channel_ids:
        try:
            cache_map = await enrich_channels_with_cache(db, channel_ids, icfg.youtube_api_key)
            for item in items:
                cache_info = cache_map.get(item.yt_channel_id)
                if cache_info:
                    item.avatar_url = cache_info.get("avatar_url")
                    item.description = cache_info.get("description")
                    item.view_count = cache_info.get("view_count", 0)
                    item.published_at = cache_info.get("published_at")
                    item.country = cache_info.get("country")
                    item.custom_url = cache_info.get("custom_url")
                    item.cached = cache_info.get("cached", False)
        except Exception:
            # 缓存增强失败不影响主搜索结果返回
            pass

    return ChannelDiscoverResponse(items=items, warnings=result.warnings)


@router.get(
    "/discover/channels/{channel_id}",
    response_model=ChannelDetailResponse,
    summary="频道详情（优先缓存）",
)
async def get_channel_detail(
    channel_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ChannelDetailResponse:
    """
    获取频道详情，优先从缓存读取，未命中则调用 YouTube API 并写入缓存。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    try:
        detail = await get_channel_detail_with_cache(
            session=db,
            channel_id=channel_id,
            youtube_api_key=icfg.youtube_api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ChannelDetailResponse.model_validate(detail)


@router.post(
    "/blue-ocean-radar",
    response_model=BlueOceanRadarResponse,
    summary="蓝海雷达扫描（仅查询，不落库）",
)
async def blue_ocean_radar(
    body: BlueOceanRadarRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> BlueOceanRadarResponse:
    """
    蓝海雷达：搜索低粉丝但近期产出超级爆款的潜力对标频道。
    通过 search.list + videos.list + channels.list 三步策略，
    按 outlier_score (播放量/粉丝数) 筛选真正的蓝海爆款。
    结果仅查询不落库，用户需手动点击「入库关注」才会持久化。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    result = await blue_ocean_radar_scan(
        keyword=body.keyword,
        published_after_days=body.published_after,
        max_subscribers=body.max_subscribers,
        outlier_multiplier=body.outlier_multiplier,
        video_duration=body.video_duration,
        youtube_api_key=icfg.youtube_api_key,
    )

    if result.search_calls > 0:
        await record_api_quota_usage(db, "search", times=result.search_calls)
    if result.channels_list_calls > 0:
        await record_api_quota_usage(db, "channels", times=result.channels_list_calls)
    if result.videos_list_calls > 0:
        await record_api_quota_usage(db, "videos", times=result.videos_list_calls)
    await db.commit()

    items = [BlueOceanChannelItem.model_validate(x) for x in result.items]
    return BlueOceanRadarResponse(items=items, warnings=result.warnings)


@router.post(
    "/quick-track",
    response_model=QuickTrackResponse,
    summary="快速追踪博主（从视频列表一键入库）",
)
async def quick_track_channel(
    body: QuickTrackRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> QuickTrackResponse:
    """
    通过 YouTube 频道 ID 快速追踪博主。
    1. 调用 YouTube API 获取频道最新信息
    2. 更新或创建 YouTubeChannel 记录
    3. 添加到当前用户的监控池（如果尚未存在）
    """
    channel_id_str = body.channel_id.strip()

    # Step 1: 查找已有频道记录
    stmt = select(YouTubeChannel).where(YouTubeChannel.yt_channel_id == channel_id_str)
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()

    # Step 2: 如果频道不存在，调用 YouTube API 获取信息
    if channel is None:
        try:
            icfg = await resolve_integration_config(db, org_id=current_user.org_id)
            api_item = await fetch_channel_info(
                {"channel_id": channel_id_str},
                youtube_api_key=icfg.youtube_api_key,
            )
        except HTTPException:
            # YouTube API 不可用或频道不存在，用最小信息入库
            channel = YouTubeChannel(
                yt_channel_id=channel_id_str,
                title=channel_id_str,
            )
            db.add(channel)
            await db.flush()
        else:
            snippet = api_item.get("snippet", {})
            statistics = api_item.get("statistics", {})
            channel = YouTubeChannel(
                yt_channel_id=channel_id_str,
                title=snippet.get("title", "") or channel_id_str,
                description=snippet.get("description", "") or "",
                thumbnail_url=(snippet.get("thumbnails", {}).get("high", {}) or {}).get("url"),
                subscriber_count=int(statistics.get("subscriberCount", 0) or 0),
                total_views=int(statistics.get("viewCount", 0) or 0),
                video_count=int(statistics.get("videoCount", 0) or 0),
            )
            db.add(channel)
            await db.flush()
    else:
        # 频道已存在，尝试从 YouTube API 更新信息（best-effort）
        try:
            icfg = await resolve_integration_config(db, org_id=current_user.org_id)
            api_item = await fetch_channel_info(
                {"channel_id": channel_id_str},
                youtube_api_key=icfg.youtube_api_key,
            )
            snippet = api_item.get("snippet", {})
            statistics = api_item.get("statistics", {})
            new_title = snippet.get("title", "")
            if new_title:
                channel.title = new_title
            new_thumb = (snippet.get("thumbnails", {}).get("high", {}) or {}).get("url")
            if new_thumb:
                channel.thumbnail_url = new_thumb
            new_sub = int(statistics.get("subscriberCount", 0) or 0)
            if new_sub > 0:
                channel.subscriber_count = new_sub
            await db.flush()
        except HTTPException:
            # API 调用失败不影响入库流程
            pass

    # Step 3: 检查是否已在监控池
    pool_stmt = select(UserCompetitorPool).where(
        UserCompetitorPool.user_id == current_user.id,
        UserCompetitorPool.channel_id == channel.id,
    )
    pool_result = await db.execute(pool_stmt)
    existing_pool = pool_result.scalar_one_or_none()

    if existing_pool:
        return QuickTrackResponse(
            success=True,
            message=f"频道「{channel.title}」已在监控池中",
            pool_id=existing_pool.id,
            channel_title=channel.title,
        )

    # Step 4: 添加到监控池
    try:
        pool = await ensure_competitor_pool(
            session=db,
            user_id=current_user.id,
            channel_id=channel.id,
            group_name="全局视频列表",
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Channel already in tracking pool")

    return QuickTrackResponse(
        success=True,
        message=f"频道「{channel.title}」已入库追踪",
        pool_id=pool.id,
        channel_title=channel.title,
    )
