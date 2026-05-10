"""决策报告服务：为导航推荐品类计算6维度指标。"""

from __future__ import annotations


def enrich_recommendations_with_metrics(recommendations: list[dict]) -> list[dict]:
    """为每个推荐品类计算6维度指标，原地修改并返回。"""
    for rec in recommendations:
        rec["market_heat"] = _calc_market_heat(rec)
        rec["competition_intensity"] = _calc_competition(rec)
        rec["content_gap"] = _infer_content_gap(rec)
        rec["benchmark_channel"] = _pick_benchmark(rec)
        rec["cold_start_period"] = _estimate_cold_start(rec)
        rec["is_avoid"] = _check_avoid(rec)
        rec["cr4"] = _calc_cr4(rec)
    return recommendations


def _calc_market_heat(rec: dict) -> dict:
    """市场热度：基于频道数量和平均订阅数推算增速。"""
    channels = rec.get("top_channels", [])
    if not channels:
        return {"stars": 1, "growth_rate": "数据不足"}

    avg_subs = sum(ch.get("subscriber_count", 0) for ch in channels) / len(channels)
    # 频道多 + 平均订阅高 → 热度高
    if avg_subs > 500_000:
        stars = 5
        growth_rate = "+20%/月以上"
    elif avg_subs > 100_000:
        stars = 4
        growth_rate = "+10~20%/月"
    elif avg_subs > 10_000:
        stars = 3
        growth_rate = "+5~10%/月"
    elif avg_subs > 1_000:
        stars = 2
        growth_rate = "+2~5%/月"
    else:
        stars = 1
        growth_rate = "低速增长"

    # 频道数量加成
    if len(channels) >= 5:
        stars = min(5, stars + 1)

    return {"stars": stars, "growth_rate": growth_rate}


def _calc_competition(rec: dict) -> dict:
    """竞争强度：基于频道订阅分布推算新入局者成功率。"""
    channels = rec.get("top_channels", [])
    if not channels:
        return {"stars": 1, "success_rate": "数据不足"}

    subs_list = sorted([ch.get("subscriber_count", 0) for ch in channels], reverse=True)
    # 头部集中度越高 → 竞争越激烈 → 成功率越低
    top1 = subs_list[0] if subs_list else 0
    total = sum(subs_list)
    if total == 0:
        return {"stars": 1, "success_rate": "35%+"}

    top_ratio = top1 / total
    if top_ratio > 0.6:
        stars = 5
        success_rate = "<10%"
    elif top_ratio > 0.4:
        stars = 4
        success_rate = "10~20%"
    elif top_ratio > 0.25:
        stars = 3
        success_rate = "20~30%"
    elif top_ratio > 0.15:
        stars = 2
        success_rate = "30~40%"
    else:
        stars = 1
        success_rate = "40%+"

    return {"stars": stars, "success_rate": success_rate}


def _infer_content_gap(rec: dict) -> str:
    """内容缺口：基于频道标题模式推断饱和/不足的内容形式。"""
    channels = rec.get("top_channels", [])
    if not channels:
        return "数据不足"

    patterns = [ch.get("title_pattern", "") for ch in channels]
    tutorial_count = sum(1 for p in patterns if "教程" in p or "tutorial" in p.lower())
    number_count = sum(1 for p in patterns if "数字" in p)
    question_count = sum(1 for p in patterns if "疑问" in p)

    gaps = []
    if tutorial_count > len(channels) * 0.5:
        gaps.append("教程类饱和，实战/案例类供给不足")
    elif tutorial_count == 0:
        gaps.append("教程类内容空白，有机会切入")
    if number_count > len(channels) * 0.5:
        gaps.append("数字列表式饱和，深度分析类不足")
    if question_count == 0:
        gaps.append("疑问式标题稀缺，可尝试问答形式")

    if not gaps:
        # 通用推断
        if len(channels) < 3:
            gaps.append("内容供给不足，多种形式均有机会")
        else:
            gaps.append("长视频较饱和，Shorts 供给可能不足")

    return "；".join(gaps)


def _pick_benchmark(rec: dict) -> dict | None:
    """对标频道：选择订阅数适中（非头部巨头）的频道作为对标。"""
    channels = rec.get("top_channels", [])
    if not channels:
        return None

    sorted_chs = sorted(channels, key=lambda x: x.get("subscriber_count", 0), reverse=True)
    # 优先选第2-3名（非巨头但有规模）
    for ch in sorted_chs[1:3]:
        subs = ch.get("subscriber_count", 0)
        if 1_000 <= subs <= 500_000:
            return {
                "title": ch.get("title", ""),
                "subscribers": subs,
                "monthly_growth": _estimate_monthly_growth(subs),
            }

    # 退而选第1名
    if sorted_chs:
        top = sorted_chs[0]
        subs = top.get("subscriber_count", 0)
        return {
            "title": top.get("title", ""),
            "subscribers": subs,
            "monthly_growth": _estimate_monthly_growth(subs),
        }

    return None


def _estimate_cold_start(rec: dict) -> str:
    """预估冷启动期：基于竞争强度和频道规模。"""
    channels = rec.get("top_channels", [])
    if not channels:
        return "需进一步调研"

    avg_subs = sum(ch.get("subscriber_count", 0) for ch in channels) / len(channels)
    # 头部越大 → 冷启动越长
    if avg_subs > 500_000:
        return "6-12个月"
    if avg_subs > 100_000:
        return "3-6个月"
    if avg_subs > 10_000:
        return "2-4个月"
    return "1-3个月"


def _check_avoid(rec: dict) -> bool:
    """避开品类：CR4 > 60% 标记为避开。"""
    cr4 = _calc_cr4(rec)
    if cr4 is None:
        return False
    return cr4 > 60


def _calc_cr4(rec: dict) -> float | None:
    """计算头部集中度 CR4（前4名订阅占比）。"""
    channels = rec.get("top_channels", [])
    if len(channels) < 5:
        return None  # 样本不足

    subs_list = sorted([ch.get("subscriber_count", 0) for ch in channels], reverse=True)
    total = sum(subs_list)
    if total == 0:
        return None

    top4_sum = sum(subs_list[:4])
    return round(top4_sum / total * 100, 1)


def _estimate_monthly_growth(subs: int) -> str:
    """根据订阅规模估算月增速。"""
    if subs > 1_000_000:
        return "+1~3%/月"
    if subs > 100_000:
        return "+3~8%/月"
    if subs > 10_000:
        return "+5~15%/月"
    return "+10~25%/月"
