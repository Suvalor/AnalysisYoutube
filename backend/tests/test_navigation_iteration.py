"""出海导航迭代测试：配额守卫 + 6维度决策指标 + schema 扩展。"""

from __future__ import annotations

import pytest


# ── quota_guard_service 纯逻辑测试 ──

def test_quota_check_result_defaults():
    """QuotaCheckResult 默认值正确。"""
    from app.services.quota_guard_service import QuotaCheckResult
    r = QuotaCheckResult(allowed=True, remaining=5000, estimated_cost=1500, today_used=5000, today_total=10000)
    assert r.allowed is True
    assert r.remaining == 5000
    assert r.estimated_cost == 1500
    assert r.today_used == 5000
    assert r.today_total == 10000


def test_quota_check_allowed_when_sufficient():
    """剩余配额充足时 allowed=True。"""
    from app.services.quota_guard_service import DAILY_QUOTA_LIMIT
    assert DAILY_QUOTA_LIMIT == 10_000


# ── navigation_report_service 纯逻辑测试 ──

def test_calc_market_heat_high_subs():
    """高订阅频道 → 市场热度5星。"""
    from app.services.navigation_report_service import _calc_market_heat
    rec = {"top_channels": [
        {"subscriber_count": 600_000, "title": "A"},
        {"subscriber_count": 400_000, "title": "B"},
        {"subscriber_count": 300_000, "title": "C"},
        {"subscriber_count": 200_000, "title": "D"},
        {"subscriber_count": 100_000, "title": "E"},
    ]}
    result = _calc_market_heat(rec)
    assert result["stars"] == 5
    assert "20%" in result["growth_rate"]


def test_calc_market_heat_low_subs():
    """低订阅频道 → 市场热度1-2星。"""
    from app.services.navigation_report_service import _calc_market_heat
    rec = {"top_channels": [
        {"subscriber_count": 500, "title": "A"},
    ]}
    result = _calc_market_heat(rec)
    assert result["stars"] <= 2


def test_calc_market_heat_empty():
    """空频道 → 数据不足。"""
    from app.services.navigation_report_service import _calc_market_heat
    result = _calc_market_heat({"top_channels": []})
    assert result["stars"] == 1
    assert result["growth_rate"] == "数据不足"


def test_calc_competition_high_concentration():
    """头部集中度高 → 竞争5星。"""
    from app.services.navigation_report_service import _calc_competition
    rec = {"top_channels": [
        {"subscriber_count": 900_000, "title": "A"},
        {"subscriber_count": 50_000, "title": "B"},
        {"subscriber_count": 30_000, "title": "C"},
        {"subscriber_count": 20_000, "title": "D"},
    ]}
    result = _calc_competition(rec)
    assert result["stars"] == 5
    assert "10%" in result["success_rate"]


def test_calc_competition_low_concentration():
    """头部集中度低 → 竞争1-2星。"""
    from app.services.navigation_report_service import _calc_competition
    rec = {"top_channels": [
        {"subscriber_count": 10_000, "title": "A"},
        {"subscriber_count": 10_000, "title": "B"},
        {"subscriber_count": 10_000, "title": "C"},
        {"subscriber_count": 10_000, "title": "D"},
        {"subscriber_count": 10_000, "title": "E"},
        {"subscriber_count": 10_000, "title": "F"},
    ]}
    result = _calc_competition(rec)
    assert result["stars"] <= 2


def test_infer_content_gap_tutorial_saturated():
    """教程类过半 → 标记饱和。"""
    from app.services.navigation_report_service import _infer_content_gap
    rec = {"top_channels": [
        {"title_pattern": "教程式标题"},
        {"title_pattern": "教程式标题"},
        {"title_pattern": "教程式标题"},
    ]}
    result = _infer_content_gap(rec)
    assert "饱和" in result


def test_pick_benchmark_mid_tier():
    """选择第2-3名作为对标。"""
    from app.services.navigation_report_service import _pick_benchmark
    rec = {"top_channels": [
        {"title": "巨头", "subscriber_count": 1_000_000},
        {"title": "中等", "subscriber_count": 50_000},
        {"title": "小", "subscriber_count": 5_000},
    ]}
    result = _pick_benchmark(rec)
    assert result is not None
    assert result["title"] == "中等"


def test_pick_benchmark_empty():
    """空频道返回 None。"""
    from app.services.navigation_report_service import _pick_benchmark
    assert _pick_benchmark({"top_channels": []}) is None


def test_estimate_cold_start():
    """冷启动期估算。"""
    from app.services.navigation_report_service import _estimate_cold_start
    rec_high = {"top_channels": [{"subscriber_count": 600_000}]}
    assert "6-12" in _estimate_cold_start(rec_high)

    rec_low = {"top_channels": [{"subscriber_count": 500}]}
    assert "1-3" in _estimate_cold_start(rec_low)

    assert _estimate_cold_start({"top_channels": []}) == "需进一步调研"


def test_check_avoid_cr4_over_60():
    """CR4 > 60% 标记为避开。"""
    from app.services.navigation_report_service import _check_avoid, _calc_cr4
    rec = {"top_channels": [
        {"subscriber_count": 800, "title": "A"},
        {"subscriber_count": 100, "title": "B"},
        {"subscriber_count": 50, "title": "C"},
        {"subscriber_count": 30, "title": "D"},
        {"subscriber_count": 20, "title": "E"},
    ]}
    cr4 = _calc_cr4(rec)
    assert cr4 is not None
    assert cr4 > 60
    assert _check_avoid(rec) is True


