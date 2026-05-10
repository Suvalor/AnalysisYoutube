"""组织级集成配置 JSON（云存储、YouTube、火山等），与 user_id 解耦。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class OrgSettings(Base):
    __tablename__ = "org_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    payload_json: Mapped[str] = mapped_column(LONGTEXT, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="settings_row")
