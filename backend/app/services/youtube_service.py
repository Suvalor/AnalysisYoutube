from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import re

import httpx
from fastapi import HTTPException, status

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

CHANNEL_ID_REGEX = re.compile(r"(?:youtube\.com/channel/)(UC[a-zA-Z0-9_-]{22})")
# 允许 handle 中包含 '-'，例如 @GiggleGalaxyTV-k9e
HANDLE_REGEX = re.compile(r"(?:youtube\.com/)(@[\w\.\-]+)")

# 旧版自定义频道 URL（不使用 search.list）：
# - https://www.youtube.com/c/CreatorName
# - https://www.youtube.com/user/CreatorName
CUSTOM_URL_REGEX = re.compile(r"(?:youtube\.com/)(?:c|user)/([a-zA-Z0-9_\.\-]+)")

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

    # /c/ /user/ 形式：当成 forHandle 的自定义名处理
    custom_match = CUSTOM_URL_REGEX.search(youtube_url)
    if custom_match:
        return {"handle": custom_match.group(1)}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="无法识别 YouTube URL，请使用 /channel/ID 或 /@handle 格式",
    )


def _require_api_key(youtube_api_key: str) -> None:
    if not (youtube_api_key or "").strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未配置 YouTube Data API Key（请在设置中心填写或配置环境变量 YOUTUBE_API_KEY）",
        )


def _http_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


def _youtube_api_failure_detail(resp: httpx.Response) -> tuple[int, str]:
    """
    解析 YouTube Data API 错误响应，返回 (建议 HTTP 状态码, 中文说明)。
    配额类错误映射为 429，其余为 502。
    """
    try:
        data = resp.json()
        err = data.get("error") or {}
        reasons = [str(e.get("reason", "")) for e in err.get("errors", []) if isinstance(e, dict)]
        msg = str(err.get("message", "") or "").strip() or resp.text[:800]
        quota_like = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "userRateLimitExceeded"}
        if any(r in quota_like for r in reasons):
            return (
                status.HTTP_429_TOO_MANY_REQUESTS,
                "YouTube API 配额不足或触发限流，请稍后再试或减少 search 类调用。",
            )
        return status.HTTP_502_BAD_GATEWAY, f"YouTube API 调用失败：{msg}"
    except Exception:
        return (
            status.HTTP_502_BAD_GATEWAY,
            f"YouTube API 调用失败（HTTP {resp.status_code}）：{resp.text[:500]}",
        )


def _raise_for_youtube_response(resp: httpx.Response) -> None:
    """非 200 时抛出 HTTPException，避免未处理响应拖垮上层。"""
    if resp.status_code == 200:
        return
    code, detail = _youtube_api_failure_detail(resp)
    raise HTTPException(status_code=code, detail=detail)


@dataclass
class DiscoverChannelsByKeywordResult:
    """关键词挖掘潜力频道：仅内存数据，供路由层序列化；不落库。"""

    items: list[dict]
    warnings: list[str]
    search_calls: int
    channels_list_calls: int