def test_check_avoid_cr4_under_60():
    """CR4 < 60% 不标记避开。"""
    from app.services.navigation_report_service import _check_avoid, _calc_cr4
    # 6个频道均匀分布 → CR4 = 4/6 = 66.7%，仍>60
    # 用10个频道 → CR4 = 4/10 = 40% < 60
    rec = {"top_channels": [
        {"subscriber_count": 100, "title": str(i)} for i in range(10)
    ]}
    cr4 = _calc_cr4(rec)
    assert cr4 is not None
    assert cr4 <= 60
    assert _check_avoid(rec) is False


def test_calc_cr4_insufficient_sample():
    """频道数<5时 CR4 返回 None。"""
    from app.services.navigation_report_service import _calc_cr4
    rec = {"top_channels": [
        {"subscriber_count": 100},
        {"subscriber_count": 200},
    ]}
    assert _calc_cr4(rec) is None


def test_enrich_recommendations_with_metrics():
    """enrich_recommendations_with_metrics 完整流程。"""
    from app.services.navigation_report_service import enrich_recommendations_with_metrics
    recs = [{"category": "test", "region": "US", "fit_score": 80, "reason": "test",
             "top_channels": [
                 {"subscriber_count": 200_000, "title": "A", "title_pattern": "教程式标题"},
                 {"subscriber_count": 50_000, "title": "B", "title_pattern": "描述式标题"},
                 {"subscriber_count": 10_000, "title": "C", "title_pattern": "数字+关键词"},
                 {"subscriber_count": 5_000, "title": "D", "title_pattern": "描述式标题"},
                 {"subscriber_count": 2_000, "title": "E", "title_pattern": "描述式标题"},
             ]}]
    result = enrich_recommendations_with_metrics(recs)
    assert len(result) == 1
    r = result[0]
    assert "market_heat" in r
    assert "competition_intensity" in r
    assert "content_gap" in r
    assert "benchmark_channel" in r
    assert "cold_start_period" in r
    assert "is_avoid" in r
    assert "cr4" in r


# ── Schema 测试 ──

def test_navigation_quota_usage_schema():
    """NavigationQuotaUsage schema 正确解析。"""
    from app.schemas.radar import NavigationQuotaUsage
    u = NavigationQuotaUsage(search_calls=5, channels_calls=10, total_points=510)
    assert u.search_calls == 5
    assert u.channels_calls == 10
    assert u.total_points == 510


def test_quota_check_info_schema():
    """QuotaCheckInfo schema 正确解析。"""
    from app.schemas.radar import QuotaCheckInfo
    q = QuotaCheckInfo(allowed=True, remaining=8000, estimated_cost=1500, today_used=2000, today_total=10000)
    assert q.allowed is True
    assert q.remaining == 8000


def test_market_heat_schema():
    """MarketHeat schema 验证。"""
    from app.schemas.radar import MarketHeat
    m = MarketHeat(stars=4, growth_rate="+10~20%/月")
    assert m.stars == 4
    assert m.growth_rate == "+10~20%/月"


def test_market_heat_stars_range():
    """MarketHeat stars 范围 1-5。"""
    from app.schemas.radar import MarketHeat
    with pytest.raises(Exception):
        MarketHeat(stars=0, growth_rate="test")
    with pytest.raises(Exception):
        MarketHeat(stars=6, growth_rate="test")


def test_competition_intensity_schema():
    """CompetitionIntensity schema 验证。"""
    from app.schemas.radar import CompetitionIntensity
    c = CompetitionIntensity(stars=3, success_rate="20~30%")
    assert c.stars == 3


def test_benchmark_channel_schema():
    """BenchmarkChannel schema 验证。"""
    from app.schemas.radar import BenchmarkChannel
    b = BenchmarkChannel(title="Test", subscribers=50000, monthly_growth="+5~15%/月")
    assert b.title == "Test"
    assert b.subscribers == 50000


def test_category_recommendation_with_dimensions():
    """CategoryRecommendation 包含6维度字段。"""
    from app.schemas.radar import CategoryRecommendation
    rec = CategoryRecommendation(
        category="科技", region="美国", fit_score=85.0, reason="test",
        top_channels=[],
        market_heat={"stars": 4, "growth_rate": "+10~20%/月"},
        competition_intensity={"stars": 3, "success_rate": "20~30%"},
        content_gap="Shorts不足",
        benchmark_channel={"title": "Test", "subscribers": 50000, "monthly_growth": "+5~15%/月"},
        cold_start_period="3-6个月",
        is_avoid=False,
        cr4=45.2,
    )
    assert rec.market_heat is not None
    assert rec.market_heat.stars == 4
    assert rec.is_avoid is False
    assert rec.cr4 == 45.2


def test_navigation_guide_response_with_quota():
    """NavigationGuideResponse 包含配额信息。"""
    from app.schemas.radar import NavigationGuideResponse
    resp = NavigationGuideResponse(
        recommendations=[],
        ai_summary=None,
        quota_usage={"search_calls": 5, "channels_calls": 10, "total_points": 510},
        quota_check={"allowed": True, "remaining": 8000, "estimated_cost": 0, "today_used": 2000, "today_total": 10000},
    )
    assert resp.quota_usage is not None
    assert resp.quota_usage.total_points == 510
    assert resp.quota_check is not None
    assert resp.quota_check.remaining == 8000