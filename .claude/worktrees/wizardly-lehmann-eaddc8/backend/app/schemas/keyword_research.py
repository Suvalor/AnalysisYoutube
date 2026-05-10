"""关键词研究请求与响应模型。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class KeywordResearchRequest(BaseModel):
    """关键词研究请求。"""

    keyword: str = Field(..., min_length=1, max_length=200, description="研究关键词")
    region: str = Field(default="US", description="地区代码，如 US/GB/JP/KR")
    language: str = Field(default="zh", description="语言代码，如 zh/en/ja")
    region_label: str = Field(default="", description="地区中文名，用于历史记录")
    language_label: str = Field(default="", description="语言中文名，用于历史记录")

    @field_validator("keyword")
    @classmethod
    def strip_keyword(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("keyword 不能为空")
        return s


class TrendDataPoint(BaseModel):
    """趋势数据点。"""

    period: str = Field(description="时间段标签，如 '7天'")
    days: int = Field(description="天数")
    result_count: int = Field(description="该时间段内的搜索结果数")


class TopVideoItem(BaseModel):
    """搜索结果中的热门视频。"""

    view_count: int = Field(description="播放量")
    like_count: int = Field(default=0, description="点赞数")
    comment_count: int = Field(default=0, description="评论数")
    channel_title: str = Field(default="", description="频道名称")


class RelatedKeywordItem(BaseModel):
    """相关关键词（带评分）。"""

    keyword: str = Field(description="相关关键词")
    search_volume_score: int = Field(default=0, description="搜索量评分 0-100")
    competition_score: int = Field(default=0, description="竞争度评分 0-100")


class KeywordResearchResponse(BaseModel):
    """关键词研究响应。"""

    keyword: str
    region: str
    # ── 核心评分 ──
    keyword_score: int = Field(description="关键词综合评分 0-100")
    search_volume_score: int = Field(description="搜索量评分 0-100")
    competition_score: int = Field(description="竞争度评分 0-100")
    keyword_difficulty: int = Field(default=0, description="关键词难度 0-100")
    opportunity_score: int = Field(default=0, description="机会得分 0-100")
    trend_direction: str = Field(default="stable", description="趋势方向：rising/stable/declining")
    # ── 原始数据 ──
    total_results: int = Field(description="YouTube 返回的估算结果总数")
    related_keywords: list[str] = Field(default_factory=list, description="相关关键词")
    related_keywords_with_scores: list[RelatedKeywordItem] = Field(
        default_factory=list, description="相关关键词（带评分）"
    )
    trend_data: list[TrendDataPoint] = Field(default_factory=list, description="趋势数据")
    top_videos: list[TopVideoItem] = Field(default_factory=list, description="热门视频")
    channel_count: int = Field(default=0, description="相关频道数")
    avg_channel_subscribers: int = Field(default=0, description="平均频道订阅数")
    content_gap_ratio: float = Field(default=0.0, description="内容缺口比率 0-1")
    search_calls: int = Field(default=0, description="消耗的 search.list 调用次数")
