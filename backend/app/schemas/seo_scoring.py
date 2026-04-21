"""SEO 评分 Pydantic schemas。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SeoScoringRequest(BaseModel):
    """SEO 评分请求。"""

    title: str = Field(..., min_length=1, max_length=500, description="视频标题")
    description: str = Field("", max_length=5000, description="视频描述")
    tags: list[str] = Field(default_factory=list, description="视频标签列表")
    target_keyword: str | None = Field(None, max_length=200, description="目标关键词（可选）")


class SeoScoringResponse(BaseModel):
    """SEO 评分结果。"""

    total_score: int = Field(..., ge=0, le=100, description="总分（0-100）")
    title_score: int = Field(..., ge=0, le=40, description="标题得分")
    title_max: int = Field(40, description="标题满分")
    description_score: int = Field(..., ge=0, le=30, description="描述得分")
    description_max: int = Field(30, description="描述满分")
    tags_score: int = Field(..., ge=0, le=30, description="标签得分")
    tags_max: int = Field(30, description="标签满分")
    suggestions: list[str] = Field(default_factory=list, description="优化建议列表")
