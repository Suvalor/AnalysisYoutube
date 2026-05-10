from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class MixTaskStatus(str, PyEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MixTask(Base):
    __tablename__ = "mix_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=MixTaskStatus.PENDING, server_default="PENDING")
    source_video_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    audio_source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="tts", server_default="tts")
    audio_source_ref: Mapped[str] = mapped_column(String(2000), nullable=False, default="", server_default="")
    aspect_ratio: Mapped[str] = mapped_column(String(8), nullable=False, default="9:16", server_default="9:16")
    use_highlights: Mapped[bool] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    output_path: Mapped[str] = mapped_column(String(500), nullable=False, default="", server_default="")
    error_message: Mapped[str] = mapped_column(String(500), nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
