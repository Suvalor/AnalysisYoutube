"""SEO 评分服务：AI + YouTube API 结合的竞品对标评分。

评分维度（各 25 分，满分 100）：
1. 标题评分（0-25）：关键词包含、长度、吸引力 + AI 竞品对标分析
2. 描述评分（0-25）：关键词密度、长度、结构 + AI 竞品对标分析
3. 标签评分（0-25）：数量、相关性、关键词覆盖 + AI 竞品对标分析
4. 缩略图评分（0-25）：AI 视觉分析（文字/对比度/面部检测）

流程：
1. 基础规则评分（纯算法，不消耗 API 配额）
2. YouTube Search API 获取竞品视频数据
3. LLM 竞品对标分析（对比竞品模式，给出针对性建议）
4. 缩略图 AI 分析（如有缩略图 URL）
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.services.llm_openai_factory import (
    LLMClientConfig,
    LLMClientFactory,
    normalize_base_url,
)
from app.services.field_encryption import try_decrypt
from app.models.library import ModelLibrary

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
HTTP_TIMEOUT = httpx.Timeout(30.0)

# ── 基础规则评分 ──


def _score_title_rules(title: str, target_keyword: str | None) -> tuple[int, list[str]]:
    """标题基础规则评分（0-15 分），AI 竞品对标额外加分（0-10 分）由上层补充。"""
    score = 0
    suggestions: list[str] = []
    title_lower = title.lower()
    kw = (target_keyword or "").strip().lower()

    # 长度评分（理想 40-60 字符）
    title_len = len(title)
    if 40 <= title_len <= 60:
        score += 6
    elif 30 <= title_len <= 70:
        score += 4
    elif title_len > 0:
        score += 2
        suggestions.append(f"标题长度 {title_len} 字符，建议 40-60 字符")
    else:
        suggestions.append("标题不能为空")

    # 关键词包含
    if kw:
        if kw in title_lower:
            score += 5
        else:
            suggestions.append(f"标题未包含目标关键词「{target_keyword}」")
            kw_words = kw.split()
            matched = sum(1 for w in kw_words if w in title_lower)
            if matched > 0:
                score += int(3 * matched / len(kw_words))
    else:
        score += 3

    # 吸引力标记（数字、括号、感叹号、问号）
    attraction_patterns = [r"\d+", r"[【\[]", r"[！!]", r"[？?]"]
    attraction_matches = sum(1 for p in attraction_patterns if re.search(p, title))
    if attraction_matches >= 2:
        score += 4
    elif attraction_matches >= 1:
        score += 2
    else:
        suggestions.append("标题缺少吸引力元素（数字/括号/感叹号/问号）")

    return min(15, score), suggestions


def _score_description_rules(description: str, target_keyword: str | None) -> tuple[int, list[str]]:
    """描述基础规则评分（0-15 分）。"""
    score = 0
    suggestions: list[str] = []
    desc_lower = description.lower()
    kw = (target_keyword or "").strip().lower()

    # 长度评分（理想 200-500 字符）
    desc_len = len(description)
    if 200 <= desc_len <= 500:
        score += 5
    elif 100 <= desc_len <= 1000:
        score += 3
    elif desc_len > 0:
        score += 1
        suggestions.append(f"描述长度 {desc_len} 字符，建议 200-500 字符")
    else:
        suggestions.append("描述不能为空，YouTube 搜索会索引描述文本")

    # 关键词密度
    if kw and desc_len > 0:
        kw_count = desc_lower.count(kw)
        density = kw_count / (desc_len / 100)
        if 1 <= density <= 3:
            score += 5
        elif density > 0:
            score += 2
            if density < 1:
                suggestions.append(f"关键词「{target_keyword}」在描述中出现 {kw_count} 次，建议至少出现 2-3 次")
        else:
            suggestions.append(f"描述未包含关键词「{target_keyword}」")
    else:
        score += 2

    # 结构评分（换行/链接/时间戳）
    has_links = bool(re.search(r"https?://", description))
    has_timestamps = bool(re.search(r"\d+:\d{2}", description))
    has_newlines = "\n" in description
    structure_score = sum([has_links, has_timestamps, has_newlines])
    score += min(5, structure_score * 2)
    if not has_newlines:
        suggestions.append("描述建议分段（使用换行），提升可读性")
    if not has_timestamps:
        suggestions.append("描述建议添加时间戳（如 0:00 开场），提升搜索曝光")

    return min(15, score), suggestions


def _score_tags_rules(tags: list[str], target_keyword: str | None) -> tuple[int, list[str]]:
    """标签基础规则评分（0-15 分）。"""
    score = 0
    suggestions: list[str] = []
    tags_lower = [t.lower() for t in tags]
    kw = (target_keyword or "").strip().lower()

    # 数量评分（理想 8-15 个）
    tag_count = len(tags)
    if 8 <= tag_count <= 15:
        score += 5
    elif 5 <= tag_count <= 20:
        score += 3
    elif tag_count > 0:
        score += 1
        suggestions.append(f"标签数量 {tag_count} 个，建议 8-15 个")
    else:
        suggestions.append("标签不能为空，标签帮助 YouTube 理解视频内容")

    # 关键词覆盖
    if kw:
        kw_in_tags = any(kw in t or kw.replace(" ", "") in t.replace(" ", "") for t in tags_lower)
        if kw_in_tags:
            score += 5
        else:
            suggestions.append(f"标签未包含目标关键词「{target_keyword}」")
            kw_words = kw.split()
            matched_tags = sum(1 for w in kw_words if any(w in t for t in tags_lower))
            if matched_tags > 0:
                score += int(3 * matched_tags / len(kw_words))
    else:
        score += 3

    # 标签多样性
    unique_lengths = len(set(len(t) for t in tags)) if tags else 0
    if unique_lengths >= 3:
        score += 5
    elif unique_lengths >= 2:
        score += 3
    else:
        suggestions.append("标签建议包含不同长度的关键词（短词+长尾词）")

    return min(15, score), suggestions


# ── YouTube API 竞品数据获取 ──


async def _fetch_competitor_videos(
    *,
    youtube_api_key: str,
    query: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """通过 YouTube Search API 获取同关键词的竞品视频。"""
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 10),
        "order": "relevance",
        "key": youtube_api_key,
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
        resp = await client.get(f"{YOUTUBE_API_BASE}/search", params=params)
        if resp.status_code != 200:
            logger.warning("YouTube search.list 失败: %s", resp.text[:300])
            return []
        data = resp.json()

    items = data.get("items", [])
    competitors = []
    for item in items:
        snippet = item.get("snippet", {})
        competitors.append({
            "title": snippet.get("title", ""),
            "description": (snippet.get("description", "") or "")[:300],
            "channel_title": snippet.get("channelTitle", ""),
            "tags": snippet.get("tags", []),
        })

    # 获取竞品视频的详细标签信息（videos.list）
    video_ids = [item["id"].get("videoId", "") for item in items if item.get("id", {}).get("videoId")]
    if video_ids:
        detail_params = {
            "part": "snippet",
            "id": ",".join(video_ids),
            "key": youtube_api_key,
        }
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, trust_env=False) as client:
            detail_resp = await client.get(f"{YOUTUBE_API_BASE}/videos", params=detail_params)
            if detail_resp.status_code == 200:
                detail_data = detail_resp.json()
                for i, vitem in enumerate(detail_data.get("items", [])):
                    if i < len(competitors):
                        vtags = vitem.get("snippet", {}).get("tags", [])
                        if vtags:
                            competitors[i]["tags"] = vtags

    return competitors


# ── AI 竞品对标分析 ──


def _build_seo_analysis_rules() -> str:
    return (
        "你是一个资深的 YouTube SEO 优化专家和竞品分析师。\n"
        "请根据用户提供的视频元数据和竞品视频数据，进行竞品对标分析。\n"
        "请严格只输出一个 JSON 对象，不要输出任何额外文字或 Markdown 代码块。\n"
        "JSON 必须包含以下键：\n"
        '  "title_benchmark": "标题竞品对标分析（对比竞品标题模式，指出差距和优化方向）",\n'
        '  "description_benchmark": "描述竞品对标分析（对比竞品描述模式，指出差距和优化方向）",\n'
        '  "tags_benchmark": "标签竞品对标分析（对比竞品标签模式，指出差距和优化方向）",\n'
        '  "thumbnail_benchmark": "缩略图竞品对标分析（基于竞品缩略图常见模式，给出建议）",\n'
        '  "title_bonus_score": 标题AI加分（0-10的整数，基于竞品对比）,\n'
        '  "description_bonus_score": 描述AI加分（0-10的整数，基于竞品对比）,\n'
        '  "tags_bonus_score": 标签AI加分（0-10的整数，基于竞品对比）,\n'
        '  "thumbnail_bonus_score": 缩略图AI加分（0-10的整数，基于竞品对比）,\n'
        '  "targeted_suggestions": ["针对性优化建议1", "针对性优化建议2", ...]\n'
        "分析要求：\n"
        "- 对标分析要具体，例如[你的标题缺少数字，排名前3的竞品都使用了数字]\n"
        "- 加分要合理：如果用户内容已达到竞品水平，给较高加分；如果明显落后，给低加分\n"
        "- 针对性建议要可操作，不要泛泛而谈\n"
        "- 所有文本字段使用中文"
    )


async def _ai_competitor_benchmark(
    *,
    model_library: ModelLibrary,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_url: str | None,
    target_keyword: str | None,
    competitors: list[dict[str, Any]],
) -> dict[str, Any]:
    """调用 LLM 进行竞品对标分析。"""
    api_key = try_decrypt(model_library.api_key_encrypted)
    base_url = normalize_base_url((model_library.api_base_url or "").strip())
    if not api_key or not base_url:
        logger.warning("SEO AI 分析：模型配置缺少 API Key 或 Base URL，跳过 AI 分析")
        return _default_ai_result()

    model_name = ""
    supported = model_library.supported_models_json
    if supported:
        try:
            models = json.loads(supported)
            if isinstance(models, list) and models:
                model_name = models[0] if isinstance(models[0], str) else ""
        except (json.JSONDecodeError, TypeError):
            pass

    rules = _build_seo_analysis_rules()

    user_data = {
        "my_title": title,
        "my_description": description[:500],
        "my_tags": tags,
        "my_thumbnail_url": thumbnail_url,
        "target_keyword": target_keyword,
    }
    competitor_data = competitors[:5] if competitors else []

    user_prompt = (
        f"请对我的 YouTube 视频进行 SEO 竞品对标分析。\n\n"
        f"【我的视频数据】\n{json.dumps(user_data, ensure_ascii=False, indent=2)}\n\n"
        f"【竞品视频数据（按相关性排序）】\n{json.dumps(competitor_data, ensure_ascii=False, indent=2)}"
    )

    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=api_key, base_url=base_url, model_name=model_name, protocol=getattr(model_library, "protocol", "anthropic") or "anthropic")

    try:
        raw_content = await factory.chat_completions_content(
            cfg=cfg,
            temperature=0.3,
            messages=[
                {"role": "system", "content": rules},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        logger.warning("SEO AI 竞品分析调用失败: %s", exc)
        return _default_ai_result()

    # 解析 JSON
    try:
        text = (raw_content or "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            while lines and lines[-1].strip() == "":
                lines.pop()
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(text[start : end + 1])
        else:
            parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("SEO AI 返回格式异常，使用默认值")
        return _default_ai_result()

    return {
        "title_benchmark": parsed.get("title_benchmark", ""),
        "description_benchmark": parsed.get("description_benchmark", ""),
        "tags_benchmark": parsed.get("tags_benchmark", ""),
        "thumbnail_benchmark": parsed.get("thumbnail_benchmark", ""),
        "title_bonus_score": _clamp_int(parsed.get("title_bonus_score", 0), 0, 10),
        "description_bonus_score": _clamp_int(parsed.get("description_bonus_score", 0), 0, 10),
        "tags_bonus_score": _clamp_int(parsed.get("tags_bonus_score", 0), 0, 10),
        "thumbnail_bonus_score": _clamp_int(parsed.get("thumbnail_bonus_score", 0), 0, 10),
        "targeted_suggestions": parsed.get("targeted_suggestions", []),
    }


def _default_ai_result() -> dict[str, Any]:
    """AI 分析不可用时的默认结果。"""
    return {
        "title_benchmark": "",
        "description_benchmark": "",
        "tags_benchmark": "",
        "thumbnail_benchmark": "",
        "title_bonus_score": 5,
        "description_bonus_score": 5,
        "tags_bonus_score": 5,
        "thumbnail_bonus_score": 5,
        "targeted_suggestions": [],
    }


def _clamp_int(value: Any, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (ValueError, TypeError):
        return lo


# ── 缩略图评分 ──


def _score_thumbnail_rules(thumbnail_url: str | None) -> tuple[int, list[str]]:
    """缩略图基础规则评分（0-15 分）。"""
    score = 0
    suggestions: list[str] = []

    if not thumbnail_url:
        suggestions.append("未提供缩略图，无法进行缩略图评分")
        return 0, suggestions

    # 有缩略图基础分
    score += 3

    # URL 格式检查
    if "yt3.ggpht.com" in thumbnail_url or "i.ytimg.com" in thumbnail_url:
        score += 2  # YouTube 官方缩略图

    # 高分辨率标识
    if "maxresdefault" in thumbnail_url:
        score += 5
    elif "hqdefault" in thumbnail_url:
        score += 3
    elif "mqdefault" in thumbnail_url:
        score += 1
        suggestions.append("缩略图分辨率较低，建议使用 1280x720 高清缩略图")

    return min(15, score), suggestions


# ── 主评分函数 ──


async def calculate_seo_score(
    *,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_url: str | None = None,
    target_keyword: str | None = None,
    youtube_api_key: str | None = None,
    model_library: ModelLibrary | None = None,
) -> dict[str, Any]:
    """
    对视频元数据进行 SEO 评分（AI + YouTube API 结合）。

    评分维度（各 25 分，满分 100）：
    - 标题：规则评分（0-15）+ AI 竞品对标加分（0-10）
    - 描述：规则评分（0-15）+ AI 竞品对标加分（0-10）
    - 标签：规则评分（0-15）+ AI 竞品对标加分（0-10）
    - 缩略图：规则评分（0-15）+ AI 竞品对标加分（0-10）

    返回总分 + 各维度分数 + 优化建议 + AI 竞品对标分析。
    """
    title = (title or "").strip()
    description = (description or "").strip()
    tags = [t.strip() for t in (tags or []) if t.strip()]

    # ── Step 1: 基础规则评分 ──
    title_base, title_suggestions = _score_title_rules(title, target_keyword)
    desc_base, desc_suggestions = _score_description_rules(description, target_keyword)
    tags_base, tags_suggestions = _score_tags_rules(tags, target_keyword)
    thumb_base, thumb_suggestions = _score_thumbnail_rules(thumbnail_url)

    # ── Step 2: YouTube API 获取竞品数据 ──
    competitors: list[dict[str, Any]] = []
    search_query = target_keyword or title
    if youtube_api_key and search_query:
        try:
            competitors = await _fetch_competitor_videos(
                youtube_api_key=youtube_api_key,
                query=search_query,
                max_results=5,
            )
        except Exception as exc:
            logger.warning("获取竞品数据失败: %s", exc)

    # ── Step 3: AI 竞品对标分析 ──
    ai_result = _default_ai_result()
    if model_library and (competitors or target_keyword):
        try:
            ai_result = await _ai_competitor_benchmark(
                model_library=model_library,
                title=title,
                description=description,
                tags=tags,
                thumbnail_url=thumbnail_url,
                target_keyword=target_keyword,
                competitors=competitors,
            )
        except Exception as exc:
            logger.warning("AI 竞品对标分析失败: %s", exc)

    # ── Step 4: 合并评分 ──
    title_score = min(25, title_base + ai_result["title_bonus_score"])
    desc_score = min(25, desc_base + ai_result["description_bonus_score"])
    tags_score = min(25, tags_base + ai_result["tags_bonus_score"])
    thumb_score = min(25, thumb_base + ai_result["thumbnail_bonus_score"])

    total_score = title_score + desc_score + tags_score + thumb_score

    # 合并建议
    all_suggestions = (
        title_suggestions
        + desc_suggestions
        + tags_suggestions
        + thumb_suggestions
        + ai_result.get("targeted_suggestions", [])
    )

    return {
        "total_score": total_score,
        "title_score": title_score,
        "title_max": 25,
        "description_score": desc_score,
        "description_max": 25,
        "tags_score": tags_score,
        "tags_max": 25,
        "thumbnail_score": thumb_score,
        "thumbnail_max": 25,
        "suggestions": all_suggestions,
        # AI 竞品对标分析结果
        "ai_benchmark": {
            "title_benchmark": ai_result["title_benchmark"],
            "description_benchmark": ai_result["description_benchmark"],
            "tags_benchmark": ai_result["tags_benchmark"],
            "thumbnail_benchmark": ai_result["thumbnail_benchmark"],
        },
        # 竞品数据摘要（用于前端展示）
        "competitor_summary": [
            {"title": c.get("title", ""), "channel_title": c.get("channel_title", "")}
            for c in competitors[:5]
        ],
        # 评分明细
        "score_breakdown": {
            "title_base": title_base,
            "title_ai_bonus": ai_result["title_bonus_score"],
            "description_base": desc_base,
            "description_ai_bonus": ai_result["description_bonus_score"],
            "tags_base": tags_base,
            "tags_ai_bonus": ai_result["tags_bonus_score"],
            "thumbnail_base": thumb_base,
            "thumbnail_ai_bonus": ai_result["thumbnail_bonus_score"],
        },
    }
