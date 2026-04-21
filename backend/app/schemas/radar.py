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
    budget_level: Literal["zero", "low", "medium", "high"] = Field(default="low", description="预算水平")
    core_skills: list[str] = Field(..., min_length=1, max_length=3, description="核心技能/内容方向，最多3个")
    monetization_goal: str | None = Field(None, description="变现目标")
    existing_channel_url: str | None = Field(None, description="已有 YouTube 频道 URL，可选")
    target_regions: list[str] = Field(default_factory=list, description="目标市场地区，如 ['US', 'SEA']")
    weekly_hours: str | None = Field(None, description="每周可投入时间，如 '<5h', '5-10h', '10-20h', '20h+'")
    model_library_id: int | None = None
    llm_model_name: str | None = None
    agent_id: int | None = None


class RoadmapStep(BaseModel):
    """行动路线图步骤。"""

    day_range: str = Field(description="时间范围，如 '1-7'")
    task: str = Field(description="具体任务")
    expected_result: str = Field(description="预期成果")


class NicheRecommendation(BaseModel):
    """LLM 深度推荐品类。"""

    niche_title: str = Field(description="如 '科技评测 - 英语 → 美国'")
    match_score: int = Field(ge=1, le=100, description="匹配度 1-100")
    market_heat_stars: int = Field(ge=1, le=5, description="市场热度星级")
    market_heat_desc: str = Field(description="如 '头部频道增速 +15%/月'")
    competition_stars: int = Field(ge=1, le=5, description="竞争强度星级")
    competition_desc: str = Field(description="如 '近半年新入局者成功率 23%'")
    content_gap: str = Field(description="市场缺什么内容")
    cold_start_period: str = Field(description="如 '3-6个月'")
    target_channel_example: str = Field(description="如 '@TechShorts（8万粉，月增2万）'")
    action_advice: str = Field(description="给用户的直接执行建议")
    action_roadmap: list[RoadmapStep] = Field(default_factory=list, description="30天行动路线图")
    estimated_monthly_income: str | None = Field(None, description="预估月收入范围，如 '$200-800'")


class AvoidNiche(BaseModel):
    """避坑品类。"""

    niche_title: str
    reason: str


class ChannelStrategyBreakdown(BaseModel):
    """频道内容策略拆解。"""

    channel_id: str
    title: str
    subscriber_count: int
    publish_frequency: str = Field(description="如 '每周2-3条'")
    avg_duration: str = Field(description="如 '8-15分钟'")
    title_pattern: str = Field(description="如 '数字+痛点+解决方案'")
    tag_pattern: str = Field(description="如 '核心关键词+长尾词'")


class MarketHeat(BaseModel):
    """市场热度。"""
    stars: int = Field(ge=1, le=5, description="星级 1-5")
    growth_rate: str = Field(description="如 '+10~20%/月'")


class CompetitionIntensity(BaseModel):
    """竞争强度。"""
    stars: int = Field(ge=1, le=5, description="星级 1-5")
    success_rate: str = Field(description="如 '20~30%'")


class BenchmarkChannel(BaseModel):
    """对标频道。"""
    title: str
    subscribers: int
    monthly_growth: str = Field(description="如 '+5~15%/月'")


class CategoryRecommendation(BaseModel):
    """品类+地区推荐（YouTube API 查询结果，兼容旧逻辑）。"""

    category: str
    region: str
    fit_score: float = Field(description="匹配度 0-100")
    reason: str
    top_channels: list[ChannelStrategyBreakdown]
    market_heat: MarketHeat | None = None
    competition_intensity: CompetitionIntensity | None = None
    content_gap: str | None = None
    benchmark_channel: BenchmarkChannel | None = None
    cold_start_period: str | None = None
    is_avoid: bool = False
    cr4: float | None = None


class NavigationQuotaUsage(BaseModel):
    """导航配额消耗。"""
    search_calls: int
    channels_calls: int
    total_points: int


class QuotaCheckInfo(BaseModel):
    """配额前置检查结果（返回给前端展示）。"""
    allowed: bool
    remaining: int
    estimated_cost: int
    today_used: int
    today_total: int


class NavigationGuideResponse(BaseModel):
    recommendations: list[NicheRecommendation] = Field(default_factory=list)
    avoid_niche: AvoidNiche | None = None
    ai_summary: str | None = None
    quota_usage: NavigationQuotaUsage | None = None
    quota_check: QuotaCheckInfo | None = None
    conversation_id: str | None = Field(None, description="对话 ID，用于多轮追问")
    channel_info: dict | None = Field(None, description="频道分析结果摘要")


# ──────────────────────────────────────────────
# 出海导航多轮对话
# ──────────────────────────────────────────────

class NavigationChatRequest(BaseModel):
    """出海导航追问请求。"""

    conversation_id: str = Field(..., min_length=1, description="对话 ID")
    user_message: str = Field(..., min_length=1, max_length=2000, description="用户追问内容")
    model_library_id: int | None = None
    llm_model_name: str | None = None
    agent_id: int | None = None


class NavigationChatResponse(BaseModel):
    """出海导航追问响应。"""

    assistant_message: str
    conversation_id: str


# ──────────────────────────────────────────────
# 出海导航推荐记录
# ──────────────────────────────────────────────

from datetime import datetime as _datetime


class NavigationGuideRecordItem(BaseModel):
    """推荐记录列表项（摘要）。"""

    id: int
    request_params: dict
    # 从 result 中提取的摘要字段，方便列表展示
    top_niche_title: str | None = Field(None, description="匹配度最高的品类名称")
    top_match_score: int | None = Field(None, description="匹配度最高的品类分数")
    recommendation_count: int = Field(0, description="推荐品类数量")
    created_at: _datetime


class NavigationGuideRecordDetail(BaseModel):
    """推荐记录详情（完整结果）。"""

    id: int
    request_params: dict
    result: dict
    created_at: _datetime


class NavigationGuideRecordListResponse(BaseModel):
    """推荐记录分页列表。"""

    items: list[NavigationGuideRecordItem]
    total: int