async def discover_channels_by_keyword(
    *,
    keyword: str,
    published_after_days: int,
    max_subscribers: int,
    max_results: int,
    youtube_api_key: str,
) -> DiscoverChannelsByKeywordResult:
    """
    两步策略：search.list（按播放量排序的视频）→ 去重 channelId → channels.list（snippet+statistics）→ 本地按订阅数过滤。
    search 单次约 100 quota，channels 按批每批 1 quota。
    """
    _require_api_key(youtube_api_key)
    kw = (keyword or "").strip()
    if not kw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="keyword 不能为空")

    mr = max(1, min(int(max_results), 50))
    warnings: list[str] = []
    now_utc = datetime.now(timezone.utc)
    published_after_dt = now_utc - timedelta(days=max(1, int(published_after_days)))
    published_after_iso = published_after_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    search_calls = 0
    channels_list_calls = 0

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
            resp = await client.get(
                f"{YOUTUBE_API_BASE}/search",
                params={
                    "part": "snippet",
                    "type": "video",
                    "q": kw,
                    "order": "viewCount",
                    "publishedAfter": published_after_iso,
                    "maxResults": mr,
                    "key": youtube_api_key,
                },
            )
            search_calls = 1
            _raise_for_youtube_response(resp)
            search_data = resp.json()

        channel_first_video: dict[str, str] = {}
        for item in search_data.get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            cid = (item.get("snippet") or {}).get("channelId")
            if isinstance(vid, str) and vid.strip() and isinstance(cid, str) and cid.strip():
                cid = cid.strip()
                if cid not in channel_first_video:
                    channel_first_video[cid] = vid.strip()

        if not channel_first_video:
            return DiscoverChannelsByKeywordResult(
                items=[],
                warnings=warnings,
                search_calls=search_calls,
                channels_list_calls=0,
            )

        ordered_cids = list(channel_first_video.keys())
        channel_rows: dict[str, dict] = {}

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
            for group in chunked(ordered_cids, MAX_IDS_PER_REQUEST):
                channels_list_calls += 1
                resp = await client.get(
                    f"{YOUTUBE_API_BASE}/channels",
                    params={
                        "part": "snippet,statistics",
                        "id": ",".join(group),
                        "key": youtube_api_key,
                    },
                )
                _raise_for_youtube_response(resp)
                payload = resp.json()
                for ch in payload.get("items", []):
                    cid = ch.get("id")
                    if isinstance(cid, str) and cid:
                        channel_rows[cid] = ch

        items: list[dict] = []
        for cid in ordered_cids:
            video_id = channel_first_video[cid]
            ch = channel_rows.get(cid)
            if not ch:
                warnings.append(f"频道 {cid}：channels.list 未返回详情，已跳过")
                continue
            stats = ch.get("statistics") or {}
            sub_raw = stats.get("subscriberCount")
            if sub_raw is None:
                warnings.append(f"频道 {cid}：订阅数未公开，已跳过")
                continue
            try:
                sub = int(sub_raw)
            except (TypeError, ValueError):
                warnings.append(f"频道 {cid}：订阅数字段异常，已跳过")
                continue
            if sub >= max_subscribers:
                continue
            try:
                total_views = int(stats.get("viewCount", 0))
            except (TypeError, ValueError):
                total_views = 0
            snippet = ch.get("snippet") or {}
            title = snippet.get("title") or ""
            thumbs = snippet.get("thumbnails") or {}
            high = thumbs.get("high") or {}
            default = thumbs.get("default") or {}
            thumbnail_url = high.get("url") or default.get("url")

            items.append(
                {
                    "yt_channel_id": cid,
                    "title": title,
                    "thumbnail_url": thumbnail_url,
                    "subscriber_count": sub,
                    "total_views": total_views,
                    "channel_url": f"https://www.youtube.com/channel/{cid}",
                    "viral_video_url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )

        return DiscoverChannelsByKeywordResult(
            items=items,
            warnings=warnings,
            search_calls=search_calls,
            channels_list_calls=channels_list_calls,
        )
    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"访问 YouTube API 网络异常：{e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"挖掘过程发生异常：{e}",
        ) from e


@dataclass
class BlueOceanRadarScanResult:
    """蓝海雷达扫描：仅内存数据，供路由层序列化；不落库。"""

    items: list[dict]
    warnings: list[str]
    search_calls: int
    videos_list_calls: int
    channels_list_calls: int


async def blue_ocean_radar_scan(
    *,
    keyword: str,
    published_after_days: int,
    max_subscribers: int,
    outlier_multiplier: float,
    youtube_api_key: str,
    video_duration: str | None = None,
) -> BlueOceanRadarScanResult:
    """
    蓝海雷达：search.list（播放量序）→ videos.list 精确播放量 → channels.list →
    粉丝上限与爆款系数过滤 → 按 outlier_score 降序。
    search 单次 maxResults=50；videos / channels 按批计费。
    """
    _require_api_key(youtube_api_key)
    kw = (keyword or "").strip()
    if not kw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="keyword 不能为空")

    days = max(1, int(published_after_days))
    warnings: list[str] = []
    now_utc = datetime.now(timezone.utc)
    published_after_dt = now_utc - timedelta(days=days)
    published_after_iso = published_after_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    search_calls = 0
    videos_list_calls = 0
    channels_list_calls = 0

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
            search_params: dict[str, str | int] = {
                "part": "snippet",
                "type": "video",
                "q": kw,
                "order": "viewCount",
                "publishedAfter": published_after_iso,
                "maxResults": 50,
                "key": youtube_api_key,
            }
            if video_duration in ("short", "medium", "long"):
                search_params["videoDuration"] = video_duration

            resp = await client.get(f"{YOUTUBE_API_BASE}/search", params=search_params)
            search_calls = 1
            _raise_for_youtube_response(resp)
            search_data = resp.json()

        pairs: list[tuple[str, str]] = []
        for item in search_data.get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            cid = (item.get("snippet") or {}).get("channelId")
            if isinstance(vid, str) and vid.strip() and isinstance(cid, str) and cid.strip():
                pairs.append((vid.strip(), cid.strip()))

        if not pairs:
            return BlueOceanRadarScanResult(
                items=[],
                warnings=warnings,
                search_calls=search_calls,
                videos_list_calls=0,
                channels_list_calls=0,
            )

        video_ids = [p[0] for p in pairs]
        view_by_vid: dict[str, int] = {}

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
            for group in chunked(video_ids, MAX_IDS_PER_REQUEST):
                videos_list_calls += 1
                data = await _videos_get(client, video_ids=group, youtube_api_key=youtube_api_key)
                for v in data.get("items", []):
                    vid = v.get("id")
                    stats = v.get("statistics") or {}
                    raw_vc = stats.get("viewCount")
                    if not isinstance(vid, str) or not vid.strip():
                        continue
                    vid = vid.strip()
                    if raw_vc is None:
                        warnings.append(f"视频 {vid}：无播放量字段，已跳过")
                        continue
                    try:
                        view_by_vid[vid] = int(raw_vc)
                    except (TypeError, ValueError):
                        warnings.append(f"视频 {vid}：播放量字段异常，已跳过")

            best_by_channel: dict[str, tuple[str, int]] = {}
            for vid, cid in pairs:
                views = view_by_vid.get(vid)
                if views is None:
                    continue
                prev = best_by_channel.get(cid)
                if prev is None or views > prev[1]:
                    best_by_channel[cid] = (vid, views)

            if not best_by_channel:
                return BlueOceanRadarScanResult(
                    items=[],
                    warnings=warnings,
                    search_calls=search_calls,
                    videos_list_calls=videos_list_calls,
                    channels_list_calls=0,
                )

            ordered_cids: list[str] = []
            seen_c: set[str] = set()
            for _vid, cid in pairs:
                if cid in best_by_channel and cid not in seen_c:
                    seen_c.add(cid)
                    ordered_cids.append(cid)

            channel_rows: dict[str, dict] = {}
            for group in chunked(ordered_cids, MAX_IDS_PER_REQUEST):
                channels_list_calls += 1
                resp_ch = await client.get(
                    f"{YOUTUBE_API_BASE}/channels",
                    params={
                        "part": "snippet,statistics",
                        "id": ",".join(group),
                        "key": youtube_api_key,
                    },
                )
                _raise_for_youtube_response(resp_ch)
                payload = resp_ch.json()
                for ch in payload.get("items", []):
                    cid = ch.get("id")
                    if isinstance(cid, str) and cid:
                        channel_rows[cid] = ch

        items: list[dict] = []
        for cid in ordered_cids:
            pair = best_by_channel.get(cid)
            if not pair:
                continue
            viral_vid, viral_views = pair
            ch = channel_rows.get(cid)
            if not ch:
                warnings.append(f"频道 {cid}：channels.list 未返回详情，已跳过")
                continue
            stats = ch.get("statistics") or {}
            sub_raw = stats.get("subscriberCount")
            if sub_raw is None:
                warnings.append(f"频道 {cid}：订阅数未公开，已跳过")
                continue
            try:
                sub = int(sub_raw)
            except (TypeError, ValueError):
                warnings.append(f"频道 {cid}：订阅数字段异常，已跳过")
                continue
            if sub >= max_subscribers:
                continue
            outlier_score = viral_views / max(sub, 1)
            if outlier_score < outlier_multiplier:
                continue
            try:
                total_views = int(stats.get("viewCount", 0))
            except (TypeError, ValueError):
                total_views = 0
            snippet = ch.get("snippet") or {}
            title = snippet.get("title") or ""
            thumbs = snippet.get("thumbnails") or {}
            high = thumbs.get("high") or {}
            default = thumbs.get("default") or {}
            thumbnail_url = high.get("url") or default.get("url")

            items.append(
                {
                    "yt_channel_id": cid,
                    "title": title,
                    "thumbnail_url": thumbnail_url,
                    "subscriber_count": sub,
                    "total_views": total_views,
                    "channel_url": f"https://www.youtube.com/channel/{cid}",
                    "viral_video_url": f"https://www.youtube.com/watch?v={viral_vid}",
                    "viral_view_count": viral_views,
                    "outlier_score": round(outlier_score, 4),
                }
            )

        items.sort(key=lambda x: float(x["outlier_score"]), reverse=True)

        return BlueOceanRadarScanResult(
            items=items,
            warnings=warnings,
            search_calls=search_calls,
            videos_list_calls=videos_list_calls,
            channels_list_calls=channels_list_calls,
        )
    except HTTPException:
        raise
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"访问 YouTube API 网络异常：{e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"蓝海雷达扫描发生异常：{e}",
        ) from e


