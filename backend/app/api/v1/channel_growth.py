"""频道增长仪表盘 API 路由。"""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
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

    - 从监控池获取频道信息
    - 从 YouTubeChannelHistory 获取历史趋势
    - 调用 YouTube Data API 获取最新统计
    - 计算增长率、趋势、互动得分
    """
    # 解析 YouTube API Key
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)

    result = await get_channel_growth_data(
        db,
        user_id=current_user.id,
        channel_ids=body.channel_ids,
        days=body.days,
        youtube_api_key=icfg.youtube_api_key,
    )

    # 记录配额消耗
    quota_used = result.get("quota_used", 0)
    if quota_used > 0:
        await record_api_quota_usage(db, "channels", times=quota_used, part_count=1)
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
        quota_used=quota_used,
    )
