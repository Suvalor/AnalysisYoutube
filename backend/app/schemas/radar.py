"""蓝海雷达扫描请求与响应模型（仅查询 YouTube，不落库）。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BlueOceanRadarRequest(BaseModel):
    """蓝海雷达扫描请求。"""

    keyword: str = Field(..., min_length=1, max_length=200, description="搜索关键词")
    published_after: Literal[30, 90, 180] = Field(
        ...,
        description="仅发布于近 N 天的视频：30=近1个月，90=近3个月，180=近半年",
    )
    max_subscribers: int = Field(default=30000, ge=0, description="保留订阅数严格小于该值的频道")
    outlier_multiplier: float = Field(default=10.0, gt=0, description="爆款系数下限：单支播放量/粉丝数")
    video_duration: Literal["short", "medium", "long"] | None = Field(
        default=None,
        description="可选：对应 YouTube search 的 videoDuration；不传表示不限时长",
    )

    @field_validator("keyword")
    @classmethod
    def strip_keyword(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("keyword 不能为空")
        return s


class BlueOceanChannelItem(BaseModel):
    """单条蓝海雷达结果（内存态）。"""

    yt_channel_id: str
    title: str
    thumbnail_url: str | None = None
    subscriber_count: int
    total_views: int
    channel_url: str
    viral_video_url: str
    viral_view_count: int
    outlier_score: float


class BlueOceanRadarResponse(BaseModel):
    items: list[BlueOceanChannelItem]
    warnings: list[str] = Field(default_factory=list)


class RadarAiRetrospectiveRequest(BaseModel):
    """蓝海雷达 AI 复盘请求。"""

    lookback_days: int = Field(default=14, ge=7, le=90, description="回看天数")
    top_n: int = Field(default=8, ge=3, le=20, description="高低样本各取 N 条")
    model_library_id: int = Field(..., ge=1, description="模型库 ID")
    llm_model_name: str = Field(..., min_length=1, max_length=128, description="模型名")
    agent_id: int = Field(..., ge=1, description="智能体提示词 ID")
    conversation_id: str | None = Field(None, description="对话 ID，不传则新建")

    @field_validator("llm_model_name")
    @classmethod
    def strip_model_name(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("llm_model_name 不能为空")
        return s


class RadarRecommendedParameters(BaseModel):
    max_subscribers: int
    outlier_multiplier: float
    suggested_keywords: list[str] = Field(default_factory=list)


class RadarSampleMeta(BaseModel):
    lookback_days: int
    top_count: int
    low_count: int


class RadarAiRetrospectiveResponse(BaseModel):
    analysis_summary: str
    recommended_parameters: RadarRecommendedParameters
    next_step_action: str
    sample_meta: RadarSampleMeta
    conversation_id: str | None = Field(None, description="对话 ID，后续请求可传入以延续上下文")


# ──────────────────────────────────────────────
# 品类机会报告
# ──────────────────────────────────────────────

class CategoryOpportunityRequest(BaseModel):
    """品类机会报告请求。"""

    keyword: str = Field(..., min_length=1, max_length=200, description="品类关键词")
    region: str = Field(default="US", description="地区代码，如 US/SG/AE")
    lookback_months: int = Field(default=6, ge=1, le=12, description="回看月数")

    @field_validator("keyword")
    @classmethod
    def strip_keyword(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("keyword 不能为空")
        return s


class ChannelGrowthItem(BaseModel):
    """头部频道增速。"""

    channel_id: str
    title: str
    subscriber_count: int
    monthly_growth_rate: float = Field(description="月均增速 %")
    trend: Literal["rising", "stable", "declining"]


class ContentGapItem(BaseModel):
    """内容缺口。"""

    duration_bucket: str = Field(description="short / medium / long")
    supply_ratio: float = Field(description="该时长占比")
    avg_views: int = Field(description="该时长平均播放")
    opportunity_score: float = Field(description="供给不足 + 播放高 = 机会大")


class NewcomerStats(BaseModel):
    """新入局者统计。"""

    total_new_channels: int
    successful_channels: int = Field(description="订阅 > 1000 的频道数")
    success_rate: float = Field(description="成功率 0-1")


class CategoryOpportunityResponse(BaseModel):
    keyword: str
    region: str
    top_channels_growth: list[ChannelGrowthItem]
    content_gaps: list[ContentGapItem]
    newcomer_stats: NewcomerStats
    ai_summary: str | None = Field(None, description="LLM 生成的总结")


# ──────────────────────────────────────────────
# 跨地区对比
# ──────────────────────────────────────────────

class CrossRegionCompareRequest(BaseModel):
    """跨地区对比请求。"""

    keyword: str = Field(..., min_length=1, max_length=200, description="搜索关键词")
    regions: list[str] = Field(..., min_length=2, max_length=5, description="地区代码列表")
    published_after: Literal[30, 90, 180] = Field(default=30)

    @field_validator("keyword")
    @classmethod
    def strip_keyword(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("keyword 不能为空")
        return s


class RegionSnapshot(BaseModel):
    """单个地区的市场快照。"""

    region_code: str
    region_name: str
    channel_count: int
    avg_views: int
    median_outlier_score: float
    top_channel_title: str
    top_channel_subscribers: int


class CrossRegionCompareResponse(BaseModel):
    keyword: str
    regions: list[RegionSnapshot]
    ai_recommendation: str | None = None


# ──────────────────────────────────────────────
# 一键出报告
# ──────────────────────────────────────────────

class ExportReportRequest(BaseModel):
    """导出报告请求。"""

    scan_items: list[BlueOceanChannelItem] = Field(description="扫描结果列表")
    keyword: str = Field(default="", description="搜索关键词")
    ai_summary: str | None = Field(None, description="可选的 AI 分析结论")


class ExportReportResponse(BaseModel):
    markdown_content: str = Field(description="Markdown 格式报告内容")


# ──────────────────────────────────────────────
# 出海导航
# ──────────────────────────────────────────────

class NavigationGuideRequest(BaseModel):
    """出海导航请求。"""

    languages: list[str] = Field(..., min_length=1, description="语言能力，如 ['中文', '英语']")
    content_format: list[str] = Field(default=["video"], description="内容形式，如 ['video', 'short']")
    budget_level: Literal["low", "medium", "high"] = Field(default="low", description="预算水平")
    model_library_id: int | None = None
    llm_model_name: str | None = None
    agent_id: int | None = None


class ChannelStrategyBreakdown(BaseModel):
    """频道内容策略拆解。"""

    channel_id: str
    title: str
    subscriber_count: int
    publish_frequency: str = Field(description="如 '每周2-3条'")
    avg_duration: str = Field(description="如 '8-15分钟'")
    title_pattern: str = Field(description="如 '数字+痛点+解决方案'")
    tag_pattern: str = Field(description="如 '核心关键词+长尾词'")


class CategoryRecommendation(BaseModel):
    """品类+地区推荐。"""

    category: str
    region: str
    fit_score: float = Field(description="匹配度 0-100")
    reason: str
    top_channels: list[ChannelStrategyBreakdown]


class NavigationGuideResponse(BaseModel):
    recommendations: list[CategoryRecommendation]
    ai_summary: str | None = None
