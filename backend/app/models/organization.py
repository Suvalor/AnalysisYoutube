"""组织（租户）实体：集成配置、YouTube Key、云存储等按 org 共享。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.org_settings import OrgSettings
    from app.models.user import User


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="默认组织")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    settings_row: Mapped["OrgSettings | None"] = relationship(
        "OrgSettings",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )
