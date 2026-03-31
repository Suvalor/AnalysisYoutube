from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.quota import add_quota_points

API_POINTS = {
    "channels": 1,
    "search": 100,
    "videos": 1,
    "playlistItems": 1,
    "commentThreads": 1,
}


async def record_api_quota_usage(session: AsyncSession, api_name: str, times: int = 1) -> int:
    points = API_POINTS.get(api_name, 0) * max(1, times)
    if points > 0:
        await add_quota_points(session, points)
    return points


async def record_bulk_pipeline_quota(
    session: AsyncSession,
    *,
    for_handle_calls: int,
    channels_list_calls: int,
    playlist_items_calls: int,
    videos_list_calls: int,
) -> int:
    """
    批量流水线配额入账（forHandle 与 channels.list 均计为 channels 类型，各 1 点/次）。
    返回本次合计点数。
    """
    total = 0
    ch_times = max(0, for_handle_calls) + max(0, channels_list_calls)
    if ch_times > 0:
        total += await record_api_quota_usage(session, "channels", times=ch_times)
    if playlist_items_calls > 0:
        total += await record_api_quota_usage(session, "playlistItems", times=playlist_items_calls)
    if videos_list_calls > 0:
        total += await record_api_quota_usage(session, "videos", times=videos_list_calls)
    return total

