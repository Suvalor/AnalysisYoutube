from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quota import ApiQuotaUsage


async def add_quota_points(session: AsyncSession, points: int, record_date: date | None = None) -> ApiQuotaUsage:
    d = record_date or date.today()
    result = await session.execute(select(ApiQuotaUsage).where(ApiQuotaUsage.record_date == d))
    row = result.scalar_one_or_none()
    if row is None:
        row = ApiQuotaUsage(record_date=d, points_used=points)
        session.add(row)
    else:
        row.points_used += points
    await session.flush()
    return row


async def get_quota_by_date(session: AsyncSession, d: date) -> ApiQuotaUsage | None:
    result = await session.execute(select(ApiQuotaUsage).where(ApiQuotaUsage.record_date == d))
    return result.scalar_one_or_none()


async def list_quota_recent_days(session: AsyncSession, days: int) -> list[ApiQuotaUsage]:
    start_date = date.today() - timedelta(days=days - 1)
    result = await session.execute(
        select(ApiQuotaUsage)
        .where(ApiQuotaUsage.record_date >= start_date)
        .order_by(ApiQuotaUsage.record_date.asc())
    )
    return list(result.scalars().all())

