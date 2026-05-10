"""出海导航重构测试：LLM 深度推荐 + JSON 解析 + Schema 验证 + 新增字段。"""

from __future__ import annotations

import pytest

from app.services.radar_navigation_service import (
    _build_user_prompt,
    _parse_llm_json,
    _validate_niche_json,
    _extract_channel_id_from_url,
)


# ── _build_user_prompt 测试 ──

def test_build_user_prompt_basic():
    """基本用户提示词构建。"""
    prompt = _build_user_prompt(
        languages=["中文", "英语"],
        content_format=["video", "short"],
        budget_level="low",
        core_skills=["编程", "科技评测"],
        monetization_goal="adsense",
    )
    assert "中文" in prompt
    assert "英语" in prompt
    assert "编程" in prompt
    assert "科技评测" in prompt
    assert "低预算" in prompt
    assert "AdSense" in prompt


def test_build_user_prompt_zero_budget():
    """零预算选项。"""
    prompt = _build_user_prompt(
        languages=["英语"],
        content_format=["short"],
        budget_level="zero",
        core_skills=["AI"],
        monetization_goal=None,
    )
    assert "零预算" in prompt
    assert "未指定" in prompt


def test_build_user_prompt_monetization():
    """变现目标映射。"""
    prompt = _build_user_prompt(
        languages=["中文"],
        content_format=["video"],
        budget_level="high",
        core_skills=["美妆"],
        monetization_goal="affiliate",
    )
    assert "带货" in prompt


def test_build_user_prompt_with_target_regions():
    """目标地区字段。"""
    prompt = _build_user_prompt(
        languages=["英语"],
        content_format=["video"],
        budget_level="low",
        core_skills=["编程"],
        monetization_goal="adsense",
        target_regions=["US", "SG"],
    )
    assert "美国" in prompt
    assert "新加坡" in prompt
    assert "目标市场" in prompt


def test_build_user_prompt_with_weekly_hours():
    """每周投入时间字段。"""
    prompt = _build_user_prompt(
        languages=["英语"],
        content_format=["video"],
        budget_level="low",
        core_skills=["编程"],
        monetization_goal=None,
        weekly_hours="10-20h",
    )
    assert "半职投入" in prompt
    assert "投入时间" in prompt


def test_build_user_prompt_with_channel_info():
    """已有频道信息。"""
    prompt = _build_user_prompt(
        languages=["英语"],
        content_format=["video"],
        budget_level="low",
        core_skills=["编程"],
        monetization_goal=None,
        channel_info={
            "title": "TechChannel",
            "subscriber_count": 5000,
            "video_count": 120,
            "description": "A tech review channel",
        },
    )
    assert "TechChannel" in prompt
    assert "5,000" in prompt
    assert "已有频道" in prompt


def test_build_user_prompt_three_recommendations():
    """提示词要求3个推荐。"""
    prompt = _build_user_prompt(
        languages=["英语"],
        content_format=["video"],
        budget_level="low",
        core_skills=["编程"],
        monetization_goal="adsense",
    )
    assert "3 个" in prompt
    assert "高增长潜力" in prompt


# ── _parse_llm_json 测试 ──

def test_parse_llm_json_clean():
    """干净 JSON 解析。"""
    raw = '{"recommendations": [{"niche_title": "test"}]}'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result["recommendations"][0]["niche_title"] == "test"


def test_parse_llm_json_markdown_wrapped():
    """Markdown 代码块包裹的 JSON。"""
    raw = '```json\n{"recommendations": [{"niche_title": "test"}]}\n```'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result["recommendations"][0]["niche_title"] == "test"


def test_parse_llm_json_with_surrounding_text():
    """JSON 前后有文字。"""
    raw = 'Here is the result:\n{"recommendations": [{"niche_title": "test"}]}\nDone.'
    result = _parse_llm_json(raw)
    assert result is not None


def test_parse_llm_json_invalid():
    """无效 JSON 返回 None。"""
    assert _parse_llm_json("not json at all") is None


def test_parse_llm_json_empty():
    """空字符串返回 None。"""
    assert _parse_llm_json("") is None


