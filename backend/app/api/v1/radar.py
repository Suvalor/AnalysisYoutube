"""蓝海雷达 API（仅查询 YouTube，不落库）。"""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.schemas.radar import BlueOceanChannelItem, BlueOceanRadarRequest, BlueOceanRadarResponse
from app.services.config_manager import resolve_integration_config
from app.services.quota_service import record_api_quota_usage
from app.services.youtube_service import blue_ocean_radar_scan

router = APIRouter()


@router.post(
    "/scan",
    response_model=BlueOceanRadarResponse,
    summary="蓝海雷达深度扫描（仅查询，不落库）",
)
async def blue_ocean_scan(
    body: BlueOceanRadarRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> BlueOceanRadarResponse:
    """
    调用 YouTube search.list + videos.list + channels.list，按粉丝上限与爆款系数过滤。
    成功后会记入当日 API 配额用量。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    vd = body.video_duration
    result = await blue_ocean_radar_scan(
        keyword=body.keyword,
        published_after_days=body.published_after,
        max_subscribers=body.max_subscribers,
        outlier_multiplier=body.outlier_multiplier,
        youtube_api_key=icfg.youtube_api_key,
        video_duration=vd,
    )
    if result.search_calls > 0:
        await record_api_quota_usage(db, "search", times=result.search_calls)
    if result.videos_list_calls > 0:
        await record_api_quota_usage(db, "videos", times=result.videos_list_calls)
    if result.channels_list_calls > 0:
        await record_api_quota_usage(db, "channels", times=result.channels_list_calls)
    await db.commit()

    items = [BlueOceanChannelItem.model_validate(x) for x in result.items]
    return BlueOceanRadarResponse(items=items, warnings=result.warnings)