def enrich_video_items(items: list[dict]) -> None:
    """为 videos.list 返回的条目补充时长等派生字段（原地修改）。"""
    for item in items:
        raw_duration = item.get("contentDetails", {}).get("duration")
        sec = duration_iso8601_to_seconds(raw_duration)
        item["_duration_sec"] = sec
        item["_duration_str"] = seconds_to_duration_str(sec)
        pub = item.get("snippet", {}).get("publishedAt")
        item["_parsed_published_at"] = parse_datetime(pub)


async def fetch_channel_info(identifier: dict[str, str], *, youtube_api_key: str) -> dict:
    """调用 channels 端点获取频道信息。"""
    _require_api_key(youtube_api_key)

    params = {
        "part": "snippet,statistics",
        "key": youtube_api_key,
    }
    if "channel_id" in identifier:
        params["id"] = identifier["channel_id"]
    else:
        params["forHandle"] = identifier["handle"].lstrip("@")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
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
    youtube_api_key: str,
) -> dict:
    q = {"key": youtube_api_key, **params}
    resp = await client.get(f"{YOUTUBE_API_BASE}/channels", params=q)
    if resp.status_code != 200:
        raise _http_error(f"YouTube channels API 调用失败：{resp.text}")
    return resp.json()


async def _playlist_items_get(
    client: httpx.AsyncClient,
    *,
    playlist_id: str,
    max_results: int,
    youtube_api_key: str,
) -> dict:
    resp = await client.get(
        f"{YOUTUBE_API_BASE}/playlistItems",
        params={
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": max(1, min(max_results, 50)),
            "key": youtube_api_key,
        },
    )
    if resp.status_code != 200:
        raise _http_error(f"YouTube playlistItems API 调用失败：{resp.text}")
    return resp.json()


