from datetime import datetime

from pydantic import BaseModel, Field


class YouTubeAnalyzeRequest(BaseModel):
    youtube_url: str = Field(..., description="YouTube 频道 URL")
    group_name: str = Field(default="默认分组", description="监控分组名称")


class YouTubeBatchAnalyzeRequest(BaseModel):
    urls: str = Field(..., description="多个频道链接，分号或换行分隔")
    group_name: str = Field(default="默认分组", description="监控分组名称")


class YouTubeBatchAnalyzeResponse(BaseModel):
    channels_count: int = Field(..., description="成功分析并入库的频道数")
    videos_count: int = Field(..., description="写入或更新的视频条数")
    quota_used: int = Field(..., description="本次消耗的 API 配额点数")
    errors: list[str] = Field(default_factory=list, description="解析或部分频道失败时的提示")


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
    tags: list[str] | None = None
    view_count: int
    like_count: int
    comment_count: int
    channel_title: str | None = Field(default=None, description="所属频道标题（跨频道列表时填充）")

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
    ai_tags: list[str] | None = None
    ai_audience_age: str | None = None
    ai_summary: str | None = None
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


class CommentScrapeRequest(BaseModel):
    keyword: str = Field(..., description="在评论中搜索的关键字")


class CommentScrapeResponse(BaseModel):
    scraped_count: int = Field(..., description="写入或更新的评论条数")
    quota_used: int = Field(..., description="本次 commentThreads 调用消耗的配额点数")


class YouTubeChannelAIAnalyzeResponse(BaseModel):
    tags: list[str] = Field(default_factory=list, description="AI 推断的频道核心标签")
    age_group: str = Field(..., description="AI 推断的受众年龄段与性别倾向")
    summary: str = Field(..., description="AI 推断的频道定位与爆款套路总结")

