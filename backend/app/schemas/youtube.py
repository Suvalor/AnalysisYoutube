from datetime import datetime

from pydantic import BaseModel, Field


class YouTubeAnalyzeRequest(BaseModel):
    youtube_url: str = Field(..., description="YouTube 频道 URL")
    group_name: str = Field(default="默认分组", description="监控分组名称")


class YouTubeVideoRead(BaseModel):
    id: int
    yt_video_id: str
    title: str
    thumbnail_url: str | None = None
    published_at: datetime | None = None
    duration_sec: int
    duration_str: str
    definition: str
    privacy_status: str
    category_id: str | None = None
    view_count: int
    like_count: int
    comment_count: int

    model_config = {"from_attributes": True}


class YouTubeChannelRead(BaseModel):
    id: int
    yt_channel_id: str
    title: str
    description: str
    thumbnail_url: str | None = None
    subscriber_count: int
    total_views: int
    video_count: int
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class YouTubeAnalyzeResponse(BaseModel):
    channel: YouTubeChannelRead
    recent_avg_views: int
    videos: list[YouTubeVideoRead]


class UserCompetitorChannelItem(BaseModel):
    pool_id: int
    group_name: str
    added_at: datetime
    channel: YouTubeChannelRead


class QuotaDashboardResponse(BaseModel):
    today_total: int
    today_used: int
    today_remaining: int
    history: list[dict]


class YouTubeVideoPageResponse(BaseModel):
    items: list[YouTubeVideoRead]
    total: int
    page: int
    page_size: int

