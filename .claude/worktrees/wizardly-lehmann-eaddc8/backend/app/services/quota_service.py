"""YouTube API 配额追踪服务。

配额计算规则（参考 YouTube 官方配额计算器）：
https://developers.google.com/youtube/v3/determine_quota_cost

- search.list: 固定 100 点/次（part 参数不影响）
- channels.list: part 数量 × 1 点/次
- videos.list: part 数量 × 1 点/次
- playlistItems.list: part 数量 × 1 点/次
- commentThreads.list: part 数量 × 1 点/次
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.quota import add_quota_points

# 完整查表法：每个 API 方法的配额计算配置
# base: 固定基础成本（search.list 为 100）
# per_part: 每个 part 的附加成本（channels/videos 等为 1）
API_QUOTA_TABLE: dict[str, dict[str, int]] = {
    "search": {"base": 100, "per_part": 0},
    "channels": {"base": 0, "per_part": 1},
    "videos": {"base": 0, "per_part": 1},
    "playlistItems": {"base": 0, "per_part": 1},
    "commentThreads": {"base": 0, "per_part": 1},
}

# 向后兼容：旧代码不传 api_name 时的默认点数
API_POINTS: dict[str, int] = {
    "search": 100,
    "channels": 1,
    "videos": 1,
    "playlistItems": 1,
    "commentThreads": 1,
}


def calc_quota_points(api_name: str, times: int = 1, part_count: int = 1) -> int:
    """计算配额点数（纯函数，不写库）。

    Args:
        api_name: API 方法名，如 "search", "channels"
        times: 调用次数
        part_count: 本次请求使用的 part 数量（search 固定忽略）

    Returns:
        总配额点数
    """
    config = API_QUOTA_TABLE.get(api_name)
    if config:
        per_call = config["base"] + config["per_part"] * max(1, part_count)
    else:
        per_call = API_POINTS.get(api_name, 0)
    return per_call * max(1, times)


async def record_api_quota_usage(
    session: AsyncSession,
    api_name: str,
    times: int = 1,
    part_count: int = 1,
) -> int:
    """记录 API 配额消耗。

    Args:
        session: 数据库会话
        api_name: API 方法名
        times: 调用次数
        part_count: 本次请求使用的 part 数量

    Returns:
        本次记录的配额点数
    """
    points = calc_quota_points(api_name, times=times, part_count=part_count)
    if points > 0:
        await add_quota_points(session, points)
    return points


async def record_bulk_pipeline_quota(
    session: AsyncSession,
    *,
    for_handle_calls: int = 0,
    channels_list_calls: int = 0,
    channels_part_count: int = 2,
    playlist_items_calls: int = 0,
    playlist_items_part_count: int = 1,
    videos_list_calls: int = 0,
    videos_part_count: int = 4,
) -> int:
    """批量流水线配额入账。

    forHandle 与 channels.list 均计为 channels 类型。
    返回本次合计点数。
    """
    total = 0
    ch_times = max(0, for_handle_calls) + max(0, channels_list_calls)
    if ch_times > 0:
        total += await record_api_quota_usage(
            session, "channels", times=ch_times, part_count=channels_part_count,
        )
    if playlist_items_calls > 0:
        total += await record_api_quota_usage(
            session, "playlistItems", times=playlist_items_calls, part_count=playlist_items_part_count,
        )
    if videos_list_calls > 0:
        total += await record_api_quota_usage(
            session, "videos", times=videos_list_calls, part_count=videos_part_count,
        )
    return total
