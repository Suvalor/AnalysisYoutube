"""频道相关独立路由（与 /api/youtube 解耦）。"""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.schemas.discovery import ChannelDiscoverRequest, ChannelDiscoverResponse, DiscoverChannelItem
from app.services.config_manager import resolve_integration_config
from app.services.quota_service import record_api_quota_usage
from app.services.youtube_service import discover_channels_by_keyword

router = APIRouter()


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
    return ChannelDiscoverResponse(items=items, warnings=result.warnings)
