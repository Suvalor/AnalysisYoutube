"""关键词研究评分算法引擎。

纯函数模块，不包含 I/O（无 API 调用、无数据库）。
所有评分函数接收已获取的数据，返回评分结果。

算法设计原则：
1. YouTube Data API 不提供搜索量数据，需通过启发式指标推算
2. 评分公式：Keyword Score = Volume×0.30 + Competition_inv×0.25 + KD_inv×0.25 + Opportunity×0.20
3. 所有评分归一化到 0-100 区间
4. 趋势指标基于时间分布的发布频率变化
"""

from __future__ import annotations

import math


# ──────────────────────────────────────────────
# 1. 搜索量估算 (Search Volume Estimation)
# ──────────────────────────────────────────────

def calc_search_volume_score(
    *,
    total_results: int,
    related_keyword_count: int = 0,
    suggest_hit_count: int = 0,
) -> int:
    """计算搜索量评分（0-100）。

    基于 YouTube search.list 返回的 totalResults（估算值），
    结合相关词数量和 suggest API 命中数进行修正。

    算法：
    - 基础分：totalResults 对数映射到 0-80
      - 100 结果 → ~16分
      - 10K 结果 → ~53分
      - 1M 结果 → ~80分
    - 相关词修正：每10个相关词 +2分（上限10分）
    - Suggest 命中修正：每5个命中 +2分（上限10分）
    """
    # 基础分：对数映射
    if total_results <= 0:
        base_score = 0
    else:
        # log10(100)=2 → 16, log10(10000)=4 → 53, log10(1000000)=6 → 80
        base_score = min(80, max(0, (math.log10(max(total_results, 1)) - 1) * 16))

    # 相关词修正
    related_bonus = min(10, related_keyword_count / 10 * 2)

    # Suggest 命中修正
    suggest_bonus = min(10, suggest_hit_count / 5 * 2)

    return int(min(100, max(0, base_score + related_bonus + suggest_bonus)))


# ──────────────────────────────────────────────
# 2. 竞争度评分 (Competition Score)
# ──────────────────────────────────────────────

def calc_competition_score(
    *,
    channel_subscribers: list[int],
    video_view_counts: list[int],
    total_results: int,
) -> int:
    """计算竞争度评分（0-100，越高表示竞争越激烈）。

    算法：
    - 频道权威度：头部频道（订阅>10万）占比
    - 内容饱和度：搜索结果数对数映射
    - 播放量集中度：Top5 视频播放量占比（头部效应越强 → 竞争越激烈）

    权重：权威度 40% + 饱和度 30% + 集中度 30%
    """
    # 频道权威度
    if channel_subscribers:
        high_authority_count = sum(1 for s in channel_subscribers if s >= 100_000)
        authority_score = high_authority_count / len(channel_subscribers) * 100
    else:
        authority_score = 0

    # 内容饱和度
    if total_results > 0:
        saturation_score = min(100, math.log10(max(total_results, 1)) * 16)
    else:
        saturation_score = 0

    # 播放量集中度（Top5 占比）
    if video_view_counts and len(video_view_counts) >= 2:
        sorted_views = sorted(video_view_counts, reverse=True)
        top5 = sorted_views[:5]
        total_views = sum(sorted_views)
        if total_views > 0:
            concentration = sum(top5) / total_views
            # concentration 0.5-1.0 映射到 0-100
            concentration_score = max(0, min(100, (concentration - 0.3) / 0.7 * 100))
        else:
            concentration_score = 50
    else:
        concentration_score = 50

    return int(
        authority_score * 0.4 + saturation_score * 0.3 + concentration_score * 0.3
    )


# ──────────────────────────────────────────────
# 3. 关键词难度 (Keyword Difficulty)
# ──────────────────────────────────────────────

