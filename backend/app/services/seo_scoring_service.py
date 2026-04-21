"""SEO 评分服务：对 YouTube 视频标题/描述/标签进行 SEO 质量评分。"""

from __future__ import annotations

import re


def score_seo(
    *,
    title: str,
    description: str,
    tags: list[str],
    target_keyword: str | None = None,
) -> dict:
    """
    对视频元数据进行 SEO 评分。

    评分维度：
    1. 标题评分（0-40分）：关键词包含、长度、吸引力
    2. 描述评分（0-30分）：关键词密度、长度、结构
    3. 标签评分（0-30分）：数量、相关性、关键词覆盖

    返回总分（0-100）+ 各维度分数 + 优化建议。
    """
    title = (title or "").strip()
    description = (description or "").strip()
    tags = [t.strip() for t in (tags or []) if t.strip()]
    kw = (target_keyword or "").strip().lower()

    # ── 标题评分 ──
    title_score = 0
    title_suggestions: list[str] = []
    title_lower = title.lower()

    # 长度评分（理想 40-60 字符）
    title_len = len(title)
    if 40 <= title_len <= 60:
        title_score += 15
    elif 30 <= title_len <= 70:
        title_score += 10
    elif title_len > 0:
        title_score += 5
        title_suggestions.append(f"标题长度 {title_len} 字符，建议 40-60 字符")
    else:
        title_suggestions.append("标题不能为空")

    # 关键词包含
    if kw:
        if kw in title_lower:
            title_score += 15
        else:
            title_suggestions.append(f"标题未包含目标关键词「{target_keyword}」")
            # 检查部分匹配
            kw_words = kw.split()
            matched = sum(1 for w in kw_words if w in title_lower)
            if matched > 0:
                title_score += int(10 * matched / len(kw_words))
    else:
        title_score += 10  # 无目标关键词时给基础分

    # 吸引力标记（数字、括号、感叹号、问号）
    attraction_patterns = [r"\d+", r"[【\[]", r"[！!]", r"[？?]"]
    attraction_matches = sum(1 for p in attraction_patterns if re.search(p, title))
    if attraction_matches >= 2:
        title_score += 10
    elif attraction_matches >= 1:
        title_score += 6
    else:
        title_suggestions.append("标题缺少吸引力元素（数字/括号/感叹号/问号）")

    title_score = min(40, title_score)

    # ── 描述评分 ──
    desc_score = 0
    desc_suggestions: list[str] = []
    desc_lower = description.lower()

    # 长度评分（理想 200-500 字符）
    desc_len = len(description)
    if 200 <= desc_len <= 500:
        desc_score += 10
    elif 100 <= desc_len <= 1000:
        desc_score += 6
    elif desc_len > 0:
        desc_score += 3
        desc_suggestions.append(f"描述长度 {desc_len} 字符，建议 200-500 字符")
    else:
        desc_suggestions.append("描述不能为空，YouTube 搜索会索引描述文本")

    # 关键词密度
    if kw and desc_len > 0:
        kw_count = desc_lower.count(kw)
        density = kw_count / (desc_len / 100)  # 每100字符出现次数
        if 1 <= density <= 3:
            desc_score += 10
        elif density > 0:
            desc_score += 5
            if density < 1:
                desc_suggestions.append(f"关键词「{target_keyword}」在描述中出现 {kw_count} 次，建议至少出现 2-3 次")
        else:
            desc_suggestions.append(f"描述未包含关键词「{target_keyword}」")
    else:
        desc_score += 5

    # 结构评分（换行/链接/时间戳）
    has_links = bool(re.search(r"https?://", description))
    has_timestamps = bool(re.search(r"\d+:\d{2}", description))
    has_newlines = "\n" in description
    structure_score = sum([has_links, has_timestamps, has_newlines])
    desc_score += min(10, structure_score * 4)
    if not has_newlines:
        desc_suggestions.append("描述建议分段（使用换行），提升可读性")
    if not has_timestamps:
        desc_suggestions.append("描述建议添加时间戳（如 0:00 开场），提升搜索曝光")

    desc_score = min(30, desc_score)

    # ── 标签评分 ──
    tag_score = 0
    tag_suggestions: list[str] = []
    tags_lower = [t.lower() for t in tags]

    # 数量评分（理想 8-15 个）
    tag_count = len(tags)
    if 8 <= tag_count <= 15:
        tag_score += 10
    elif 5 <= tag_count <= 20:
        tag_score += 6
    elif tag_count > 0:
        tag_score += 3
        tag_suggestions.append(f"标签数量 {tag_count} 个，建议 8-15 个")
    else:
        tag_suggestions.append("标签不能为空，标签帮助 YouTube 理解视频内容")

    # 关键词覆盖
    if kw:
        kw_in_tags = any(kw in t or kw.replace(" ", "") in t.replace(" ", "") for t in tags_lower)
        if kw_in_tags:
            tag_score += 10
        else:
            tag_suggestions.append(f"标签未包含目标关键词「{target_keyword}」")
            # 检查部分匹配
            kw_words = kw.split()
            matched_tags = sum(1 for w in kw_words if any(w in t for t in tags_lower))
            if matched_tags > 0:
                tag_score += int(6 * matched_tags / len(kw_words))
    else:
        tag_score += 6

    # 标签多样性（不同长度/组合）
    unique_lengths = len(set(len(t) for t in tags)) if tags else 0
    if unique_lengths >= 3:
        tag_score += 10
    elif unique_lengths >= 2:
        tag_score += 6
    else:
        tag_suggestions.append("标签建议包含不同长度的关键词（短词+长尾词）")

    tag_score = min(30, tag_score)

    # ── 总分 ──
    total_score = title_score + desc_score + tag_score

    all_suggestions = title_suggestions + desc_suggestions + tag_suggestions

    return {
        "total_score": total_score,
        "title_score": title_score,
        "title_max": 40,
        "description_score": desc_score,
        "description_max": 30,
        "tags_score": tag_score,
        "tags_max": 30,
        "suggestions": all_suggestions,
    }
