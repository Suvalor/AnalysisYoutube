from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class User(Base):
    """用户表."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    org_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        server_default="1",
        index=True,
    )
    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    feishu_doc_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_api_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_models_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_prompt_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    youtube_access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    youtube_refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    youtube_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    youtube_channel_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(32), nullable=True)
    competitor_pools: Mapped[list["UserCompetitorPool"]] = relationship(
        "UserCompetitorPool", back_populates="user", cascade="all, delete-orphan"
    )