def calc_keyword_difficulty(
    *,
    top_video_views_per_sub: list[float],
    channel_authority_scores: list[float],
    avg_video_age_days: float,
) -> int:
    """计算关键词难度评分（0-100，越高越难排名）。

    KD 评估新内容在该关键词下获得排名的难度。

    算法：
    - 播放/订阅比：Top10 视频的 views/subscribers 比值
      - 比值高 → 爆款效应强 → 新内容有机会 → KD 低
      - 比值低 → 权威频道垄断 → KD 高
    - 频道权威度：头部频道的权威度均值
    - 内容新鲜度：平均视频年龄越短 → 竞争越活跃 → KD 高

    权重：播放比 40% + 权威度 35% + 新鲜度 25%
    """
    # 播放/订阅比 → 难度（反向：比值高 → 难度低）
    if top_video_views_per_sub:
        avg_ratio = sum(top_video_views_per_sub) / len(top_video_views_per_sub)
        # ratio 0-5 → 难度 100-0（sigmoid 映射）
        ratio_difficulty = 100 / (1 + math.exp(0.5 * (avg_ratio - 3)))
    else:
        ratio_difficulty = 50

    # 频道权威度 → 难度（正向：权威度高 → 难度高）
    if channel_authority_scores:
        avg_authority = sum(channel_authority_scores) / len(channel_authority_scores)
        authority_difficulty = avg_authority  # 已经是 0-100
    else:
        authority_difficulty = 50

    # 内容新鲜度 → 难度（正向：内容越新 → 竞争越活跃 → 难度高）
    if avg_video_age_days > 0:
        # 30天内 → 80-100, 90天 → 50, 365天 → 20
        freshness_difficulty = max(0, min(100, 100 - math.log10(max(avg_video_age_days, 1)) * 30))
    else:
        freshness_difficulty = 70

    return int(
        ratio_difficulty * 0.4 + authority_difficulty * 0.35 + freshness_difficulty * 0.25
    )


# ──────────────────────────────────────────────
# 4. 机会得分 (Opportunity Score)
# ──────────────────────────────────────────────

def calc_opportunity_score(
    *,
    search_volume_score: int,
    competition_score: int,
    keyword_difficulty: int,
    trend_direction: str,
    content_gap_ratio: float = 0.0,
) -> int:
    """计算机会得分（0-100，越高表示越值得投入）。

    机会 = 高搜索量 × 低竞争 × 低难度 × 趋势向好 × 内容缺口

    算法：
    - 需求供给比：搜索量 / (竞争度 + 1) → 归一化
    - 难度修正：KD 越低 → 修正系数越高
    - 趋势修正：rising → 1.2, stable → 1.0, declining → 0.7
    - 内容缺口修正：content_gap_ratio 越高 → 修正系数越高
    """
    # 需求供给比
    demand_supply = search_volume_score / max(competition_score + 1, 1)
    # 归一化到 0-100（demand_supply 0-100 映射）
    base_opportunity = min(100, demand_supply * 2)

    # 难度修正（KD 越低 → 修正越高）
    difficulty_modifier = (100 - keyword_difficulty) / 100  # 0-1

    # 趋势修正
    trend_modifiers = {"rising": 1.2, "stable": 1.0, "declining": 0.7}
    trend_modifier = trend_modifiers.get(trend_direction, 1.0)

    # 内容缺口修正（0-0.5 → 1.0-1.5）
    gap_modifier = 1.0 + content_gap_ratio * 0.5

    raw_score = base_opportunity * difficulty_modifier * trend_modifier * gap_modifier
    return int(min(100, max(0, raw_score)))


# ──────────────────────────────────────────────
# 5. 趋势方向判定
# ──────────────────────────────────────────────

def calc_trend_direction(
    *,
    trend_data: list[dict],
) -> str:
    """根据趋势数据判定关键词趋势方向。

    输入：[{period, days, result_count}, ...]
    输出："rising" | "stable" | "declining"

    算法：比较短期（7天）和长期（90天/180天）的日均发布量。
    - 日均 = result_count / days
    - 短期日均 / 长期日均 > 1.3 → rising
    - 短期日均 / 长期日均 < 0.7 → declining
    - 其余 → stable
    """
    if len(trend_data) < 2:
        return "stable"

    # 找短期和长期数据点
    short_term = None
    long_term = None
    for t in trend_data:
        days = t.get("days", 0)
        if days <= 7:
            short_term = t
        if days >= 90:
            if long_term is None or days > long_term.get("days", 0):
                long_term = t

    if not short_term or not long_term:
        # 退而求其次：用第一个和最后一个
        short_term = trend_data[0]
        long_term = trend_data[-1]

    short_daily = short_term.get("result_count", 0) / max(short_term.get("days", 1), 1)
    long_daily = long_term.get("result_count", 0) / max(long_term.get("days", 1), 1)

    if long_daily <= 0:
        return "stable" if short_daily <= 0 else "rising"

    ratio = short_daily / long_daily
    if ratio > 1.3:
        return "rising"
    elif ratio < 0.7:
        return "declining"
    else:
        return "stable"