# ── _validate_niche_json 测试（升级版：含新字段） ──

def test_validate_niche_json_valid_with_new_fields():
    """合法 JSON 结构（含 action_roadmap 和 estimated_monthly_income）。"""
    data = {
        "recommendations": [
            {
                "niche_title": "科技评测 - 英语 → 美国",
                "match_score": 95,
                "market_heat_stars": 4,
                "market_heat_desc": "头部频道增速 +15%/月",
                "competition_stars": 3,
                "competition_desc": "近半年新入局者成功率 23%",
                "content_gap": "Shorts评测供给不足",
                "cold_start_period": "3-6个月",
                "target_channel_example": "@TechShorts（8万粉）",
                "action_advice": "从 Shorts 评测切入",
                "action_roadmap": [
                    {"day_range": "1-7", "task": "注册频道", "expected_result": "频道上线"},
                    {"day_range": "8-14", "task": "建立节奏", "expected_result": "日更Shorts"},
                    {"day_range": "15-30", "task": "优化标题", "expected_result": "播放突破1万"},
                ],
                "estimated_monthly_income": "$200-800",
            }
        ],
        "avoid_niche": {"niche_title": "美食Vlog", "reason": "极度饱和"},
    }
    assert _validate_niche_json(data) is True


def test_validate_niche_json_missing_new_field():
    """缺少新增字段 action_roadmap 或 estimated_monthly_income。"""
    data = {
        "recommendations": [
            {
                "niche_title": "test",
                "match_score": 80,
                "market_heat_stars": 3,
                "market_heat_desc": "",
                "competition_stars": 3,
                "competition_desc": "",
                "content_gap": "",
                "cold_start_period": "",
                "target_channel_example": "",
                "action_advice": "",
                # 缺少 action_roadmap 和 estimated_monthly_income
            }
        ]
    }
    assert _validate_niche_json(data) is False


def test_validate_niche_json_empty_recommendations():
    """空推荐列表。"""
    assert _validate_niche_json({"recommendations": []}) is False


def test_validate_niche_json_no_recommendations_key():
    """缺少 recommendations 键。"""
    assert _validate_niche_json({"avoid_niche": {}}) is False


# ── _extract_channel_id_from_url 测试 ──

def test_extract_channel_id_from_handle():
    """从 @handle URL 提取。"""
    assert _extract_channel_id_from_url("https://www.youtube.com/@TechChannel") == "TechChannel"


def test_extract_channel_id_from_channel_id():
    """从 /channel/ URL 提取。"""
    assert _extract_channel_id_from_url("https://www.youtube.com/channel/UCxxxxxx") == "UCxxxxxx"


def test_extract_channel_id_from_c_handle():
    """从 /c/ URL 提取。"""
    assert _extract_channel_id_from_url("https://www.youtube.com/c/MyChannel") == "MyChannel"


def test_extract_channel_id_invalid():
    """无效 URL 返回 None。"""
    assert _extract_channel_id_from_url("https://example.com/foo") is None


def test_extract_channel_id_empty():
    """空字符串返回 None。"""
    assert _extract_channel_id_from_url("") is None


# ── Schema 测试（升级版） ──

def test_navigation_guide_request_with_all_new_fields():
    """NavigationGuideRequest 包含所有新增字段。"""
    from app.schemas.radar import NavigationGuideRequest
    req = NavigationGuideRequest(
        languages=["英语"],
        content_format=["video"],
        budget_level="zero",
        core_skills=["编程", "AI"],
        monetization_goal="adsense",
        existing_channel_url="https://www.youtube.com/@mychannel",
        target_regions=["US", "SG"],
        weekly_hours="10-20h",
    )
    assert req.core_skills == ["编程", "AI"]
    assert req.monetization_goal == "adsense"
    assert req.budget_level == "zero"
    assert req.existing_channel_url == "https://www.youtube.com/@mychannel"
    assert req.target_regions == ["US", "SG"]
    assert req.weekly_hours == "10-20h"


