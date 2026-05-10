"""SEO 评分记录模型：持久化评分结果 + 优化建议 + 竞品数据 + AI 分析。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BIGINT, JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class SeoScoreRecord(Base):
    """SEO 评分记录：每次评分保存完整结果，支持历史趋势追踪。"""

    __tablename__ = "seo_score_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # 输入数据
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    target_keyword: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 评分结果
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thumbnail_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 优化建议
    suggestions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # AI 竞品对标分析
    ai_benchmark: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 竞品数据摘要
    competitor_summary: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 评分明细（基础分 + AI 加分）
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 使用的模型配置
    model_library_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
