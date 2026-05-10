from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ApiQuotaUsage(Base):
    __tablename__ = "api_quota_usages"
    __table_args__ = (UniqueConstraint("record_date", name="uq_api_quota_record_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    points_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

