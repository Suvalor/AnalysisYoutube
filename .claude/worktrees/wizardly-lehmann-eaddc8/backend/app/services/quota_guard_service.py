"""配额守卫服务：导航执行前的前置配额检查与超限阻断。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.quota import get_quota_by_date
from app.services.quota_service import calc_quota_points

DAILY_QUOTA_LIMIT = 10_000


@dataclass
class QuotaCheckResult:
    """配额检查结果。"""

    allowed: bool
    remaining: int
    estimated_cost: int
    today_used: int
    today_total: int


async def check_quota_before_navigation(
    session: AsyncSession,
    *,
    estimated_search_calls: int = 5,
    estimated_channel_calls: int = 15,
    channels_part_count: int = 2,
) -> QuotaCheckResult:
    """导航执行前的前置配额检查。

    使用 calc_quota_points 精确估算消耗。
    """
    search_cost = calc_quota_points("search", times=estimated_search_calls)
    channels_cost = calc_quota_points(
        "channels", times=estimated_channel_calls, part_count=channels_part_count,
    )
    estimated_cost = search_cost + channels_cost

    today_row = await get_quota_by_date(session, date.today())
    today_used = int(today_row.points_used) if today_row else 0
    remaining = max(0, DAILY_QUOTA_LIMIT - today_used)

    return QuotaCheckResult(
        allowed=remaining >= estimated_cost,
        remaining=remaining,
        estimated_cost=estimated_cost,
        today_used=today_used,
        today_total=DAILY_QUOTA_LIMIT,
    )
