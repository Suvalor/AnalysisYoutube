"""频道缓存服务：协调缓存查询、YouTube API 调用与缓存写入。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.channel_cache import (
    batch_get_cached_channels_if_fresh,
    get_cached_channel_even_if_stale,
    get_cached_channel_if_fresh,
    mark_refresh_attempted,
    upsert_channel_cache,
)
from app.services.youtube_service import MAX_IDS_PER_REQUEST, fetch_channels_by_ids

logger = logging.getLogger(__name__)

# 刷新尝试冷却时间（分钟）：在此窗口内不重复尝试刷新过期缓存
_REFRESH_COOLDOWN_MINUTES = 5


async def get_channel_detail_with_cache(
    session: AsyncSession,
    channel_id: str,
    youtube_api_key: str,
) -> dict:
    """获取频道详情，优先从缓存读取；缓存过期时尝试刷新，刷新失败则回退旧缓存。"""
    ttl_hours = settings.channel_cache_ttl_hours

    # 1. 尝试缓存命中（未过期）
    cached = await get_cached_channel_if_fresh(session, channel_id, ttl_hours)
    if cached is not None:
        logger.debug("频道缓存命中: %s", channel_id)
        return _cache_to_dict(cached, cached_flag=True)

    # 2. 缓存过期或不存在，尝试刷新
    logger.debug("频道缓存未命中，尝试刷新: %s", channel_id)
    try:
        yt_items = await fetch_channels_by_ids(
            channel_ids=[channel_id],
            youtube_api_key=youtube_api_key,
        )
        if not yt_items:
            raise ValueError(f"YouTube API 未返回频道 {channel_id} 的数据")

        item = _parse_yt_channel_item(yt_items[0])

        # 3. 成功获取新数据，写入缓存
        await upsert_channel_cache(
            session,
            channel_id=item["channel_id"],
            title=item["title"],
            description=item["description"],
            avatar_url=item.get("avatar_url"),
            subscriber_count=item.get("subscriber_count", 0),
            video_count=item.get("video_count", 0),
            view_count=item.get("view_count", 0),
            published_at=_parse_iso_datetime(item.get("published_at")),
            country=item.get("country"),
            custom_url=item.get("custom_url"),
        )
        await session.commit()
        return {**item, "cached": False}

    except Exception as exc:
        # 4. 刷新失败：回退过期缓存（如有），防止缓存穿透
        logger.warning("频道 %s 刷新失败，尝试回退旧缓存: %s", channel_id, exc)
        stale = await get_cached_channel_even_if_stale(session, channel_id)
        if stale is not None:
            # 检查是否在冷却窗口内已尝试过刷新，避免频繁重试
            if _is_in_refresh_cooldown(stale):
                logger.debug("频道 %s 刚尝试过刷新，返回旧缓存", channel_id)
                return _cache_to_dict(stale, cached_flag=True)

            # 标记本次刷新尝试时间，防止短时间内重复刷新
            await mark_refresh_attempted(session, channel_id)
            await session.commit()
            return _cache_to_dict(stale, cached_flag=True)

        # 无任何缓存数据，向上抛出异常
        raise


async def enrich_channels_with_cache(
    session: AsyncSession,
    channel_ids: list[str],
    youtube_api_key: str,
) -> dict[str, dict]:
    """批量获取频道详情，优先从缓存读取，未命中则批量调用 YouTube API 并写入缓存。"""
    if not channel_ids:
        return {}

    ttl_hours = settings.channel_cache_ttl_hours

    # 1. 批量查缓存
    cached_map = await batch_get_cached_channels_if_fresh(session, channel_ids, ttl_hours)
    result: dict[str, dict] = {
        cid: _cache_to_dict(cache, cached_flag=True) for cid, cache in cached_map.items()
    }

    # 2. 找出未命中的频道 ID
    missed_ids = [cid for cid in channel_ids if cid not in cached_map]
    if not missed_ids:
        logger.debug("全部频道缓存命中，共 %d 个", len(channel_ids))
        return result

    # 3. 批量调用 YouTube API（channels.list 最多 MAX_IDS_PER_REQUEST 个 ID）
    logger.debug("频道缓存未命中 %d 个，调用 YouTube API", len(missed_ids))
    all_api_items: list[dict] = []
    failed_ids: list[str] = []
    for i in range(0, len(missed_ids), MAX_IDS_PER_REQUEST):
        batch = missed_ids[i : i + MAX_IDS_PER_REQUEST]
        try:
            batch_items = await fetch_channels_by_ids(
                channel_ids=batch,
                youtube_api_key=youtube_api_key,
            )
            all_api_items.extend(batch_items)
        except Exception as exc:
            # 单批次失败不阻断整体，记录失败 ID 以便返回占位数据
            logger.warning("批量频道刷新批次失败（%d 个 ID）: %s", len(batch), exc)
            failed_ids.extend(batch)

    # 4. 写入缓存并合并结果
    for raw_item in all_api_items:
        item = _parse_yt_channel_item(raw_item)
        cid = item["channel_id"]
        await upsert_channel_cache(
            session,
            channel_id=cid,
            title=item["title"],
            description=item["description"],
            avatar_url=item.get("avatar_url"),
            subscriber_count=item.get("subscriber_count", 0),
            video_count=item.get("video_count", 0),
            view_count=item.get("view_count", 0),
            published_at=_parse_iso_datetime(item.get("published_at")),
            country=item.get("country"),
            custom_url=item.get("custom_url"),
        )
        result[cid] = {**item, "cached": False}

    await session.commit()

    # 5. 未被 API 返回的频道 ID，优先回退过期缓存，否则保留空条目
    for cid in missed_ids:
        if cid in result:
            continue
        if cid in failed_ids:
            stale = await get_cached_channel_even_if_stale(session, cid)
            if stale is not None:
                result[cid] = _cache_to_dict(stale, cached_flag=True)
                continue
        result[cid] = _placeholder_channel(cid)

    return result


def _cache_to_dict(cache, cached_flag: bool = False) -> dict:
    """将 ChannelCache ORM 对象转为字典，datetime 字段序列化为 ISO 字符串。"""
    published_at_str: str | None = None
    if cache.published_at is not None:
        published_at_str = cache.published_at.isoformat()
    return {
        "channel_id": cache.channel_id,
        "title": cache.title,
        "description": cache.description,
        "avatar_url": cache.avatar_url,
        "subscriber_count": cache.subscriber_count,
        "video_count": cache.video_count,
        "view_count": cache.view_count,
        "published_at": published_at_str,
        "country": cache.country,
        "custom_url": cache.custom_url,
        "cached": cached_flag,
    }


def _parse_yt_channel_item(raw: dict) -> dict:
    """将 YouTube channels.list 返回的单个 item 解析为统一字典格式。"""
    snippet = raw.get("snippet", {})
    statistics = raw.get("statistics", {})
    return {
        "channel_id": raw.get("id", ""),
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "avatar_url": _extract_avatar(snippet),
        "subscriber_count": _safe_int(statistics.get("subscriberCount")),
        "video_count": _safe_int(statistics.get("videoCount")),
        "view_count": _safe_int(statistics.get("viewCount")),
        "published_at": snippet.get("publishedAt"),
        "country": snippet.get("country"),
        "custom_url": snippet.get("customUrl"),
    }


def _extract_avatar(snippet: dict) -> str | None:
    """从 snippet.thumbnails 中提取最高分辨率头像 URL。"""
    thumbnails = snippet.get("thumbnails", {})
    for key in ("maxres", "high", "medium", "default"):
        thumb = thumbnails.get(key)
        if thumb and thumb.get("url"):
            return thumb["url"]
    return None


# subscriber_count 为 "hidden" 时存储为 -1，前端据此显示"隐藏"
_SUBSCRIBER_COUNT_HIDDEN = -1


def _safe_int(value: str | None) -> int:
    """安全地将字符串转为整数；"hidden" 返回 -1，其余失败返回 0。"""
    if value is None:
        return 0
    if isinstance(value, str) and value.strip().lower() == "hidden":
        return _SUBSCRIBER_COUNT_HIDDEN
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _placeholder_channel(channel_id: str) -> dict:
    """生成频道占位数据，用于 API 未返回且无缓存的情况。"""
    return {
        "channel_id": channel_id,
        "title": "",
        "description": "",
        "subscriber_count": 0,
        "video_count": 0,
        "view_count": 0,
    }


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """将 ISO 8601 字符串解析为 datetime 对象，失败返回 None。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _is_in_refresh_cooldown(cache) -> bool:
    """检查缓存记录是否在刷新冷却窗口内，防止短时间内重复刷新。"""
    if cache.refresh_attempted_at is None:
        return False
    cooldown_cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=_REFRESH_COOLDOWN_MINUTES
    )
    return cache.refresh_attempted_at >= cooldown_cutoff
