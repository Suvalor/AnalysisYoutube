"""出海导航服务：根据用户资源推荐品类+地区组合，并拆解 Top 频道内容策略。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.youtube_service import (
    YOUTUBE_API_BASE,
    HTTP_TIMEOUT,
    _require_api_key,
    _raise_for_youtube_response,
    chunked,
    MAX_IDS_PER_REQUEST,
)

logger = logging.getLogger(__name__)

# 品类关键词库：按语言和内容形式推荐
_CATEGORY_KEYWORDS_BY_LANGUAGE: dict[str, list[str]] = {
    "中文": ["中文教程", "Chinese", "Mandarin"],
    "英语": ["tutorial", "how to", "tips", "guide"],
    "日语": ["日本語", "Japanese"],
    "韩语": ["한국어", "Korean"],
    "阿拉伯语": ["Arabic", "عربي"],
    "西班牙语": ["Español", "Spanish"],
    "法语": ["Français", "French"],
    "德语": ["Deutsch", "German"],
    "葡萄牙语": ["Português", "Portuguese"],
    "印地语": ["Hindi", "हिन्दी"],
}

# 预算水平 → 推荐地区
_BUDGET_REGIONS: dict[str, list[tuple[str, str]]] = {
    "low": [("SG", "新加坡"), ("PH", "菲律宾"), ("VN", "越南"), ("ID", "印尼"), ("TH", "泰国")],
    "medium": [("SG", "新加坡"), ("MY", "马来西亚"), ("AE", "阿联酋"), ("TW", "台湾"), ("HK", "香港")],
    "high": [("US", "美国"), ("GB", "英国"), ("CA", "加拿大"), ("AU", "澳大利亚"), ("JP", "日本")],
}

# 内容形式 → 搜索修饰词
_FORMAT_MODIFIERS: dict[str, str] = {
    "video": "",
    "short": "shorts",
    "live": "live stream",
}


async def navigation_guide(
    *,
    db: AsyncSession,
    user_id: int,
    org_id: int,
    languages: list[str],
    content_format: list[str],
    budget_level: str,
    youtube_api_key: str,
    model_library_id: int | None = None,
    llm_model_name: str | None = None,
    agent_id: int | None = None,
) -> dict:
    """
    出海导航：根据用户语言能力、内容形式、预算水平，
    推荐最适合的品类+地区组合，并给出 Top 频道内容策略拆解。
    """
    _require_api_key(youtube_api_key)

    # 生成搜索关键词组合
    search_queries = _build_search_queries(languages, content_format)
    # 获取推荐地区
    regions = _BUDGET_REGIONS.get(budget_level, _BUDGET_REGIONS["low"])

    recommendations: list[dict] = []
    now_utc = datetime.now(timezone.utc)
    published_after_iso = (now_utc - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        for query in search_queries[:5]:  # 最多 5 个查询
            for region_code, region_name in regions[:3]:  # 每个查询最多 3 个地区
                try:
                    result = await _scan_region_category(
                        client=client,
                        query=query,
                        region_code=region_code,
                        region_name=region_name,
                        published_after_iso=published_after_iso,
                        youtube_api_key=youtube_api_key,
                    )
                    if result:
                        recommendations.append(result)
                except Exception:
                    logger.warning("出海导航扫描失败: query=%s region=%s", query, region_code, exc_info=True)

    # 按匹配度排序
    recommendations.sort(key=lambda x: x["fit_score"], reverse=True)

    # 可选 LLM 总结
    ai_summary = None
    if model_library_id and llm_model_name and agent_id and recommendations:
        ai_summary = await _generate_ai_summary(
            db=db,
            user_id=user_id,
            org_id=org_id,
            languages=languages,
            budget_level=budget_level,
            recommendations=recommendations,
            model_library_id=model_library_id,
            llm_model_name=llm_model_name,
            agent_id=agent_id,
        )

    return {
        "recommendations": recommendations[:10],
        "ai_summary": ai_summary,
    }


def _build_search_queries(languages: list[str], content_format: list[str]) -> list[str]:
    """根据语言和内容形式生成搜索关键词。"""
    queries: list[str] = []
    for lang in languages:
        keywords = _CATEGORY_KEYWORDS_BY_LANGUAGE.get(lang, [lang])
        for kw in keywords:
            for fmt in content_format:
                modifier = _FORMAT_MODIFIERS.get(fmt, "")
                query = f"{kw} {modifier}".strip()
                if query not in queries:
                    queries.append(query)
    return queries


async def _scan_region_category(
    *,
    client: httpx.AsyncClient,
    query: str,
    region_code: str,
    region_name: str,
    published_after_iso: str,
    youtube_api_key: str,
) -> dict | None:
    """扫描单个地区+品类组合，返回推荐结果。"""
    resp = await client.get(
        f"{YOUTUBE_API_BASE}/search",
        params={
            "part": "snippet",
            "type": "video",
            "q": query,
            "order": "viewCount",
            "publishedAfter": published_after_iso,
            "maxResults": 15,
            "regionCode": region_code,
            "key": youtube_api_key,
        },
    )
    _raise_for_youtube_response(resp)
    search_data = resp.json()

    # 提取频道 ID
    cids: list[str] = []
    seen: set[str] = set()
    for item in search_data.get("items", []):
        cid = (item.get("snippet") or {}).get("channelId", "")
        if cid and cid not in seen:
            seen.add(cid)
            cids.append(cid)

    if not cids:
        return None

    # channels.list
    ch_data: list[dict] = []
    for group in chunked(cids, MAX_IDS_PER_REQUEST):
        resp_ch = await client.get(
            f"{YOUTUBE_API_BASE}/channels",
            params={
                "part": "snippet,statistics",
                "id": ",".join(group),
                "key": youtube_api_key,
            },
        )
        _raise_for_youtube_response(resp_ch)
        for ch in resp_ch.json().get("items", []):
            snippet = ch.get("snippet") or {}
            stats = ch.get("statistics") or {}
            try:
                subs = int(stats.get("subscriberCount", 0))
            except (TypeError, ValueError):
                subs = 0
            try:
                views = int(stats.get("viewCount", 0))
            except (TypeError, ValueError):
                views = 0
            try:
                video_count = int(stats.get("videoCount", 0))
            except (TypeError, ValueError):
                video_count = 0
            ch_data.append({
                "channel_id": ch.get("id", ""),
                "title": snippet.get("title", ""),
                "subscriber_count": subs,
                "total_views": views,
                "video_count": video_count,
                "description": snippet.get("description", ""),
            })

    if not ch_data:
        return None

    # 计算匹配度
    total_subs = sum(d["subscriber_count"] for d in ch_data)
    avg_subs = total_subs / len(ch_data)
    # 频道数量多 + 有高订阅频道 = 高匹配度
    fit_score = min(100, len(ch_data) * 3 + min(avg_subs / 100, 50))

    # Top 频道策略拆解
    top_channels = sorted(ch_data, key=lambda x: x["subscriber_count"], reverse=True)[:5]
    channel_breakdowns = []
    for ch in top_channels:
        # 简单的策略推断
        freq = _infer_publish_frequency(ch["video_count"])
        channel_breakdowns.append({
            "channel_id": ch["channel_id"],
            "title": ch["title"],
            "subscriber_count": ch["subscriber_count"],
            "publish_frequency": freq,
            "avg_duration": "8-15分钟",  # 需要更详细的视频分析才能准确
            "title_pattern": _infer_title_pattern(ch["title"]),
            "tag_pattern": "核心关键词+长尾词",
        })

    return {
        "category": query,
        "region": region_name,
        "fit_score": round(fit_score, 1),
        "reason": f"该地区有 {len(ch_data)} 个相关频道，平均订阅 {int(avg_subs):,}",
        "top_channels": channel_breakdowns,
    }


def _infer_publish_frequency(video_count: int) -> str:
    """根据视频总数推断发布频率。"""
    if video_count > 200:
        return "每周3-5条"
    if video_count > 50:
        return "每周1-2条"
    if video_count > 10:
        return "每月2-4条"
    return "低频更新"


def _infer_title_pattern(title: str) -> str:
    """简单推断标题模式。"""
    if any(c.isdigit() for c in title):
        return "数字+关键词"
    if "?" in title or "？" in title:
        return "疑问式标题"
    if any(kw in title.lower() for kw in ["how", "如何", "教程", "tutorial"]):
        return "教程式标题"
    return "描述式标题"


async def _generate_ai_summary(
    *,
    db: AsyncSession,
    user_id: int,
    org_id: int,
    languages: list[str],
    budget_level: str,
    recommendations: list[dict],
    model_library_id: int,
    llm_model_name: str,
    agent_id: int,
) -> str | None:
    """可选：调用 LLM 生成出海导航总结。"""
    try:
        from app.services.youtube_ai_service import _call_llm
        from app.services.config_manager import resolve_integration_config

        icfg = await resolve_integration_config(db, org_id=org_id)
        prompt = (
            f"用户语言能力：{', '.join(languages)}\n"
            f"预算水平：{budget_level}\n"
            f"推荐结果：{recommendations[:5]}\n\n"
            "请用中文总结：1) 最推荐的品类和地区 2) 需要注意的风险 3) 下一步行动建议"
        )
        result = await _call_llm(
            db=db,
            user_id=user_id,
            org_id=org_id,
            prompt=prompt,
            model_library_id=model_library_id,
            llm_model_name=llm_model_name,
            agent_id=agent_id,
        )
        return result
    except Exception:
        logger.warning("出海导航 AI 总结生成失败", exc_info=True)
        return None
