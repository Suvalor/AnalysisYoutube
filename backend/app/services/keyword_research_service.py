"""关键词研究服务。

调用 YouTube Data API 获取搜索数据，结合 keyword_scoring_algorithm 计算评分。

API 调用策略（配额优化）：
1. search.list（100 配额/次）：获取搜索结果数、相关视频、频道
2. channels.list（1 配额/次）：获取频道统计（批量，50/次）
3. videos.list（1 配额/次）：获取视频时长和统计
4. YouTube Suggest API（免费）：获取搜索建议/相关词

趋势数据策略：
- 用不同 publishedAfter 参数多次调用 search.list
- 7天/30天/90天 三个时间窗口
- 总配额消耗：3-4 次 search.list + 1 次 channels.list + 1 次 videos.list ≈ 302-402 配额
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

from app.services.keyword_scoring_algorithm import (
    calc_channel_authority,
    calc_competition_score,
    calc_content_gap_ratio,
    calc_keyword_difficulty,
    calc_keyword_score,
    calc_opportunity_score,
    calc_search_volume_score,
    calc_trend_direction,
)

# ── YouTube API 常量 ──

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
SUGGEST_API_BASE = "https://suggestqueries.google.com/complete/search"
HTTP_TIMEOUT = 30


def _require_api_key(key: str | None) -> str:
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API Key 未配置，请在设置中心配置",
        )
    return key


# ──────────────────────────────────────────────
# 1. YouTube Suggest API（免费，不消耗配额）
# ──────────────────────────────────────────────

async def fetch_suggestions(
    *,
    keyword: str,
    region: str = "US",
    language: str = "zh",
) -> list[str]:
    """获取 YouTube 搜索建议（相关关键词）。

    使用 Google Suggest API，不消耗 YouTube Data API 配额。
    """
    suggestions: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
            # 前缀组合：原词 + 字母后缀
            prefixes = [keyword]
            for ch in "abcdefghijklmnopqrstuvwxyz":
                prefixes.append(f"{keyword} {ch}")

            # 批量请求（限制并发，避免被限流）
            for prefix in prefixes[:6]:  # 最多6个前缀
                try:
                    resp = await client.get(
                        SUGGEST_API_BASE,
                        params={
                            "q": prefix,
                            "client": "youtube",
                            "hl": language,
                            "gl": region.lower(),
                            "ds": "yt",
                        },
                    )
                    if resp.status_code != 200:
                        continue
                    # 解析 JSONP 响应
                    text = resp.text
                    # 格式：window.google.ac.h([...])
                    match = re.search(r"\[(\[.*\])\]", text)
                    if match:
                        import json
                        data = json.loads(match.group(1))
                        for item in data:
                            if isinstance(item, list) and len(item) > 0:
                                word = item[0]
                                if isinstance(word, str) and word.lower() != keyword.lower():
                                    if word not in suggestions:
                                        suggestions.append(word)
                except Exception:
                    continue
    except Exception:
        logger.warning("获取搜索建议失败: keyword=%s, region=%s", keyword, region, exc_info=True)

    return suggestions[:30]  # 最多返回30个


# ──────────────────────────────────────────────
# 2. YouTube search.list（100 配额/次）
# ──────────────────────────────────────────────

async def _search_youtube(
    *,
    keyword: str,
    region: str,
    api_key: str,
    published_after: str | None = None,
    max_results: int = 15,
    order: str = "relevance",
) -> dict[str, Any]:
    """调用 YouTube search.list。

    Returns: API 原始 JSON 响应。
    """
    params: dict[str, Any] = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "regionCode": region,
        "maxResults": max_results,
        "order": order,
        "key": api_key,
    }
    if published_after:
        params["publishedAfter"] = published_after

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        resp = await client.get(f"{YOUTUBE_API_BASE}/search", params=params)
        if resp.status_code != 200:
            detail = f"YouTube search API 返回 {resp.status_code}"
            try:
                err = resp.json().get("error", {}).get("message", "")
                if err:
                    detail = err
            except Exception:
                logger.warning("解析 YouTube search API 错误响应失败: status=%d", resp.status_code)
            raise HTTPException(status_code=502, detail=detail)
        return resp.json()


# ──────────────────────────────────────────────
# 3. YouTube channels.list（1 配额/次）
# ──────────────────────────────────────────────

async def _fetch_channel_stats(
    *,
    channel_ids: list[str],
    api_key: str,
) -> dict[str, dict]:
    """批量获取频道统计。"""
    if not channel_ids:
        return {}
    result: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        # 批量 50/次
        for i in range(0, len(channel_ids), 50):
            chunk = channel_ids[i : i + 50]
            resp = await client.get(
                f"{YOUTUBE_API_BASE}/channels",
                params={
                    "part": "statistics",
                    "id": ",".join(chunk),
                    "key": api_key,
                },
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            for item in data.get("items", []):
                cid = item.get("id", "")
                stats = item.get("statistics", {})
                try:
                    result[cid] = {
                        "subscriber_count": int(stats.get("subscriberCount", 0)),
                        "video_count": int(stats.get("videoCount", 0)),
                        "total_views": int(stats.get("viewCount", 0)),
                    }
                except (TypeError, ValueError):
                    continue
    return result


# ──────────────────────────────────────────────
# 4. YouTube videos.list（1 配额/次）
# ──────────────────────────────────────────────

async def _fetch_video_details(
    *,
    video_ids: list[str],
    api_key: str,
) -> list[dict]:
    """批量获取视频详情（时长、统计）。"""
    if not video_ids:
        return []
    videos: list[dict] = []
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            resp = await client.get(
                f"{YOUTUBE_API_BASE}/videos",
                params={
                    "part": "statistics,contentDetails",
                    "id": ",".join(chunk),
                    "key": api_key,
                },
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            for item in data.get("items", []):
                stats = item.get("statistics", {})
                content = item.get("contentDetails", {})
                duration_iso = content.get("duration", "PT0S")
                duration_sec = _parse_iso_duration(duration_iso)
                try:
                    videos.append({
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                        "duration_sec": duration_sec,
                    })
                except (TypeError, ValueError):
                    continue
    return videos


def _parse_iso_duration(iso: str) -> int:
    """解析 ISO 8601 时长（PT1H2M10S）→ 秒数。"""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + s


# ──────────────────────────────────────────────
# 5. 主入口：关键词研究
# ──────────────────────────────────────────────

async def research_keyword(
    *,
    keyword: str,
    region: str = "US",
    language: str = "zh",
    youtube_api_key: str,
) -> dict:
    """执行关键词研究，返回完整评分结果。

    流程：
    1. 获取搜索建议（免费）
    2. search.list 获取主搜索结果 + 趋势数据（3次调用）
    3. channels.list 获取频道统计
    4. videos.list 获取视频详情
    5. 调用评分算法计算各维度评分
    6. 对相关词做轻量评分
    """
    api_key = _require_api_key(youtube_api_key)
    search_calls = 0

    # ── Step 1：获取搜索建议 ──
    suggestions = await fetch_suggestions(keyword=keyword, region=region, language=language)

    # ── Step 2：主搜索 + 趋势数据 ──
    now = datetime.now(timezone.utc)

    # 主搜索（最近365天，按相关性排序）
    main_result = await _search_youtube(
        keyword=keyword, region=region, api_key=api_key,
        published_after=(now - timedelta(days=365)).isoformat(),
        max_results=15,
    )
    search_calls += 1
    total_results = main_result.get("pageInfo", {}).get("totalResults", 0)

    # 趋势搜索（7天/30天/90天窗口）
    trend_data: list[dict] = []
    for period_label, days in [("7天", 7), ("30天", 30), ("90天", 90)]:
        try:
            trend_result = await _search_youtube(
                keyword=keyword, region=region, api_key=api_key,
                published_after=(now - timedelta(days=days)).isoformat(),
                max_results=5,
                order="date",
            )
            search_calls += 1
            trend_count = trend_result.get("pageInfo", {}).get("totalResults", 0)
            trend_data.append({
                "period": period_label,
                "days": days,
                "result_count": trend_count,
            })
        except Exception:
            logger.warning("趋势搜索失败: keyword=%s, period=%s", keyword, period_label, exc_info=True)
            trend_data.append({"period": period_label, "days": days, "result_count": 0})

    # ── Step 3：提取频道ID和视频ID ──
    channel_ids: list[str] = []
    video_ids: list[str] = []
    top_videos_raw: list[dict] = []

    for item in main_result.get("items", []):
        snippet = item.get("snippet", {})
        cid = snippet.get("channelId", "")
        vid = item.get("id", {}).get("videoId", "")
        if cid and cid not in channel_ids:
            channel_ids.append(cid)
        if vid and vid not in video_ids:
            video_ids.append(vid)
        top_videos_raw.append({
            "channel_title": snippet.get("channelTitle", ""),
            "channel_id": cid,
        })

    # ── Step 4：获取频道统计 ──
    channel_stats = await _fetch_channel_stats(channel_ids=channel_ids, api_key=api_key)
    channels_calls = math.ceil(len(channel_ids) / 50) if channel_ids else 0

    # ── Step 5：获取视频详情 ──
    video_details = await _fetch_video_details(video_ids=video_ids, api_key=api_key)
    videos_calls = math.ceil(len(video_ids) / 50) if video_ids else 0

    # ── Step 6：计算评分 ──

    # 6a. 搜索量评分
    search_volume_score = calc_search_volume_score(
        total_results=total_results,
        related_keyword_count=len(suggestions),
        suggest_hit_count=len(suggestions),
    )

    # 6b. 竞争度评分
    channel_subscribers = [
        stats["subscriber_count"]
        for stats in channel_stats.values()
    ]
    video_view_counts = [v["view_count"] for v in video_details]
    competition_score = calc_competition_score(
        channel_subscribers=channel_subscribers,
        video_view_counts=video_view_counts,
        total_results=total_results,
    )

    # 6c. 关键词难度
    # 播放/订阅比
    views_per_sub: list[float] = []
    for v in video_details:
        # 找到该视频对应的频道
        idx = video_details.index(v)
        if idx < len(top_videos_raw):
            cid = top_videos_raw[idx].get("channel_id", "")
            ch_stats = channel_stats.get(cid, {})
            subs = ch_stats.get("subscriber_count", 0)
            if subs > 0:
                views_per_sub.append(v["view_count"] / subs)

    # 频道权威度
    authority_scores: list[float] = []
    for stats in channel_stats.values():
        authority_scores.append(calc_channel_authority(
            subscriber_count=stats["subscriber_count"],
            video_count=stats["video_count"],
            total_views=stats["total_views"],
        ))

    # 平均视频年龄（用趋势数据估算）
    avg_video_age_days = 90.0  # 默认值
    if trend_data and len(trend_data) >= 2:
        # 用7天和90天的结果数差估算活跃度
        t7 = next((t for t in trend_data if t["days"] == 7), None)
        t90 = next((t for t in trend_data if t["days"] == 90), None)
        if t7 and t90 and t90["result_count"] > 0:
            freshness_ratio = t7["result_count"] / max(t7["days"], 1) / (
                t90["result_count"] / max(t90["days"], 1)
            )
            # freshness_ratio > 1 → 内容新鲜 → 年龄短
            avg_video_age_days = max(7, 180 / max(freshness_ratio, 0.1))

    keyword_difficulty = calc_keyword_difficulty(
        top_video_views_per_sub=views_per_sub,
        channel_authority_scores=authority_scores,
        avg_video_age_days=avg_video_age_days,
    )

    # 6d. 趋势方向
    trend_direction = calc_trend_direction(trend_data=trend_data)

    # 6e. 内容缺口
    video_durations = [v["duration_sec"] for v in video_details]
    avg_views_by_duration: dict[str, int] = {"short": 0, "medium": 0, "long": 0}
    counts_by_duration: dict[str, int] = {"short": 0, "medium": 0, "long": 0}
    for v in video_details:
        dur = v["duration_sec"]
        views = v["view_count"]
        if dur <= 60:
            bucket = "short"
        elif dur <= 600:
            bucket = "medium"
        else:
            bucket = "long"
        avg_views_by_duration[bucket] += views
        counts_by_duration[bucket] += 1
    # 计算平均
    for k in avg_views_by_duration:
        if counts_by_duration[k] > 0:
            avg_views_by_duration[k] = avg_views_by_duration[k] // counts_by_duration[k]

    content_gap_ratio = calc_content_gap_ratio(
        video_durations_sec=video_durations,
        avg_views_by_duration=avg_views_by_duration,
    )

    # 6f. 机会得分
    opportunity_score = calc_opportunity_score(
        search_volume_score=search_volume_score,
        competition_score=competition_score,
        keyword_difficulty=keyword_difficulty,
        trend_direction=trend_direction,
        content_gap_ratio=content_gap_ratio,
    )

    # 6g. 综合评分
    keyword_score = calc_keyword_score(
        search_volume_score=search_volume_score,
        competition_score=competition_score,
        keyword_difficulty=keyword_difficulty,
        opportunity_score=opportunity_score,
    )

    # ── Step 7：相关词轻量评分 ──
    related_with_scores: list[dict] = []
    for kw in suggestions[:10]:
        # 轻量评分：基于关键词长度和与主词的相似度估算
        kw_vol = max(0, search_volume_score - len(kw) * 2)
        kw_comp = min(100, competition_score + (10 if len(kw) < len(keyword) else -5))
        related_with_scores.append({
            "keyword": kw,
            "search_volume_score": kw_vol,
            "competition_score": kw_comp,
        })

    # ── Step 8：组装热门视频数据 ──
    top_videos: list[dict] = []
    for i, v in enumerate(video_details):
        top_videos.append({
            "view_count": v["view_count"],
            "like_count": v["like_count"],
            "comment_count": v["comment_count"],
            "channel_title": top_videos_raw[i]["channel_title"] if i < len(top_videos_raw) else "",
        })

    # 平均频道订阅数
    avg_subs = int(sum(channel_subscribers) / max(len(channel_subscribers), 1))

    return {
        "keyword": keyword,
        "region": region,
        "keyword_score": keyword_score,
        "search_volume_score": search_volume_score,
        "competition_score": competition_score,
        "keyword_difficulty": keyword_difficulty,
        "opportunity_score": opportunity_score,
        "trend_direction": trend_direction,
        "total_results": total_results,
        "related_keywords": suggestions,
        "related_keywords_with_scores": related_with_scores,
        "trend_data": trend_data,
        "top_videos": top_videos,
        "channel_count": len(channel_ids),
        "avg_channel_subscribers": avg_subs,
        "content_gap_ratio": round(content_gap_ratio, 2),
        "search_calls": search_calls,
        "channels_calls": channels_calls,
        "videos_calls": videos_calls,
    }
