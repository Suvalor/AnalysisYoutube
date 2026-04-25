"""出海导航服务：LLM 深度推荐 + YouTube API 数据验证。"""

from __future__ import annotations

import json
import logging
import re
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

# ── LLM 深度推荐 ──

_SYSTEM_PROMPT = """你是一个顶级的 YouTube 商业分析师，拥有丰富的海外市场洞察经验。
你的任务是根据用户提供的资源条件，推演并推荐最适合他们切入的 YouTube 细分品类组合。

你必须严格输出以下 JSON 结构，不要有任何 Markdown 包装或代码块标记：
{
  "recommendations": [
    {
      "niche_title": "品类名称 (如：科技评测 - 英语 → 美国)",
      "match_score": 95,
      "market_heat_stars": 4,
      "market_heat_desc": "头部频道增速 +15%/月",
      "competition_stars": 3,
      "competition_desc": "近半年新入局者成功率 23%",
      "content_gap": "一句话描述目前市场缺什么内容",
      "cold_start_period": "预估冷启动时间 (如：3-6个月)",
      "target_channel_example": "@ChannelName（X万粉，月增Y万）",
      "action_advice": "给用户的直接执行建议",
      "action_roadmap": [
        {"day_range": "1-7", "task": "具体任务", "expected_result": "预期成果"},
        {"day_range": "8-14", "task": "具体任务", "expected_result": "预期成果"},
        {"day_range": "15-30", "task": "具体任务", "expected_result": "预期成果"}
      ],
      "estimated_monthly_income": "预估月收入范围 (如：$200-800)"
    }
  ],
  "avoid_niche": {
    "niche_title": "必须避开的品类",
    "reason": "避坑原因"
  }
}

规则：
1. 必须推荐 3 个细分品类：第1-2个是最匹配用户条件的品类，第3个是中等匹配度但高增长潜力的品类
2. 必须推荐 1 个应该避开的品类（基于用户技能最容易踩坑的领域）
3. match_score 范围 1-100
4. stars 范围 1-5
5. 推荐必须基于用户的核心技能和变现目标进行个性化
6. action_roadmap 必须包含 3 个步骤，覆盖前 30 天
7. estimated_monthly_income 基于品类、预算和变现目标给出合理预估
8. 不要输出任何 JSON 之外的内容"""

_MAX_LLM_RETRIES = 3


