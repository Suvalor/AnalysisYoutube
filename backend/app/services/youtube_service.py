from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

CHANNEL_ID_REGEX = re.compile(r"(?:youtube\.com/channel/)(UC[a-zA-Z0-9_-]{22})")
HANDLE_REGEX = re.compile(r"(?:youtube\.com/)(@[\w\.-]+)")

# 单次请求最多 50 个 ID（YouTube Data API 限制）
MAX_IDS_PER_REQUEST = 50

HTTP_TIMEOUT = httpx.Timeout(30.0)


def chunked(seq: list[str], size: int = MAX_IDS_PER_REQUEST) -> list[list[str]]:
    """将列表按固定长度切片。"""
    if size < 1:
        raise ValueError("size 必须 >= 1")
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def split_url_segments(raw: str) -> list[str]:
    """按分号或换行切分输入，去空。"""
    if not raw or not raw.strip():
        return []
    parts = re.split(r"[;\n\r]+", raw)
    return [p.strip() for p in parts if p.strip()]


def extract_handles_and_channel_ids_from_bulk(raw: str) -> tuple[set[str], set[str]]:
    """
    从批量输入中提取 Handle（含 @）与频道 UC ID。
    对每个片段分别用正则搜索。
    """
    handles: set[str] = set()
    channel_ids: set[str] = set()
    for segment in split_url_segments(raw):
        ch = CHANNEL_ID_REGEX.search(segment)
        if ch:
            channel_ids.add(ch.group(1))
        ha = HANDLE_REGEX.search(segment)
        if ha:
            handles.add(ha.group(1))
    return handles, channel_ids


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


def _require_api_key() -> None:
    if not settings.youtube_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="后端未配置 YOUTUBE_API_KEY",
        )


def _http_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


def enrich_video_items(items: list[dict]) -> None:
    """为 videos.list 返回的条目补充时长等派生字段（原地修改）。"""
    for item in items:
        raw_duration = item.get("contentDetails", {}).get("duration")
        sec = duration_iso8601_to_seconds(raw_duration)
        item["_duration_sec"] = sec
        item["_duration_str"] = seconds_to_duration_str(sec)
        pub = item.get("snippet", {}).get("publishedAt")
        item["_parsed_published_at"] = parse_datetime(pub)


async def fetch_channel_info(identifier: dict[str, str]) -> dict:
    """调用 channels 端点获取频道信息。"""
    _require_api_key()

    params = {
        "part": "snippet,statistics",
        "key": settings.youtube_api_key,
    }
    if "channel_id" in identifier:
        params["id"] = identifier["channel_id"]
    else:
        params["forHandle"] = identifier["handle"].lstrip("@")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.get(f"{YOUTUBE_API_BASE}/channels", params=params)

    if response.status_code != 200:
        raise _http_error(f"YouTube channels API 调用失败：{response.text}")
    data = response.json()
    items = data.get("items", [])
    if not items:
        raise HTTPException(status_code=404, detail="未找到频道信息")
    return items[0]


async def _channels_get(
    client: httpx.AsyncClient,
    *,
    params: dict,
) -> dict:
    q = {"key": settings.youtube_api_key, **params}
    resp = await client.get(f"{YOUTUBE_API_BASE}/channels", params=q)
    if resp.status_code != 200:
        raise _http_error(f"YouTube channels API 调用失败：{resp.text}")
    return resp.json()


async def _playlist_items_get(
    client: httpx.AsyncClient,
    *,
    playlist_id: str,
    max_results: int,
) -> dict:
    resp = await client.get(
        f"{YOUTUBE_API_BASE}/playlistItems",
        params={
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": max(1, min(max_results, 50)),
            "key": settings.youtube_api_key,
        },
    )
    if resp.status_code != 200:
        raise _http_error(f"YouTube playlistItems API 调用失败：{resp.text}")
    return resp.json()


async def _videos_get(client: httpx.AsyncClient, *, video_ids: list[str]) -> dict:
    resp = await client.get(
        f"{YOUTUBE_API_BASE}/videos",
        params={
            "part": "contentDetails,status,statistics,snippet",
            "id": ",".join(video_ids),
            "key": settings.youtube_api_key,
        },
    )
    if resp.status_code != 200:
        raise _http_error(f"YouTube videos API 调用失败：{resp.text}")
    return resp.json()


@dataclass
class FetchRecentVideosQuota:
    """fetch_recent_videos 的 API 调用次数（用于配额入账）。"""

    channels_calls: int = 0
    playlist_items_calls: int = 0
    videos_list_calls: int = 0