# ──────────────────────────────────────────────
# 6. 频道权威度评分
# ──────────────────────────────────────────────

def calc_channel_authority(
    *,
    subscriber_count: int,
    video_count: int,
    total_views: int,
) -> float:
    """计算单个频道的权威度评分（0-100）。

    算法：
    - 订阅数贡献（50%）：对数映射
    - 播放量贡献（30%）：对数映射
    - 活跃度贡献（20%）：视频数对数映射
    """
    # 订阅数贡献
    if subscriber_count > 0:
        sub_score = min(100, math.log10(max(subscriber_count, 1)) * 20)
    else:
        sub_score = 0

    # 播放量贡献
    if total_views > 0:
        view_score = min(100, math.log10(max(total_views, 1)) * 10)
    else:
        view_score = 0

    # 活跃度贡献
    if video_count > 0:
        activity_score = min(100, math.log10(max(video_count, 1)) * 30)
    else:
        activity_score = 0

    return sub_score * 0.5 + view_score * 0.3 + activity_score * 0.2


# ──────────────────────────────────────────────
# 7. 内容缺口检测
# ──────────────────────────────────────────────

def calc_content_gap_ratio(
    *,
    video_durations_sec: list[int],
    avg_views_by_duration: dict[str, int],
) -> float:
    """计算内容缺口比率（0-1，越高表示缺口越大）。

    检测某个时长区间是否供给不足但需求高（平均播放量高）。

    时长分类：
    - short: ≤60s
    - medium: 61-600s
    - long: >600s

    算法：找出供给占比最低但平均播放量最高的时长区间，
    缺口比率 = (1 - 最低供给占比) × (最高播放 / 总播放)
    """
    if not video_durations_sec:
        return 0.0

    # 统计各时长区间供给占比
    buckets = {"short": 0, "medium": 0, "long": 0}
    for dur in video_durations_sec:
        if dur <= 60:
            buckets["short"] += 1
        elif dur <= 600:
            buckets["medium"] += 1
        else:
            buckets["long"] += 1

    total = sum(buckets.values())
    if total == 0:
        return 0.0

    supply_ratios = {k: v / total for k, v in buckets.items()}

    # 找供给最低的区间
    min_supply_bucket = min(supply_ratios, key=supply_ratios.get)
    min_supply = supply_ratios[min_supply_bucket]

    # 该区间的播放量占比
    views = avg_views_by_duration.get(min_supply_bucket, 0)
    total_views = sum(avg_views_by_duration.values())
    if total_views <= 0:
        return 0.0

    demand_ratio = views / total_views

    # 缺口 = (1 - 供给占比) × 需求占比
    gap = (1 - min_supply) * demand_ratio
    return min(1.0, max(0.0, gap))


# ──────────────────────────────────────────────
# 8. 综合评分
# ──────────────────────────────────────────────

def calc_keyword_score(
    *,
    search_volume_score: int,
    competition_score: int,
    keyword_difficulty: int,
    opportunity_score: int,
) -> int:
    """计算关键词综合评分（0-100）。

    公式：Volume×0.30 + Competition_inv×0.25 + KD_inv×0.25 + Opportunity×0.20

    其中 Competition_inv = 100 - Competition（竞争度越低越好）
    其中 KD_inv = 100 - KD（难度越低越好）
    """
    competition_inv = 100 - competition_score
    kd_inv = 100 - keyword_difficulty

    raw = (
        search_volume_score * 0.30
        + competition_inv * 0.25
        + kd_inv * 0.25
        + opportunity_score * 0.20
    )
    return int(min(100, max(0, raw)))
