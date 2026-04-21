"""热门趋势发现服务：按地区/品类获取 YouTube Trending 数据。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
HTTP_TIMEOUT = httpx.Timeout(30.0)

# YouTube 品类 ID → 名称映射
CATEGORY_NAMES: dict[str, str] = {
    "0": "全部", "1": "电影与动画", "2": "汽车与车辆", "10": "音乐",
    "15": "宠物与动物", "17": "体育", "18": "短片", "19": "旅行与活动",
    "20": "游戏", "21": "视频博客", "22": "人物与博客", "23": "喜剧",
    "24": "娱乐", "25": "新闻与政治", "26": "操作指南与风格",
    "27": "教育", "28": "科学与技术", "29": "非营利组织与行动主义",
}


async def fetch_trending(
    *,
    youtube_api_key: str,
    region: str = "US",
    category_id: str | None = None,
    max_results: int = 50,
) -> dict:
    """
    获取 YouTube 热门趋势视频。

    流程：
    1. videos.list(chart=mostPopular) 获取热门视频列表
    2. 提取频道 ID → channels.list 获取频道信息
    3. 计算趋势指标（互动率）
    4. 按品类分组统计

    返回趋势视频列表 + 品类分布 + 统计摘要。
    """
    now = datetime.now(timezone.utc)

    # ── Step 1: 获取热门视频 ──
    video_params: dict = {
        "chart": "mostPopular",
        "regionCode": region,
        "part": "snippet,contentDetails,statistics",
        "maxResults": min(max_results, 50),
        "key": youtube_api_key,
    }
    if category_id:
        video_params["videoCategoryId"] = category_id

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        resp = await client.get(f"{YOUTUBE_API_BASE}/videos", params=video_params)
        if resp.status_code != 200:
            logger.error("YouTube videos.list 失败: %s", resp.text[:500])
            return {
                "region": region,
                "category_id": category_id,
                "fetched_at": now.isoformat(),
                "trending_videos": [],
                "category_distribution": [],
                "stats": {
                    "total_videos": 0,
                    "avg_views": 0,
                    "avg_likes": 0,
                    "avg_engagement_rate": 0,
                },
            }

        data = resp.json()
        items = data.get("items", [])

        if not items:
            return {
                "region": region,
                "category_id": category_id,
                "fetched_at": now.isoformat(),
                "trending_videos": [],
                "category_distribution": [],
                "stats": {
                    "total_videos": 0,
                    "avg_views": 0,
                    "avg_likes": 0,
                    "avg_engagement_rate": 0,
                },
            }

        # ── Step 2: 解析视频数据 ──
        trending_videos = []
        channel_ids = set()
        category_count: dict[str, int] = {}

        for item in items:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})

            vid_cat = snippet.get("categoryId", "0")
            category_count[vid_cat] = category_count.get(vid_cat, 0) + 1

            ch_id = snippet.get("channelId", "")
            if ch_id:
                channel_ids.add(ch_id)

            view_count = int(stats.get("viewCount", 0))
            like_count = int(stats.get("likeCount", 0))
            comment_count = int(stats.get("commentCount", 0))
            engagement_rate = (
                (like_count + comment_count) / view_count * 100
                if view_count > 0
                else 0
            )

            trending_videos.append({
                "video_id": item.get("id", ""),
                "title": snippet.get("title", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "channel_id": ch_id,
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail_url": (
                    snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                    or snippet.get("thumbnails", {}).get("default", {}).get("url", "")
                ),
                "category_id": vid_cat,
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "engagement_rate": round(engagement_rate, 2),
                "duration": content.get("duration", ""),
            })

        # ── Step 3: 获取频道信息（批量） ──
        channel_map: dict[str, dict] = {}
        if channel_ids:
            ch_ids_list = list(channel_ids)
            for i in range(0, len(ch_ids_list), 50):
                batch = ch_ids_list[i : i + 50]
                try:
                    ch_resp = await client.get(
                        f"{YOUTUBE_API_BASE}/channels",
                        params={
                            "id": ",".join(batch),
                            "part": "snippet,statistics",
                            "key": youtube_api_key,
                        },
                    )
                    if ch_resp.status_code == 200:
                        ch_data = ch_resp.json()
                        for ch in ch_data.get("items", []):
                            ch_stats = ch.get("statistics", {})
                            channel_map[ch["id"]] = {
                                "subscriber_count": int(ch_stats.get("subscriberCount", 0)),
                                "total_views": int(ch_stats.get("viewCount", 0)),
                                "video_count": int(ch_stats.get("videoCount", 0)),
                            }
                except Exception:
                    logger.warning("channels.list 批量查询失败，跳过频道详情")

    # 将频道信息合并到视频
    for v in trending_videos:
        ch_info = channel_map.get(v["channel_id"], {})
        v["channel_subscribers"] = ch_info.get("subscriber_count", 0)

    # ── Step 4: 品类分布 ──
    category_distribution = sorted(
        [
            {
                "category_id": cid,
                "category_name": CATEGORY_NAMES.get(cid, f"品类 {cid}"),
                "video_count": count,
                "percentage": round(count / len(items) * 100, 1),
            }
            for cid, count in category_count.items()
        ],
        key=lambda x: x["video_count"],
        reverse=True,
    )

    # ── Step 5: 统计摘要 ──
    total_views = sum(v["view_count"] for v in trending_videos)
    total_likes = sum(v["like_count"] for v in trending_videos)
    avg_engagement = (
        sum(v["engagement_rate"] for v in trending_videos) / len(trending_videos)
        if trending_videos
        else 0
    )

    stats = {
        "total_videos": len(trending_videos),
        "avg_views": round(total_views / len(trending_videos)) if trending_videos else 0,
        "avg_likes": round(total_likes / len(trending_videos)) if trending_videos else 0,
        "avg_engagement_rate": round(avg_engagement, 2),
    }

    return {
        "region": region,
        "category_id": category_id,
        "fetched_at": now.isoformat(),
        "trending_videos": trending_videos,
        "category_distribution": category_distribution,
        "stats": stats,
    }
