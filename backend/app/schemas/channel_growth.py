"""频道增长仪表盘 Pydantic schemas。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChannelGrowthRequest(BaseModel):
    """频道增长仪表盘请求体。"""

    channel_ids: list[int] = Field(
        default_factory=list,
        description="YouTubeChannel 数据库 ID 列表（最多 10 个，为空则返回该用户所有监控池频道）",
        max_length=10,
    )
    days: int = Field(
        30,
        description="回看天数（7/14/30/90）",
        ge=7,
        le=90,
    )


class GrowthDataPoint(BaseModel):
    """增长趋势数据点。"""

    date: str = Field(..., description="日期（YYYY-MM-DD）")
    subscribers: int = Field(0, description="订阅数")
    views: int = Field(0, description="总播放量")
    videos: int = Field(0, description="视频数")


class ChannelGrowthMetrics(BaseModel):
    """单个频道的增长指标。"""

    pool_id: int = Field(..., description="监控池 ID")
    channel_id: str = Field(..., description="YouTube 频道 ID")
    title: str = Field(..., description="频道标题")
    thumbnail_url: str | None = Field(None, description="缩略图 URL")
    current_subscribers: int = Field(0, description="当前订阅数")
    current_views: int = Field(0, description="当前总播放量")
    current_videos: int = Field(0, description="当前视频数")
    subscriber_growth_rate: float = Field(
        0.0, description="订阅增长率（%）"
    )
    view_growth_rate: float = Field(
        0.0, description="播放量增长率（%）"
    )
    avg_views_per_video: float = Field(
        0.0, description="平均单视频播放量"
    )
    engagement_score: float = Field(
        0.0, description="互动得分（0-100）"
    )
    growth_trend: str = Field(
        "stable", description="增长趋势：rising/stable/declining"
    )
    growth_data: list[GrowthDataPoint] = Field(
        default_factory=list, description="历史增长数据点"
    )


class ChannelGrowthSummary(BaseModel):
    """所有频道汇总统计。"""

    total_subscribers: int = Field(0, description="总订阅数")
    total_views: int = Field(0, description="总播放量")
    total_videos: int = Field(0, description="总视频数")
    avg_subscriber_growth_rate: float = Field(
        0.0, description="平均订阅增长率（%）"
    )
    avg_view_growth_rate: float = Field(
        0.0, description="平均播放量增长率（%）"
    )
    fastest_growing_channel: str = Field(
        "", description="增长最快频道标题"
    )
    fastest_growing_rate: float = Field(
        0.0, description="最快增长率（%）"
    )


class ChannelGrowthResponse(BaseModel):
    """频道增长仪表盘响应。"""

    channels: list[ChannelGrowthMetrics] = Field(
        default_factory=list, description="各频道增长指标"
    )
    summary: ChannelGrowthSummary = Field(
        default_factory=ChannelGrowthSummary, description="汇总统计"
    )
    quota_used: int = Field(0, description="本次消耗的 API 配额")