async def fetch_recent_videos(
    channel_id: str,
    limit: int = 10,
    *,
    return_quota: bool = False,
) -> list[dict] | tuple[list[dict], FetchRecentVideosQuota]:
    """
    通过 uploads 播放列表 + videos.list 获取近期视频（不使用 Search API）。
    消耗：channels 1 + playlistItems 1 + videos 按 50 个分块。
    """
    _require_api_key()
    limit = max(1, min(limit, 50))
    quota = FetchRecentVideosQuota()

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        data = await _channels_get(
            client,
            params={
                "part": "contentDetails",
                "id": channel_id,
            },
        )
        quota.channels_calls = 1
        items_ch = data.get("items", [])
        if not items_ch:
            return ([], quota) if return_quota else []

        uploads = (
            items_ch[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads:
            return ([], quota) if return_quota else []

        pl_data = await _playlist_items_get(client, playlist_id=uploads, max_results=limit)
        quota.playlist_items_calls = 1
        pl_items = pl_data.get("items", [])
        video_ids: list[str] = []
        for pl in pl_items:
            vid = pl.get("snippet", {}).get("resourceId", {}).get("videoId")
            if vid:
                video_ids.append(vid)
        if not video_ids:
            return ([], quota) if return_quota else []

        all_videos: list[dict] = []
        for group in chunked(video_ids, MAX_IDS_PER_REQUEST):
            vdata = await _videos_get(client, video_ids=group)
            quota.videos_list_calls += 1
            all_videos.extend(vdata.get("items", []))

    enrich_video_items(all_videos)
    if return_quota:
        return all_videos, quota
    return all_videos


async def fetch_channels_by_ids(channel_ids: list[str], return_call_count: bool = False):
    """批量按 channel id 拉取频道详情，单次最多 50 个。"""
    if not channel_ids:
        return [] if not return_call_count else ([], 0)

    _require_api_key()
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        all_items: list[dict] = []
        call_count = 0
        for group in chunked(channel_ids, MAX_IDS_PER_REQUEST):
            call_count += 1
            data = await _channels_get(
                client,
                params={
                    "part": "snippet,statistics",
                    "id": ",".join(group),
                },
            )
            all_items.extend(data.get("items", []))
    if return_call_count:
        return all_items, call_count
    return all_items


async def resolve_handles_to_channel_ids(
    client: httpx.AsyncClient,
    handles: list[str],
) -> tuple[dict[str, str], list[str]]:
    """
    forHandle 逐个解析，返回 {handle原样: yt_channel_id} 与失败说明列表。
    每次请求消耗 1 点配额。
    """
    errors: list[str] = []
    # 使用有序去重，保持确定性
    seen: set[str] = set()
    ordered_handles: list[str] = []
    for h in handles:
        if h not in seen:
            seen.add(h)
            ordered_handles.append(h)

    mapping: dict[str, str] = {}
    for h in ordered_handles:
        handle_param = h.lstrip("@")
        resp = await client.get(
            f"{YOUTUBE_API_BASE}/channels",
            params={
                "part": "id",
                "forHandle": handle_param,
                "key": settings.youtube_api_key,
            },
        )
        if resp.status_code != 200:
            errors.append(f"Handle {h}: API 错误 {resp.status_code}")
            continue
        data = resp.json()
        items = data.get("items", [])
        if not items:
            errors.append(f"Handle {h}: 未找到对应频道")
            continue
        cid = items[0].get("id")
        if cid:
            mapping[h] = cid
    return mapping, errors


async def fetch_channels_with_content_details(
    client: httpx.AsyncClient,
    channel_ids: list[str],
) -> tuple[list[dict], int]:
    """按 50 个一组拉取 snippet,statistics,contentDetails。返回 (items, 请求次数)。"""
    if not channel_ids:
        return [], 0
    all_items: list[dict] = []
    calls = 0
    for group in chunked(channel_ids, MAX_IDS_PER_REQUEST):
        calls += 1
        data = await _channels_get(
            client,
            params={
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(group),
            },
        )
        all_items.extend(data.get("items", []))
    return all_items, calls


async def fetch_videos_in_chunks(
    client: httpx.AsyncClient,
    video_ids: list[str],
) -> tuple[list[dict], int]:
    """按 50 个一组拉取视频详情。返回 (items, 请求次数)。"""
    if not video_ids:
        return [], 0
    # 去重且保持顺序
    seen: set[str] = set()
    ordered: list[str] = []
    for vid in video_ids:
        if vid not in seen:
            seen.add(vid)
            ordered.append(vid)

    all_items: list[dict] = []
    calls = 0
    for group in chunked(ordered, MAX_IDS_PER_REQUEST):
        calls += 1
        data = await _videos_get(client, video_ids=group)
        all_items.extend(data.get("items", []))
    return all_items, calls


@dataclass
class BulkAnalyzePipelineResult:
    """批量分析流水线结果，供路由层落库与记配额。"""

    channel_items: list[dict] = field(default_factory=list)
    video_items: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    for_handle_calls: int = 0
    channels_list_calls: int = 0
    playlist_items_calls: int = 0
    videos_list_calls: int = 0


async def _pipeline_fetch_channels_and_videos(
    client: httpx.AsyncClient,
    channel_id_list: list[str],
) -> BulkAnalyzePipelineResult:
    """
    步骤 C–E：批量 channels（含 contentDetails）→ 各频道 uploads 的 playlistItems → 批量 videos。
    """
    result = BulkAnalyzePipelineResult()
    if not channel_id_list:
        return result

    channel_items, ch_calls = await fetch_channels_with_content_details(client, channel_id_list)
    result.channel_items = channel_items
    result.channels_list_calls = ch_calls

    all_video_ids: list[str] = []
    for ch in channel_items:
        cid = ch.get("id")
        uploads = (
            ch.get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not cid or not uploads:
            if cid:
                result.errors.append(f"频道 {cid}: 无 uploads 播放列表，跳过视频拉取")
            continue

        pl_data = await _playlist_items_get(client, playlist_id=uploads, max_results=50)
        result.playlist_items_calls += 1
        for pl in pl_data.get("items", []):
            vid = pl.get("snippet", {}).get("resourceId", {}).get("videoId")
            if vid:
                all_video_ids.append(vid)

    video_items, v_calls = await fetch_videos_in_chunks(client, all_video_ids)
    result.video_items = video_items
    result.videos_list_calls = v_calls
    enrich_video_items(result.video_items)
    return result


async def run_bulk_analyze_pipeline(urls: str) -> BulkAnalyzePipelineResult:
    """
    高性价比批量抓取：解析 → forHandle → channels 批量 → playlistItems → videos 批量。
    不使用 Search API。
    """
    result = BulkAnalyzePipelineResult()
    _require_api_key()

    handles, direct_ids = extract_handles_and_channel_ids_from_bulk(urls)
    if not handles and not direct_ids:
        result.errors.append("未解析到任何有效的频道链接（需要 youtube.com/channel/UC… 或 youtube.com/@handle）")
        return result

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        if handles:
            mapping, herr = await resolve_handles_to_channel_ids(client, list(handles))
            result.errors.extend(herr)
            result.for_handle_calls = len(handles)
            for _h, cid in mapping.items():
                direct_ids.add(cid)

        channel_id_list = sorted(direct_ids)
        if not channel_id_list:
            result.errors.append("所有 Handle 均解析失败，且无直接频道 ID")
            return result

        inner = await _pipeline_fetch_channels_and_videos(client, channel_id_list)
        result.channel_items = inner.channel_items
        result.video_items = inner.video_items
        result.errors.extend(inner.errors)
        result.channels_list_calls = inner.channels_list_calls
        result.playlist_items_calls = inner.playlist_items_calls
        result.videos_list_calls = inner.videos_list_calls

    return result


async def run_refresh_pipeline_for_youtube_channel_ids(
    yt_channel_ids: list[str],
) -> BulkAnalyzePipelineResult:
    """
    监控池「一键更新」：仅按已知的 YouTube 频道 ID 执行 C–E，无解析与 forHandle。
    """
    result = BulkAnalyzePipelineResult()
    _require_api_key()
    unique = sorted({x.strip() for x in yt_channel_ids if x and x.strip()})
    if not unique:
        return result

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        inner = await _pipeline_fetch_channels_and_videos(client, unique)
        result.channel_items = inner.channel_items
        result.video_items = inner.video_items
        result.errors.extend(inner.errors)
        result.channels_list_calls = inner.channels_list_calls
        result.playlist_items_calls = inner.playlist_items_calls
        result.videos_list_calls = inner.videos_list_calls

    return result


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


def parse_comment_thread_item(item: dict) -> dict | None:
    """从 commentThreads.list 单条 item 解析为可入库字段。"""
    tl = item.get("snippet", {}).get("topLevelComment", {})
    if not tl:
        return None
    cid = tl.get("id")
    sn = tl.get("snippet", {})
    if not cid:
        return None
    text = sn.get("textDisplay") or sn.get("textOriginal") or ""
    return {
        "yt_comment_id": cid,
        "author_name": sn.get("authorDisplayName", "") or "",
        "author_avatar": sn.get("authorProfileImageUrl"),
        "text_original": text,
        "like_count": int(sn.get("likeCount", 0)),
        "published_at_raw": sn.get("publishedAt"),
    }


async def fetch_comment_threads_with_search(
    video_yt_id: str,
    keyword: str,
    *,
    max_total: int = 100,
) -> tuple[list[dict], int]:
    """
    调用 commentThreads.list（支持 searchTerms），最多收集 max_total 条。
    返回 (解析后的评论行列表, YouTube API 调用次数)。
    """
    _require_api_key()
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="keyword 不能为空")

    collected: list[dict] = []
    page_token: str | None = None
    api_calls = 0

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        while len(collected) < max_total:
            batch = min(100, max_total - len(collected))
            params: dict = {
                "part": "snippet",
                "videoId": video_yt_id,
                "searchTerms": keyword.strip(),
                "maxResults": batch,
                "textFormat": "plainText",
                "key": settings.youtube_api_key,
            }
            if page_token:
                params["pageToken"] = page_token

            resp = await client.get(f"{YOUTUBE_API_BASE}/commentThreads", params=params)
            api_calls += 1
            if resp.status_code != 200:
                raise _http_error(f"YouTube commentThreads API 调用失败：{resp.text}")

            data = resp.json()
            for item in data.get("items", []):
                row = parse_comment_thread_item(item)
                if row:
                    collected.append(row)
                if len(collected) >= max_total:
                    break

            page_token = data.get("nextPageToken")
            if not page_token or not data.get("items"):
                break

    return collected[:max_total], api_calls