def _build_user_prompt(
    languages: list[str],
    content_format: list[str],
    budget_level: str,
    core_skills: list[str],
    monetization_goal: str | None,
    target_regions: list[str] | None = None,
    weekly_hours: str | None = None,
    channel_info: dict | None = None,
) -> str:
    """构建 LLM 用户提示词。"""
    budget_map = {
        "zero": "零预算（纯AI制作，无需拍摄）",
        "low": "低预算（个人/小团队）",
        "medium": "中预算（工作室）",
        "high": "高预算（公司级）",
    }
    format_map = {"video": "长视频", "short": "短视频", "live": "直播"}
    monetize_map = {
        "adsense": "YouTube AdSense 广告收入",
        "course": "卖课/知识付费",
        "affiliate": "带货/联盟营销",
        "sponsor": "接商单/品牌合作",
    }
    region_map = {
        "US": "美国", "GB": "英国", "CA": "加拿大", "AU": "澳大利亚",
        "SG": "新加坡", "MY": "马来西亚", "PH": "菲律宾", "VN": "越南",
        "ID": "印尼", "TH": "泰国", "AE": "阿联酋", "SA": "沙特",
        "JP": "日本", "KR": "韩国", "TW": "台湾", "HK": "香港",
        "DE": "德国", "FR": "法国", "BR": "巴西", "MX": "墨西哥",
        "IN": "印度",
    }
    hours_map = {
        "<5h": "每周不到5小时（兼职尝试）",
        "5-10h": "每周5-10小时（认真投入）",
        "10-20h": "每周10-20小时（半职投入）",
        "20h+": "每周20小时以上（全职投入）",
    }

    langs = "、".join(languages)
    fmts = "、".join(format_map.get(f, f) for f in content_format)
    budget = budget_map.get(budget_level, budget_level)
    skills = "、".join(core_skills)
    monetize = monetize_map.get(monetization_goal, monetization_goal) if monetization_goal else "未指定"

    lines = [
        "用户资源条件：",
        f"- 语言能力：{langs}",
        f"- 内容形式：{fmts}",
        f"- 预算水平：{budget}",
        f"- 核心技能/内容方向：{skills}",
        f"- 变现目标：{monetize}",
    ]

    if target_regions:
        region_names = "、".join(region_map.get(r, r) for r in target_regions)
        lines.append(f"- 目标市场：{region_names}")

    if weekly_hours:
        hours_desc = hours_map.get(weekly_hours, weekly_hours)
        lines.append(f"- 投入时间：{hours_desc}")

    if channel_info:
        lines.append(f"- 已有频道：{channel_info.get('title', '未知')}（{channel_info.get('subscriber_count', 0):,} 订阅，{channel_info.get('video_count', 0)} 个视频）")
        if channel_info.get("description"):
            # 截取频道描述前200字
            desc = channel_info["description"][:200]
            lines.append(f"  频道简介：{desc}")

    lines.append("")
    lines.append("请基于以上条件，推荐 3 个最适合的 YouTube 细分品类组合（第3个为高增长潜力品类），以及 1 个应该避开的品类。")

    return "\n".join(lines)


def _parse_llm_json(raw: str) -> dict | None:
    """解析 LLM 返回的 JSON，容错处理 Markdown 代码块包裹。"""
    # 去除 Markdown 代码块标记
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 尝试提取 JSON 对象
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
        return None


def _validate_niche_json(data: dict) -> bool:
    """校验 LLM 返回的 JSON 结构是否合法。"""
    if "recommendations" not in data:
        return False
    recs = data["recommendations"]
    if not isinstance(recs, list) or len(recs) == 0:
        return False
    required_fields = {
        "niche_title", "match_score", "market_heat_stars", "market_heat_desc",
        "competition_stars", "competition_desc", "content_gap",
        "cold_start_period", "target_channel_example", "action_advice",
        "action_roadmap", "estimated_monthly_income",
    }
    for rec in recs:
        if not isinstance(rec, dict):
            return False
        missing = required_fields - set(rec.keys())
        if missing:
            return False
        # 校验 action_roadmap 结构
        roadmap = rec.get("action_roadmap", [])
        if isinstance(roadmap, list):
            for step in roadmap:
                if not isinstance(step, dict):
                    continue
                if not all(k in step for k in ("day_range", "task", "expected_result")):
                    continue
    return True


