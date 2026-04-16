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
