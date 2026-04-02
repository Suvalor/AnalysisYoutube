from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BIGINT, JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class YouTubeChannel(Base):
    __tablename__ = "youtube_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    yt_channel_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    subscriber_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    total_views: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    video_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    ai_expertise: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_audience_age: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_source_model_library_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_source_llm_model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_source_agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    videos: Mapped[list["YouTubeVideo"]] = relationship(
        "YouTubeVideo", back_populates="channel", cascade="all, delete-orphan"
    )
    users_in_pool: Mapped[list["UserCompetitorPool"]] = relationship(
        "UserCompetitorPool", back_populates="channel", cascade="all, delete-orphan"
    )
    histories: Mapped[list["YouTubeChannelHistory"]] = relationship(
        "YouTubeChannelHistory", back_populates="channel", cascade="all, delete-orphan"
    )
    comments: Mapped[list["YouTubeComment"]] = relationship(
        "YouTubeComment", back_populates="channel", cascade="all, delete-orphan"
    )
    insights: Mapped[list["YouTubeChannelInsight"]] = relationship(
        "YouTubeChannelInsight", back_populates="channel", cascade="all, delete-orphan"
    )


class YouTubeChannelInsight(Base):
    """博主 AI 深度洞察历史记录（每次分析一条）。"""

    __tablename__ = "youtube_channel_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_library_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_model_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    ai_expertise: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_audience_age: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    channel: Mapped["YouTubeChannel"] = relationship("YouTubeChannel", back_populates="insights")


class UserCompetitorPool(Base):
    __tablename__ = "user_competitor_pools"
    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_user_competitor_channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"), nullable=False
    )
    group_name: Mapped[str] = mapped_column(String(100), nullable=False, default="默认分组")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="competitor_pools")
    channel: Mapped["YouTubeChannel"] = relationship("YouTubeChannel", back_populates="users_in_pool")


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    yt_video_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_str: Mapped[str] = mapped_column(String(20), nullable=False, default="00:00")
    definition: Mapped[str] = mapped_column(String(20), nullable=False, default="sd")
    privacy_status: Mapped[str] = mapped_column(String(20), nullable=False, default="public")
    category_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    view_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    channel: Mapped["YouTubeChannel"] = relationship("YouTubeChannel", back_populates="videos")
    comments: Mapped[list["YouTubeComment"]] = relationship(
        "YouTubeComment", back_populates="video", cascade="all, delete-orphan"
    )


class YouTubeVideoAnalysis(Base):
    """视频 AI 深度洞察持久化结果（每个组织/视频一份最新）。"""

    __tablename__ = "video_analyses"
    __table_args__ = (
        UniqueConstraint("org_id", "video_id", name="uq_video_analyses_org_video"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class YouTubeComment(Base):
    """定向抓取的 YouTube 评论（commentThreads + searchTerms）。"""

    __tablename__ = "youtube_comments"
    __table_args__ = (UniqueConstraint("yt_comment_id", name="uq_youtube_comment_yt_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    yt_comment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    author_avatar: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    text_original: Mapped[str] = mapped_column(Text, nullable=False, default="")
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    keyword_used: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    video: Mapped["YouTubeVideo"] = relationship("YouTubeVideo", back_populates="comments")
    channel: Mapped["YouTubeChannel"] = relationship("YouTubeChannel", back_populates="comments")


class YouTubeChannelHistory(Base):
    __tablename__ = "youtube_channel_histories"
    __table_args__ = (
        UniqueConstraint("channel_id", "record_date", name="uq_channel_record_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    record_date: Mapped[date] = mapped_column(nullable=False, index=True)
    subscriber_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    total_views: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    video_count: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    channel: Mapped["YouTubeChannel"] = relationship("YouTubeChannel", back_populates="histories")