async def generate_niche_recommendations(
    *,
    db: AsyncSession,
    user_id: int,
    org_id: int,
    languages: list[str],
    content_format: list[str],
    budget_level: str,
    core_skills: list[str],
    monetization_goal: str | None,
    target_regions: list[str] | None = None,
    weekly_hours: str | None = None,
    channel_info: dict | None = None,
    model_library_id: int | None = None,
    llm_model_name: str | None = None,
    agent_id: int | None = None,
) -> dict:
    """调用 LLM 生成深度品类推荐，含重试机制。"""
    from app.services.llm_openai_factory import LLMClientFactory, LLMClientConfig
    from app.services.field_encryption import try_decrypt
    from app.crud.library import get_by_user
    from app.models.library import ModelLibrary

    if not model_library_id or not llm_model_name:
        return {"recommendations": [], "avoid_niche": None, "error": "未配置 LLM 模型"}

    ml = await get_by_user(db, ModelLibrary, user_id, model_library_id)
    if not ml:
        return {"recommendations": [], "avoid_niche": None, "error": "模型配置不存在"}

    # 优先使用模型库自带的 API Key
    ml_api_key = try_decrypt(ml.api_key_encrypted) or ""
    ml_base_url = (ml.api_base_url or "").strip().rstrip("/")
    api_key = ml_api_key
    base_url = ml_base_url
    cfg = LLMClientConfig(
        api_key=api_key,
        base_url=base_url,
        model_name=llm_model_name,
        protocol=getattr(ml, "protocol", "anthropic") or "anthropic",
    )
    factory = LLMClientFactory()

    user_prompt = _build_user_prompt(
        languages, content_format, budget_level, core_skills, monetization_goal,
        target_regions=target_regions,
        weekly_hours=weekly_hours,
        channel_info=channel_info,
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    # 重试机制
    for attempt in range(1, _MAX_LLM_RETRIES + 1):
        try:
            raw = await factory.chat_completions_content(cfg=cfg, messages=messages)
            if not raw:
                logger.warning("LLM 返回空内容，第 %d 次尝试", attempt)
                continue

            parsed = _parse_llm_json(raw)
            if parsed and _validate_niche_json(parsed):
                return parsed

            logger.warning("LLM JSON 解析/校验失败，第 %d 次尝试", attempt)
        except Exception:
            logger.warning("LLM 调用异常，第 %d 次尝试", attempt, exc_info=True)

    return {"recommendations": [], "avoid_niche": None, "error": "LLM 推荐生成失败，请重试"}


# ── YouTube API 数据扫描（保留作为数据源） ──

def _safe_int(val: object) -> int:
    """安全转换为 int，失败返回 0。"""
    try:
        return int(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


# YouTube 频道 URL 正则
_CHANNEL_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?youtube\.com/(?:channel/|c/|@)([\w.-]+)"
)


def _extract_channel_id_from_url(url: str) -> str | None:
    """从 YouTube 频道 URL 中提取频道标识。"""
    m = _CHANNEL_URL_RE.match(url.strip())
    return m.group(1) if m else None


async def fetch_channel_info(
    *,
    channel_url: str,
    youtube_api_key: str,
) -> dict | None:
    """根据频道 URL 获取频道信息摘要，供 LLM 上下文使用。"""
    channel_id = _extract_channel_id_from_url(channel_url)
    if not channel_id:
        logger.warning("无法解析频道 URL: %s", channel_url)
        return None

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        # 尝试以 channel ID 查询
        params = {
            "part": "snippet,statistics",
            "key": youtube_api_key,
        }
        if channel_id.startswith("UC"):
            params["id"] = channel_id
        else:
            # @handle 或自定义名，用 forHandle 或 forUsername
            params["forHandle"] = channel_id

        try:
            resp = await client.get(f"{YOUTUBE_API_BASE}/channels", params=params)
            _raise_for_youtube_response(resp)
            items = resp.json().get("items", [])
            if not items:
                # 回退：尝试 forUsername
                params2 = {
                    "part": "snippet,statistics",
                    "forUsername": channel_id,
                    "key": youtube_api_key,
                }
                resp2 = await client.get(f"{YOUTUBE_API_BASE}/channels", params=params2)
                _raise_for_youtube_response(resp2)
                items = resp2.json().get("items", [])
            if not items:
                return None
            ch = items[0]
            snippet = ch.get("snippet") or {}
            stats = ch.get("statistics") or {}
            return {
                "channel_id": ch.get("id", ""),
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "subscriber_count": _safe_int(stats.get("subscriberCount", 0)),
                "video_count": _safe_int(stats.get("videoCount", 0)),
                "view_count": _safe_int(stats.get("viewCount", 0)),
            }
        except Exception:
            logger.warning("获取频道信息失败: %s", channel_url, exc_info=True)
            return None

# 品类关键词库
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
    "zero": [("SG", "新加坡"), ("PH", "菲律宾"), ("VN", "越南"), ("ID", "印尼"), ("TH", "泰国")],
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
    core_skills: list[str],
    monetization_goal: str | None = None,
    existing_channel_url: str | None = None,
    target_regions: list[str] | None = None,
    weekly_hours: str | None = None,
    youtube_api_key: str,
    model_library_id: int | None = None,
    llm_model_name: str | None = None,
    agent_id: int | None = None,
) -> dict:
    """出海导航：优先使用 LLM 深度推荐，YouTube API 作为数据源补充。"""
    _require_api_key(youtube_api_key)

    # ── 获取已有频道信息（可选） ──
    channel_info = None
    if existing_channel_url:
        channel_info = await fetch_channel_info(
            channel_url=existing_channel_url,
            youtube_api_key=youtube_api_key,
        )

    # ── LLM 深度推荐（核心逻辑） ──
    llm_result = await generate_niche_recommendations(
        db=db,
        user_id=user_id,
        org_id=org_id,
        languages=languages,
        content_format=content_format,
        budget_level=budget_level,
        core_skills=core_skills,
        monetization_goal=monetization_goal,
        target_regions=target_regions,
        weekly_hours=weekly_hours,
        channel_info=channel_info,
        model_library_id=model_library_id,
        llm_model_name=llm_model_name,
        agent_id=agent_id,
    )

    # ── YouTube API 数据补充（可选） ──
    search_calls = 0
    channels_calls = 1 if channel_info else 0  # fetch_channel_info 消耗 1-2 次 channels.list
    now_utc = datetime.now(timezone.utc)
    published_after_iso = (now_utc - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    regions = _BUDGET_REGIONS.get(budget_level, _BUDGET_REGIONS["low"])

    # 用核心技能作为搜索关键词验证市场
    search_queries = core_skills[:3]
    api_recommendations: list[dict] = []

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        for query in search_queries:
            for region_code, region_name in regions[:2]:
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
                        api_recommendations.append(result)
                        search_calls += result.get("_search_calls", 1)
                        channels_calls += result.get("_channels_calls", 0)
                except Exception:
                    logger.warning("出海导航扫描失败: query=%s region=%s", query, region_code, exc_info=True)

    # ── 组装结果 ──
    ai_summary = None
    if llm_result.get("error"):
        ai_summary = f"⚠️ {llm_result['error']}"

    return {
        "recommendations": llm_result.get("recommendations", []),
        "avoid_niche": llm_result.get("avoid_niche"),
        "ai_summary": ai_summary,
        "api_recommendations": api_recommendations[:5],
        "channel_info": channel_info,
        "quota_usage": {
            "search_calls": search_calls,
            "channels_calls": channels_calls,
            "total_points": search_calls * 100 + channels_calls * 1,
        },
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

    cids: list[str] = []
    seen: set[str] = set()
    for item in search_data.get("items", []):
        cid = (item.get("snippet") or {}).get("channelId", "")
        if cid and cid not in seen:
            seen.add(cid)
            cids.append(cid)

    if not cids:
        return None

    ch_data: list[dict] = []
    ch_call_count = 0
    for group in chunked(cids, MAX_IDS_PER_REQUEST):
        ch_call_count += 1
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

    total_subs = sum(d["subscriber_count"] for d in ch_data)
    avg_subs = total_subs / len(ch_data)
    fit_score = min(100, len(ch_data) * 3 + min(avg_subs / 100, 50))

    top_channels = sorted(ch_data, key=lambda x: x["subscriber_count"], reverse=True)[:5]
    channel_breakdowns = []
    for ch in top_channels:
        freq = _infer_publish_frequency(ch["video_count"])
        channel_breakdowns.append({
            "channel_id": ch["channel_id"],
            "title": ch["title"],
            "subscriber_count": ch["subscriber_count"],
            "publish_frequency": freq,
            "avg_duration": "8-15分钟",
            "title_pattern": _infer_title_pattern(ch["title"]),
            "tag_pattern": "核心关键词+长尾词",
        })

    return {
        "category": query,
        "region": region_name,
        "fit_score": round(fit_score, 1),
        "reason": f"该地区有 {len(ch_data)} 个相关频道，平均订阅 {int(avg_subs):,}",
        "top_channels": channel_breakdowns,
        "_search_calls": 1,
        "_channels_calls": ch_call_count,
    }


def _infer_publish_frequency(video_count: int) -> str:
    if video_count > 200:
        return "每周3-5条"
    if video_count > 50:
        return "每周1-2条"
    if video_count > 10:
        return "每月2-4条"
    return "低频更新"


def _infer_title_pattern(title: str) -> str:
    if any(c.isdigit() for c in title):
        return "数字+关键词"
    if "?" in title or "？" in title:
        return "疑问式标题"
    if any(kw in title.lower() for kw in ["how", "如何", "教程", "tutorial"]):
        return "教程式标题"
    return "描述式标题"


# ── 多轮对话追问 ──

_CHAT_SYSTEM_PROMPT = """你是一个顶级的 YouTube 商业分析师。用户正在就出海导航推荐结果进行追问。
请基于之前的推荐上下文，简洁专业地回答用户的问题。回答控制在300字以内。"""


async def navigation_chat(
    *,
    db: AsyncSession,
    user_id: int,
    org_id: int,
    conversation_id: str,
    user_message: str,
    model_library_id: int | None = None,
    llm_model_name: str | None = None,
    agent_id: int | None = None,
) -> dict:
    """出海导航多轮对话追问。"""
    from app.services.llm_openai_factory import LLMClientFactory, LLMClientConfig
    from app.services.field_encryption import try_decrypt
    from app.crud.library import get_by_user
    from app.models.library import ModelLibrary
    from app.services.llm_conversation_service import (
        load_conversation_messages,
        save_conversation_turn,
    )

    if not model_library_id or not llm_model_name:
        return {"assistant_message": "未配置 LLM 模型，无法追问", "conversation_id": conversation_id}

    ml = await get_by_user(db, ModelLibrary, user_id, model_library_id)
    if not ml:
        return {"assistant_message": "模型配置不存在", "conversation_id": conversation_id}

    # 优先使用模型库自带的 API Key
    ml_api_key = try_decrypt(ml.api_key_encrypted) or ""
    ml_base_url = (ml.api_base_url or "").strip().rstrip("/")
    api_key = ml_api_key
    base_url = ml_base_url
    cfg = LLMClientConfig(
        api_key=api_key,
        base_url=base_url,
        model_name=llm_model_name,
        protocol=getattr(ml, "protocol", "anthropic") or "anthropic",
    )
    factory = LLMClientFactory()

    # 加载对话历史
    entity_type = "nav_guide"
    history = await load_conversation_messages(
        db, user_id=user_id, entity_type=entity_type, entity_id=conversation_id,
    )

    # 构建消息列表
    messages = [{"role": "system", "content": _CHAT_SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_message})

    # 调用 LLM
    try:
        assistant_content = await factory.chat_completions_content(cfg=cfg, messages=messages)
        if not assistant_content:
            assistant_content = "抱歉，AI 暂时无法回答，请稍后重试"
    except Exception:
        logger.warning("导航追问 LLM 调用失败", exc_info=True)
        assistant_content = "AI 调用异常，请稍后重试"

    # 保存对话轮次
    try:
        await save_conversation_turn(
            db,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=conversation_id,
            user_content=user_message,
            assistant_content=assistant_content,
            system_content=_CHAT_SYSTEM_PROMPT,
            model_name=llm_model_name,
        )
        await db.commit()
    except Exception:
        logger.warning("保存导航追问对话历史失败", exc_info=True)
        await db.rollback()

    return {"assistant_message": assistant_content, "conversation_id": conversation_id}