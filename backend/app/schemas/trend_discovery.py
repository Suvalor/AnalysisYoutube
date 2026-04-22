"""热门趋势发现 Pydantic schemas。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrendDiscoveryRequest(BaseModel):
    """热门趋势请求。"""

    region: str = Field("US", max_length=5, description="地区代码，如 US/GB/JP/KR")
    category_id: str | None = Field(None, description="YouTube 品类 ID（可选，如 20=游戏）")
    max_results: int = Field(50, ge=1, le=50, description="最大返回数量")


class TrendingVideoItem(BaseModel):
    """单条趋势视频。"""

    video_id: str
    title: str
    channel_title: str
    channel_id: str
    channel_subscribers: int = 0
    published_at: str = ""
    thumbnail_url: str = ""
    category_id: str = ""
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    engagement_rate: float = 0.0
    duration: str = ""


class CategoryDistributionItem(BaseModel):
    """品类分布项。"""

    category_id: str
    category_name: str
    video_count: int
    percentage: float


class TrendDiscoveryResponse(BaseModel):
    """热门趋势响应。"""

    region: str
    category_id: str | None = None
    fetched_at: str
    trending_videos: list[TrendingVideoItem]
    category_distribution: list[CategoryDistributionItem]
    stats: dict
    channels_list_calls: int = Field(0, description="channels.list API 调用次数")
