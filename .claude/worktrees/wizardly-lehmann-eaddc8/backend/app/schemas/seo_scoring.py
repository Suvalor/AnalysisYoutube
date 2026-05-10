"""SEO 评分 Pydantic schemas。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SeoScoringRequest(BaseModel):
    """SEO 评分请求。"""

    model_config = {"protected_namespaces": ()}

    title: str = Field(..., min_length=1, max_length=500, description="视频标题")
    description: str = Field("", max_length=5000, description="视频描述")
    tags: list[str] = Field(default_factory=list, description="视频标签列表")
    thumbnail_url: str | None = Field(None, max_length=1024, description="缩略图 URL（可选）")
    target_keyword: str | None = Field(None, max_length=200, description="目标关键词（可选）")
    model_library_id: int | None = Field(None, description="模型配置 ID（可选，用于 AI 竞品分析）")


class AiBenchmarkResult(BaseModel):
    """AI 竞品对标分析结果。"""

    title_benchmark: str = Field("", description="标题竞品对标分析")
    description_benchmark: str = Field("", description="描述竞品对标分析")
    tags_benchmark: str = Field("", description="标签竞品对标分析")
    thumbnail_benchmark: str = Field("", description="缩略图竞品对标分析")


class ScoreBreakdown(BaseModel):
    """评分明细：基础分 + AI 加分。"""

    title_base: int = Field(0, description="标题基础规则分")
    title_ai_bonus: int = Field(0, description="标题 AI 竞品加分")
    description_base: int = Field(0, description="描述基础规则分")
    description_ai_bonus: int = Field(0, description="描述 AI 竞品加分")
    tags_base: int = Field(0, description="标签基础规则分")
    tags_ai_bonus: int = Field(0, description="标签 AI 竞品加分")
    thumbnail_base: int = Field(0, description="缩略图基础规则分")
    thumbnail_ai_bonus: int = Field(0, description="缩略图 AI 竞品加分")


class CompetitorSummaryItem(BaseModel):
    """竞品视频摘要。"""

    title: str = Field("", description="竞品视频标题")
    channel_title: str = Field("", description="竞品频道名称")


class SeoScoringResponse(BaseModel):
    """SEO 评分结果。"""

    record_id: int | None = Field(None, description="评分记录 ID（保存后返回）")
    total_score: int = Field(..., ge=0, le=100, description="总分（0-100）")
    title_score: int = Field(..., ge=0, le=25, description="标题得分")
    title_max: int = Field(25, description="标题满分")
    description_score: int = Field(..., ge=0, le=25, description="描述得分")
    description_max: int = Field(25, description="描述满分")
    tags_score: int = Field(..., ge=0, le=25, description="标签得分")
    tags_max: int = Field(25, description="标签满分")
    thumbnail_score: int = Field(..., ge=0, le=25, description="缩略图得分")
    thumbnail_max: int = Field(25, description="缩略图满分")
    suggestions: list[str] = Field(default_factory=list, description="优化建议列表")
    ai_benchmark: AiBenchmarkResult | None = Field(None, description="AI 竞品对标分析")
    competitor_summary: list[CompetitorSummaryItem] = Field(default_factory=list, description="竞品视频摘要")
    score_breakdown: ScoreBreakdown | None = Field(None, description="评分明细")


class SeoScoreRecordItem(BaseModel):
    """SEO 评分历史记录列表项。"""

    id: int
    title: str
    total_score: int
    title_score: int
    description_score: int
    tags_score: int
    thumbnail_score: int
    target_keyword: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SeoScoreRecordDetail(BaseModel):
    """SEO 评分历史记录详情。"""

    id: int
    title: str
    description: str
    tags: list[str] | None = None
    thumbnail_url: str | None = None
    target_keyword: str | None = None
    total_score: int
    title_score: int
    description_score: int
    tags_score: int
    thumbnail_score: int
    suggestions: list[str] | None = None
    ai_benchmark: AiBenchmarkResult | None = None
    competitor_summary: list[CompetitorSummaryItem] | None = None
    score_breakdown: ScoreBreakdown | None = None
    model_library_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SeoScoreHistoryResponse(BaseModel):
    """SEO 评分历史列表响应。"""

    items: list[SeoScoreRecordItem]
    total: int
