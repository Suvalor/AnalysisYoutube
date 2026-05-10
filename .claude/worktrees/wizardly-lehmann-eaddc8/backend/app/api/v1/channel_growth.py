"""频道增长仪表盘 API 路由。"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.youtube import YouTubeChannelHistory, UserCompetitorPool
from app.schemas.channel_growth import (
    ChannelGrowthRequest,
    ChannelGrowthMetrics,
    ChannelGrowthSummary,
    ChannelGrowthResponse,
    GrowthDataPoint,
)
from app.services.channel_growth_service import get_channel_growth_data
from app.services.config_manager import resolve_integration_config
from app.services.quota_service import record_api_quota_usage

router = APIRouter()

CHANNEL_GROWTH_CACHE_TTL = timedelta(hours=12)


async def _is_channel_growth_cache_valid(db, user_id: int) -> bool:
    """检查频道增长数据是否在12小时内已更新（基于今日历史记录的 created_at）。"""
    from app.models.youtube import YouTubeChannel, YouTubeChannelHistory as Hist

    # 获取用户监控池中的频道
    pool_stmt = select(UserCompetitorPool.channel_id).where(
        UserCompetitorPool.user_id == user_id
    )
    pool_result = await db.execute(pool_stmt)
    channel_ids = [r[0] for r in pool_result.all()]

    if not channel_ids:
        return False

    # 检查今日是否有历史记录，且 created_at 在12小时内
    from datetime import date
    today = date.today()
    hist_stmt = select(func.max(YouTubeChannelHistory.created_at)).where(
        YouTubeChannelHistory.channel_id.in_(channel_ids),
        YouTubeChannelHistory.record_date == today,
    )
    result = await db.execute(hist_stmt)
    latest_created = result.scalar_one_or_none()
    if latest_created is None:
        return False
    now = datetime.now(timezone.utc)
    if latest_created.tzinfo is None:
        latest_created = latest_created.replace(tzinfo=timezone.utc)
    return (now - latest_created) < CHANNEL_GROWTH_CACHE_TTL


@router.post(
    "/dashboard",
    response_model=ChannelGrowthResponse,
    summary="频道增长仪表盘",
)
async def channel_growth_dashboard(
    body: ChannelGrowthRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ChannelGrowthResponse:
    """
    获取频道增长仪表盘数据。
    12小时内复用缓存，不重复调用 YouTube API。
    """
    # 检查缓存
    cache_valid = await _is_channel_growth_cache_valid(db, current_user.id)
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    youtube_api_key = icfg.youtube_api_key if not cache_valid else None

    result = await get_channel_growth_data(
        db,
        user_id=current_user.id,
        channel_ids=body.channel_ids,
        days=body.days,
        youtube_api_key=youtube_api_key,
    )

    # 仅在非缓存命中时记录配额
    if not cache_valid and result.get("quota_used", 0) > 0:
        await record_api_quota_usage(db, "channels", times=result["quota_used"], part_count=1)
        await db.commit()

    # 构建响应
    channels = [
        ChannelGrowthMetrics(
            pool_id=c["pool_id"],
            channel_id=c["channel_id"],
            title=c["title"],
            thumbnail_url=c["thumbnail_url"],
            current_subscribers=c["current_subscribers"],
            current_views=c["current_views"],
            current_videos=c["current_videos"],
            subscriber_growth_rate=c["subscriber_growth_rate"],
            view_growth_rate=c["view_growth_rate"],
            avg_views_per_video=c["avg_views_per_video"],
            engagement_score=c["engagement_score"],
            growth_trend=c["growth_trend"],
            growth_data=[
                GrowthDataPoint(
                    date=g["date"],
                    subscribers=g["subscribers"],
                    views=g["views"],
                    videos=g["videos"],
                )
                for g in c["growth_data"]
            ],
        )
        for c in result["channels"]
    ]

    summary = ChannelGrowthSummary(**result["summary"])

    return ChannelGrowthResponse(
        channels=channels,
        summary=summary,
        quota_used=result.get("quota_used", 0),
    )
