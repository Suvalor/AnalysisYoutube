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


class SubmitTaskResponse(BaseModel):
    """
    后台任务提交响应：接口快速返回，具体 YouTube/LLM 处理在后台执行。
    """

    code: int = Field(200, description="业务返回码（固定 200）")
    message: str = Field(..., description="任务提交提示")


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
    has_analysis: bool = Field(
        default=False,
        description="当前组织在 video_analyses 中是否已有该视频的 AI 分析记录（列表仅布尔，不含正文）",
    )

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
    ai_expertise: str | None = None
    ai_audience_age: str | None = None
    ai_summary: str | None = None
    ai_analyzed_at: datetime | None = None
    ai_source_model_library_id: int | None = None
    ai_source_llm_model_name: str | None = None
    ai_source_agent_id: int | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class YouTubeChannelAiAnalyzeRequest(BaseModel):
    """博主详情页 AI 深度分析：使用配置中心模型与智能体。"""

    model_library_id: int = Field(..., ge=1, description="model_libraries 表主键")
    llm_model_name: str = Field(..., min_length=1, max_length=128, description="该配置下要调用的具体模型名")
    agent_id: int | None = Field(default=None, description="prompt_libraries 表主键，可选；不传则仅用默认分析师规则")


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
    expertise: str = Field(default="", description="AI 总结的擅长内容")
    age_group: str = Field(..., description="AI 推断的受众年龄段与性别倾向")
    summary: str = Field(..., description="AI 推断的频道定位与爆款套路总结")
    analyzed_at: datetime | None = Field(None, description="本次分析写入库的时间")
    model_library_id: int | None = None
    llm_model_name: str | None = None
    agent_id: int | None = None


class YouTubeVideoAnalyzeRequest(BaseModel):
    """一键 AI 深度分析：视频维度持久化写入。"""

    video_id: int = Field(..., ge=1, description="youtube_videos 表主键 id")
    model_id: str = Field(..., min_length=1, max_length=128, description="LLM model 标识（来自模型库支持的 value）")
    agent_id: int | None = Field(default=None, description="prompt_libraries 表主键，可选")


class YouTubeVideoAnalysisResponse(BaseModel):
    video_id: int
    model_id: str
    agent_id: int | None
    content: str
    updated_at: datetime