def test_navigation_guide_request_core_skills_required():
    """core_skills 必填。"""
    from app.schemas.radar import NavigationGuideRequest
    with pytest.raises(Exception):
        NavigationGuideRequest(
            languages=["英语"],
            content_format=["video"],
            budget_level="low",
        )


def test_navigation_guide_request_core_skills_max_3():
    """core_skills 最多3个。"""
    from app.schemas.radar import NavigationGuideRequest
    with pytest.raises(Exception):
        NavigationGuideRequest(
            languages=["英语"],
            content_format=["video"],
            budget_level="low",
            core_skills=["a", "b", "c", "d"],
        )


def test_roadmap_step_schema():
    """RoadmapStep schema 验证。"""
    from app.schemas.radar import RoadmapStep
    step = RoadmapStep(day_range="1-7", task="注册频道", expected_result="频道上线")
    assert step.day_range == "1-7"
    assert step.task == "注册频道"


def test_niche_recommendation_with_roadmap():
    """NicheRecommendation 包含 action_roadmap 和 estimated_monthly_income。"""
    from app.schemas.radar import NicheRecommendation, RoadmapStep
    rec = NicheRecommendation(
        niche_title="科技评测 - 英语 → 美国",
        match_score=95,
        market_heat_stars=4,
        market_heat_desc="+15%/月",
        competition_stars=3,
        competition_desc="成功率 23%",
        content_gap="Shorts不足",
        cold_start_period="3-6个月",
        target_channel_example="@TechShorts",
        action_advice="从 Shorts 切入",
        action_roadmap=[
            RoadmapStep(day_range="1-7", task="注册", expected_result="上线"),
        ],
        estimated_monthly_income="$200-800",
    )
    assert rec.match_score == 95
    assert len(rec.action_roadmap) == 1
    assert rec.estimated_monthly_income == "$200-800"


def test_niche_recommendation_score_range():
    """match_score 范围 1-100。"""
    from app.schemas.radar import NicheRecommendation
    with pytest.raises(Exception):
        NicheRecommendation(
            niche_title="test", match_score=0,
            market_heat_stars=3, market_heat_desc="",
            competition_stars=3, competition_desc="",
            content_gap="", cold_start_period="",
            target_channel_example="", action_advice="",
        )


def test_avoid_niche_schema():
    """AvoidNiche schema 验证。"""
    from app.schemas.radar import AvoidNiche
    avoid = AvoidNiche(niche_title="美食Vlog", reason="极度饱和")
    assert avoid.niche_title == "美食Vlog"


def test_navigation_guide_response_with_conversation_id():
    """NavigationGuideResponse 包含 conversation_id 和 channel_info。"""
    from app.schemas.radar import NavigationGuideResponse, NicheRecommendation, AvoidNiche
    resp = NavigationGuideResponse(
        recommendations=[
            NicheRecommendation(
                niche_title="test", match_score=80,
                market_heat_stars=4, market_heat_desc="",
                competition_stars=3, competition_desc="",
                content_gap="", cold_start_period="",
                target_channel_example="", action_advice="",
            )
        ],
        avoid_niche=AvoidNiche(niche_title="avoid", reason="saturated"),
        conversation_id="nav_guide:1:abc123",
        channel_info={"title": "MyChannel", "subscriber_count": 5000},
    )
    assert len(resp.recommendations) == 1
    assert resp.conversation_id == "nav_guide:1:abc123"
    assert resp.channel_info is not None


def test_navigation_chat_request_schema():
    """NavigationChatRequest schema 验证。"""
    from app.schemas.radar import NavigationChatRequest
    req = NavigationChatRequest(
        conversation_id="nav_guide:1:abc",
        user_message="为什么推荐这个品类？",
    )
    assert req.conversation_id == "nav_guide:1:abc"
    assert req.user_message == "为什么推荐这个品类？"


def test_navigation_chat_response_schema():
    """NavigationChatResponse schema 验证。"""
    from app.schemas.radar import NavigationChatResponse
    resp = NavigationChatResponse(
        assistant_message="因为该品类市场热度高且竞争适中",
        conversation_id="nav_guide:1:abc",
    )
    assert resp.assistant_message.startswith("因为")