async def _videos_get(
    client: httpx.AsyncClient,
    *,
    video_ids: list[str],
    youtube_api_key: str,
) -> dict:
    resp = await client.get(
        f"{YOUTUBE_API_BASE}/videos",
        params={
            "part": "contentDetails,status,statistics,snippet",
            "id": ",".join(video_ids),
            "key": youtube_api_key,
        },
    )
    _raise_for_youtube_response(resp)
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
    youtube_api_key: str,
    return_quota: bool = False,
) -> list[dict] | tuple[list[dict], FetchRecentVideosQuota]:
    """
    通过 uploads 播放列表 + videos.list 获取近期视频（不使用 Search API）。
    消耗：channels 1 + playlistItems 1 + videos 按 50 个分块。
    """
    _require_api_key(youtube_api_key)
    limit = max(1, min(limit, 50))
    quota = FetchRecentVideosQuota()

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        data = await _channels_get(
            client,
            params={
                "part": "contentDetails",
                "id": channel_id,
            },
            youtube_api_key=youtube_api_key,
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
        # uploads 应为字符串（上传播放列表 ID），若不是字符串则视为无可用 uploads。
        if isinstance(uploads, dict):
            uploads = uploads.get("playlistId") or uploads.get("id") or uploads.get("value")
        if not isinstance(uploads, str) or not uploads.strip():
            return ([], quota) if return_quota else []
        uploads = uploads.strip()

        quota.playlist_items_calls = 1
        try:
            pl_data = await _playlist_items_get(
                client,
                playlist_id=uploads,
                max_results=limit,
                youtube_api_key=youtube_api_key,
            )
        except HTTPException:
            # 单频道 uploads 无效/不可用时：降级为“无近期视频”，不阻断频道入库流程
            return ([], quota) if return_quota else []
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
            vdata = await _videos_get(client, video_ids=group, youtube_api_key=youtube_api_key)
            quota.videos_list_calls += 1
            all_videos.extend(vdata.get("items", []))

    enrich_video_items(all_videos)
    if return_quota:
        return all_videos, quota
    return all_videos


async def fetch_channels_by_ids(
    channel_ids: list[str],
    *,
    youtube_api_key: str,
    return_call_count: bool = False,
):
    """批量按 channel id 拉取频道详情，单次最多 50 个。"""
    if not channel_ids:
        return [] if not return_call_count else ([], 0)

    _require_api_key(youtube_api_key)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
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
                youtube_api_key=youtube_api_key,
            )
            all_items.extend(data.get("items", []))
    if return_call_count:
        return all_items, call_count
    return all_items


