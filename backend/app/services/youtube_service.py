from __future__ import annotations

from datetime import datetime
import re

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


CHANNEL_ID_REGEX = re.compile(r"(?:youtube\.com/channel/)(UC[a-zA-Z0-9_-]{22})")
HANDLE_REGEX = re.compile(r"(?:youtube\.com/)(@[\w\.-]+)")


def parse_youtube_identifier(youtube_url: str) -> dict[str, str]:
    """从 YouTube URL 提取 channel_id 或 handle。"""
    channel_match = CHANNEL_ID_REGEX.search(youtube_url)
    if channel_match:
        return {"channel_id": channel_match.group(1)}

    handle_match = HANDLE_REGEX.search(youtube_url)
    if handle_match:
        return {"handle": handle_match.group(1)}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="无法识别 YouTube URL，请使用 /channel/ID 或 /@handle 格式",
    )


async def fetch_channel_info(identifier: dict[str, str]) -> dict:
    """调用 channels 端点获取频道信息。"""
    if not settings.youtube_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="后端未配置 YOUTUBE_API_KEY",
        )

    params = {
        "part": "snippet,statistics",
        "key": settings.youtube_api_key,
    }
    if "channel_id" in identifier:
        params["id"] = identifier["channel_id"]
    else:
        params["forHandle"] = identifier["handle"].lstrip("@")

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get("https://www.googleapis.com/youtube/v3/channels", params=params)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube channels API 调用失败：{response.text}",
        )
    data = response.json()
    items = data.get("items", [])
    if not items:
        raise HTTPException(status_code=404, detail="未找到频道信息")
    return items[0]


async def fetch_recent_videos(channel_id: str, limit: int = 10) -> list[dict]:
    """先 search 拿视频 ID，再 videos 拉取统计信息。"""
    async with httpx.AsyncClient(timeout=15) as client:
        search_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "channelId": channel_id,
                "type": "video",
                "order": "date",
                "maxResults": limit,
                "key": settings.youtube_api_key,
            },
        )
    if search_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube search API 调用失败：{search_resp.text}",
        )

    search_items = search_resp.json().get("items", [])
    video_ids = [item.get("id", {}).get("videoId") for item in search_items]
    video_ids = [vid for vid in video_ids if vid]
    if not video_ids:
        return []

    async with httpx.AsyncClient(timeout=15) as client:
        videos_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "contentDetails,status,statistics,snippet",
                "id": ",".join(video_ids),
                "key": settings.youtube_api_key,
            },
        )
    if videos_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"YouTube videos API 调用失败：{videos_resp.text}",
        )
    items = videos_resp.json().get("items", [])
    for item in items:
        raw_duration = item.get("contentDetails", {}).get("duration")
        sec = duration_iso8601_to_seconds(raw_duration)
        item["_duration_sec"] = sec
        item["_duration_str"] = seconds_to_duration_str(sec)
    return items


async def fetch_channels_by_ids(channel_ids: list[str], return_call_count: bool = False):
    """批量按 channel id 拉取频道详情，单次最多 50 个。"""
    if not channel_ids:
        return []

    async with httpx.AsyncClient(timeout=15) as client:
        all_items: list[dict] = []
        call_count = 0
        for i in range(0, len(channel_ids), 50):
            chunk = channel_ids[i : i + 50]
            call_count += 1
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "part": "snippet,statistics",
                    "id": ",".join(chunk),
                    "key": settings.youtube_api_key,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"YouTube channels(batch) API 调用失败：{resp.text}",
                )
            all_items.extend(resp.json().get("items", []))
    if return_call_count:
        return all_items, call_count
    return all_items


def parse_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None


def calc_recent_avg_views(video_items: list[dict]) -> int:
    if not video_items:
        return 0
    total = 0
    for item in video_items:
        total += int(item.get("statistics", {}).get("viewCount", 0))
    return int(total / len(video_items))


def duration_iso8601_to_seconds(value: str | None) -> int:
    if not value:
        return 0
    pattern = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")
    m = pattern.match(value)
    if not m:
        return 0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_duration_str(sec: int) -> str:
    sec = max(0, int(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

