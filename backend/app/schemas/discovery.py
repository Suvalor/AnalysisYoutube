"""潜力频道挖掘（Discovery Radar）请求与响应模型。"""

from pydantic import BaseModel, Field, field_validator


class ChannelDiscoverRequest(BaseModel):
    """挖掘请求：仅查询 YouTube，不落库。"""

    keyword: str = Field(..., min_length=1, max_length=200, description="搜索关键词")
    published_after: int = Field(
        ...,
        description="发布时间下限为「距今天数」，仅允许 7、14、30",
    )
    max_subscribers: int = Field(default=50000, ge=0, description="保留订阅数小于该值的频道")
    max_results: int = Field(default=25, ge=1, le=50, description="search.list 单次条数上限（YouTube 最大 50）")

    @field_validator("keyword")
    @classmethod
    def strip_keyword(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("keyword 不能为空")
        return s

    @field_validator("published_after")
    @classmethod
    def allowed_published_after_days(cls, v: int) -> int:
        if v not in (7, 14, 30):
            raise ValueError("published_after 只能为 7、14 或 30")
        return v


class DiscoverChannelItem(BaseModel):
    """单条挖掘结果（内存态）。"""

    yt_channel_id: str
    title: str
    thumbnail_url: str | None = None
    subscriber_count: int
    total_views: int
    channel_url: str
    viral_video_url: str


class QuickTrackRequest(BaseModel):
    """追踪博主请求：仅需 YouTube 频道 ID。"""

    channel_id: str = Field(..., min_length=1, max_length=64, description="YouTube 频道 ID")


class QuickTrackResponse(BaseModel):
    """追踪博主响应：成功 / 已存在 / 失败。"""

    success: bool
    message: str
    pool_id: int | None = None
    channel_title: str | None = None


class ChannelDiscoverResponse(BaseModel):
    items: list[DiscoverChannelItem]
    warnings: list[str] = Field(default_factory=list)