async def resolve_handles_to_channel_ids(
    client: httpx.AsyncClient,
    handles: list[str],
    *,
    youtube_api_key: str,
) -> tuple[dict[str, str], list[str]]:
    """
    forHandle 逐个解析，返回 {handle原样: yt_channel_id} 与失败说明列表。
    每次请求消耗 1 点配额。
    """
    errors: list[str] = []
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
                "key": youtube_api_key,
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
    *,
    youtube_api_key: str,
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
            youtube_api_key=youtube_api_key,
        )
        all_items.extend(data.get("items", []))
    return all_items, calls


async def fetch_videos_in_chunks(
    client: httpx.AsyncClient,
    video_ids: list[str],
    *,
    youtube_api_key: str,
) -> tuple[list[dict], int]:
    """按 50 个一组拉取视频详情。返回 (items, 请求次数)。"""
    if not video_ids:
        return [], 0
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
        data = await _videos_get(client, video_ids=group, youtube_api_key=youtube_api_key)
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
    *,
    youtube_api_key: str,
) -> BulkAnalyzePipelineResult:
    """
    步骤 C–E：批量 channels（含 contentDetails）→ 各频道 uploads 的 playlistItems → 批量 videos。
    """
    result = BulkAnalyzePipelineResult()
    if not channel_id_list:
        return result

    channel_items, ch_calls = await fetch_channels_with_content_details(
        client, channel_id_list, youtube_api_key=youtube_api_key
    )
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
        # uploads 应为字符串（上传播放列表 ID）
        if isinstance(uploads, dict):
            uploads = uploads.get("playlistId") or uploads.get("id") or uploads.get("value")
        if not cid or not isinstance(uploads, str) or not uploads.strip():
            if cid:
                result.errors.append(f"频道 {cid}: 无 uploads 播放列表，跳过视频拉取")
            continue
        uploads = uploads.strip()

        result.playlist_items_calls += 1
        try:
            pl_data = await _playlist_items_get(
                client,
                playlist_id=uploads,
                max_results=50,
                youtube_api_key=youtube_api_key,
            )
        except HTTPException as exc:
            result.errors.append(f"频道 {cid}: uploads playlistItems 拉取失败：{exc.detail}")
            continue
        for pl in pl_data.get("items", []):
            vid = pl.get("snippet", {}).get("resourceId", {}).get("videoId")
            if vid:
                all_video_ids.append(vid)

    video_items, v_calls = await fetch_videos_in_chunks(client, all_video_ids, youtube_api_key=youtube_api_key)
    result.video_items = video_items
    result.videos_list_calls = v_calls
    enrich_video_items(result.video_items)
    return result


