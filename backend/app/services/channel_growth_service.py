"""频道增长仪表盘服务。

基于 YouTubeChannelHistory 表的历史数据计算增长指标，
同时调用 YouTube Data API 获取最新频道统计。
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import httpx
from fastapi import HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.youtube import YouTubeChannel, YouTubeChannelHistory, UserCompetitorPool
from app.services.youtube_service import YOUTUBE_API_BASE, HTTP_TIMEOUT, _require_api_key

MAX_CHANNELS_PER_REQUEST = 10


async def fetch_latest_channel_stats(
    *,
    yt_channel_ids: list[str],
    youtube_api_key: str,
) -> dict[str, dict]:
    """调用 YouTube channels.list 获取最新频道统计。

    Returns:
        {yt_channel_id: {subscriber_count, view_count, video_count}}
    """
    _require_api_key(youtube_api_key)
    if not yt_channel_ids:
        return {}

    result: dict[str, dict] = {}
    # YouTube API 单次最多 50 个 ID
    chunk_size = 50
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        for i in range(0, len(yt_channel_ids), chunk_size):
            chunk = yt_channel_ids[i : i + chunk_size]
            resp = await client.get(
                f"{YOUTUBE_API_BASE}/channels",
                params={
                    "part": "statistics",
                    "id": ",".join(chunk),
                    "key": youtube_api_key,
                },
            )
            if resp.status_code != 200:
                # 非致命：API 失败时返回空结果，不阻断整个请求
                continue
            data = resp.json()
            for item in data.get("items", []):
                cid = item.get("id", "")
                stats = item.get("statistics", {})
                try:
                    result[cid] = {
                        "subscriber_count": int(stats.get("subscriberCount", 0)),
                        "view_count": int(stats.get("viewCount", 0)),
                        "video_count": int(stats.get("videoCount", 0)),
                    }
                except (TypeError, ValueError):
                    continue
    return result


async def get_channel_growth_data(
    session: AsyncSession,
    *,
    user_id: int,
    channel_ids: list[int],
    days: int = 30,
    youtube_api_key: str | None = None,
) -> dict:
    """计算频道增长指标。

    流程：
    1. 从监控池获取频道信息
    2. 从 YouTubeChannelHistory 获取历史数据
    3. （可选）调用 YouTube API 获取最新统计
    4. 计算增长率、趋势、互动得分
    """
    # 1. 获取用户监控池中的频道
    channel_ids = channel_ids[:MAX_CHANNELS_PER_REQUEST]
    stmt = (
        select(UserCompetitorPool)
        .options(selectinload(UserCompetitorPool.channel))
        .where(UserCompetitorPool.user_id == user_id)
    )
    if channel_ids:
        stmt = stmt.where(UserCompetitorPool.channel_id.in_(channel_ids))
    result = await session.execute(stmt)
    pools = list(result.scalars().unique().all())

    if not pools:
        return {"channels": [], "summary": _empty_summary(), "quota_used": 0}

    # 构建频道映射
    channel_map: dict[int, YouTubeChannel] = {}
    pool_map: dict[int, int] = {}  # channel_db_id -> pool_id
    for pool in pools:
        if pool.channel is not None:
            channel_map[pool.channel.id] = pool.channel
            pool_map[pool.channel.id] = pool.id

    # 2. 获取历史数据
    start_date = date.today() - timedelta(days=days)
    db_channel_ids = list(channel_map.keys())

    hist_stmt = (
        select(YouTubeChannelHistory)
        .where(
            YouTubeChannelHistory.channel_id.in_(db_channel_ids),
            YouTubeChannelHistory.record_date >= start_date,
        )
        .order_by(
            YouTubeChannelHistory.channel_id.asc(),
            YouTubeChannelHistory.record_date.asc(),
        )
    )
    hist_result = await session.execute(hist_stmt)
    history_rows = list(hist_result.scalars().all())

    # 按频道分组历史
    history_by_channel: dict[int, list[YouTubeChannelHistory]] = {}
    for row in history_rows:
        history_by_channel.setdefault(row.channel_id, []).append(row)

    # 3. 调用 YouTube API 获取最新统计（如果提供了 API key）
    latest_stats: dict[str, dict] = {}
    quota_used = 0
    if youtube_api_key:
        yt_ids = [ch.yt_channel_id for ch in channel_map.values()]
        latest_stats = await fetch_latest_channel_stats(
            yt_channel_ids=yt_ids,
            youtube_api_key=youtube_api_key,
        )
        if latest_stats:
            # channels.list with 1 part = 1 quota unit per request
            quota_used = math.ceil(len(yt_ids) / 50)

    # 4. 计算各频道增长指标
    channels_data: list[dict] = []
    for db_id, channel in channel_map.items():
        histories = history_by_channel.get(db_id, [])

        # 当前值：优先使用 API 最新数据，否则使用数据库中的值
        api_stats = latest_stats.get(channel.yt_channel_id)
        if api_stats:
            current_subs = api_stats["subscriber_count"]
            current_views = api_stats["view_count"]
            current_videos = api_stats["video_count"]
        else:
            current_subs = channel.subscriber_count
            current_views = channel.total_views
            current_videos = channel.video_count

        # 历史数据点
        growth_data: list[dict] = []
        for h in histories:
            growth_data.append({
                "date": h.record_date.isoformat(),
                "subscribers": h.subscriber_count,
                "views": h.total_views,
                "videos": h.video_count,
            })

        # 计算增长率
        sub_growth_rate = 0.0
        view_growth_rate = 0.0
        if histories:
            earliest = histories[0]
            if earliest.subscriber_count > 0:
                sub_growth_rate = (
                    (current_subs - earliest.subscriber_count) / earliest.subscriber_count * 100
                )
            if earliest.total_views > 0:
                view_growth_rate = (
                    (current_views - earliest.total_views) / earliest.total_views * 100
                )

        # 平均单视频播放量
        avg_views_per_video = current_views / max(current_videos, 1)

        # 互动得分（基于增长率和平均播放量的综合评分 0-100）
        engagement_score = _calc_engagement_score(
            sub_growth_rate=sub_growth_rate,
            view_growth_rate=view_growth_rate,
            avg_views_per_video=avg_views_per_video,
        )

        # 增长趋势
        if sub_growth_rate > 5 or view_growth_rate > 10:
            growth_trend = "rising"
        elif sub_growth_rate < -2 or view_growth_rate < -5:
            growth_trend = "declining"
        else:
            growth_trend = "stable"

        channels_data.append({
            "pool_id": pool_map.get(db_id, 0),
            "channel_id": channel.yt_channel_id,
            "title": channel.title,
            "thumbnail_url": channel.thumbnail_url,
            "current_subscribers": current_subs,
            "current_views": current_views,
            "current_videos": current_videos,
            "subscriber_growth_rate": round(sub_growth_rate, 2),
            "view_growth_rate": round(view_growth_rate, 2),
            "avg_views_per_video": round(avg_views_per_video, 1),
            "engagement_score": round(engagement_score, 1),
            "growth_trend": growth_trend,
            "growth_data": growth_data,
        })

    # 5. 汇总统计
    summary = _calc_summary(channels_data)

    return {
        "channels": channels_data,
        "summary": summary,
        "quota_used": quota_used,
    }


def _calc_engagement_score(
    *,
    sub_growth_rate: float,
    view_growth_rate: float,
    avg_views_per_video: float,
) -> float:
    """计算互动得分（0-100）。

    权重：
    - 订阅增长率 40%
    - 播放量增长率 40%
    - 平均播放量 20%（对数缩放）
    """
    # 增长率映射到 0-100（sigmoid-like）
    def _rate_to_score(rate: float) -> float:
        # 10% 增长 → ~50分, 50% → ~80分, -10% → ~20分
        return 100 / (1 + math.exp(-0.1 * rate))

    sub_score = _rate_to_score(sub_growth_rate)
    view_score = _rate_to_score(view_growth_rate)

    # 平均播放量对数缩放（1000 views → ~30, 10000 → ~50, 100000 → ~70）
    if avg_views_per_video > 0:
        avg_score = min(100, max(0, (math.log10(avg_views_per_video) - 1) * 25))
    else:
        avg_score = 0

    return sub_score * 0.4 + view_score * 0.4 + avg_score * 0.2


def _calc_summary(channels_data: list[dict]) -> dict:
    """计算汇总统计。"""
    if not channels_data:
        return _empty_summary()

    total_subs = sum(c["current_subscribers"] for c in channels_data)
    total_views = sum(c["current_views"] for c in channels_data)
    total_videos = sum(c["current_videos"] for c in channels_data)
    avg_sub_growth = sum(c["subscriber_growth_rate"] for c in channels_data) / len(channels_data)
    avg_view_growth = sum(c["view_growth_rate"] for c in channels_data) / len(channels_data)

    # 增长最快频道
    fastest = max(channels_data, key=lambda c: c["subscriber_growth_rate"])

    return {
        "total_subscribers": total_subs,
        "total_views": total_views,
        "total_videos": total_videos,
        "avg_subscriber_growth_rate": round(avg_sub_growth, 2),
        "avg_view_growth_rate": round(avg_view_growth, 2),
        "fastest_growing_channel": fastest["title"],
        "fastest_growing_rate": fastest["subscriber_growth_rate"],
    }


def _empty_summary() -> dict:
    return {
        "total_subscribers": 0,
        "total_views": 0,
        "total_videos": 0,
        "avg_subscriber_growth_rate": 0.0,
        "avg_view_growth_rate": 0.0,
        "fastest_growing_channel": "",
        "fastest_growing_rate": 0.0,
    }
