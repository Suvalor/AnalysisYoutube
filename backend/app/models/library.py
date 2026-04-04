from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class AssetFileType(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"


class PromptLibrary(Base):
    __tablename__ = "prompt_libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StyleLibrary(Base):
    __tablename__ = "style_libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ModelLibrary(Base):
    __tablename__ = "model_libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_models_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AssetLibrary(Base):
    __tablename__ = "asset_libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL", server_default="MANUAL")
    storage_platform: Mapped[str] = mapped_column(String(32), nullable=False, default="aliyun", server_default="aliyun")
    storage_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ScriptLibrary(Base):
    __tablename__ = "script_libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    # AI_WORKSHOP：AI 脚本工坊保存；MANUAL：知识库手动新建
    origin_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="AI_WORKSHOP", server_default="AI_WORKSHOP"
    )
    prompt_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompt_libraries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    style_id: Mapped[int | None] = mapped_column(
        ForeignKey("style_libraries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