async def run_bulk_analyze_pipeline(urls: str, *, youtube_api_key: str) -> BulkAnalyzePipelineResult:
    """
    高性价比批量抓取：解析 → forHandle → channels 批量 → playlistItems → videos 批量。
    不使用 Search API。
    """
    result = BulkAnalyzePipelineResult()
    _require_api_key(youtube_api_key)

    handles, direct_ids = extract_handles_and_channel_ids_from_bulk(urls)
    if not handles and not direct_ids:
        result.errors.append("未解析到任何有效的频道链接（需要 youtube.com/channel/UC… 或 youtube.com/@handle）")
        return result

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        if handles:
            mapping, herr = await resolve_handles_to_channel_ids(
                client, list(handles), youtube_api_key=youtube_api_key
            )
            result.errors.extend(herr)
            result.for_handle_calls = len(handles)
            for _h, cid in mapping.items():
                direct_ids.add(cid)

        channel_id_list = sorted(direct_ids)
        if not channel_id_list:
            result.errors.append("所有 Handle 均解析失败，且无直接频道 ID")
            return result

        inner = await _pipeline_fetch_channels_and_videos(client, channel_id_list, youtube_api_key=youtube_api_key)
        result.channel_items = inner.channel_items
        result.video_items = inner.video_items
        result.errors.extend(inner.errors)
        result.channels_list_calls = inner.channels_list_calls
        result.playlist_items_calls = inner.playlist_items_calls
        result.videos_list_calls = inner.videos_list_calls

    return result


async def run_refresh_pipeline_for_youtube_channel_ids(
    yt_channel_ids: list[str],
    *,
    youtube_api_key: str,
) -> BulkAnalyzePipelineResult:
    """
    监控池「一键更新」：仅按已知的 YouTube 频道 ID 执行 C–E，无解析与 forHandle。
    """
    result = BulkAnalyzePipelineResult()
    _require_api_key(youtube_api_key)
    unique = sorted({x.strip() for x in yt_channel_ids if x and x.strip()})
    if not unique:
        return result

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        inner = await _pipeline_fetch_channels_and_videos(client, unique, youtube_api_key=youtube_api_key)
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
    youtube_api_key: str,
    max_total: int = 100,
) -> tuple[list[dict], int]:
    """
    调用 commentThreads.list（支持 searchTerms），最多收集 max_total 条。
    返回 (解析后的评论行列表, YouTube API 调用次数)。
    """
    _require_api_key(youtube_api_key)
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="keyword 不能为空")

    collected: list[dict] = []
    page_token: str | None = None
    api_calls = 0

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        while len(collected) < max_total:
            batch = min(100, max_total - len(collected))
            params: dict = {
                "part": "snippet",
                "videoId": video_yt_id,
                "searchTerms": keyword.strip(),
                "maxResults": batch,
                "textFormat": "plainText",
                "key": youtube_api_key,
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
