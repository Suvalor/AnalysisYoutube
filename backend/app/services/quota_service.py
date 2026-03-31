from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.quota import add_quota_points

API_POINTS = {
    "channels": 1,
    "search": 100,
    "videos": 1,
}


async def record_api_quota_usage(session: AsyncSession, api_name: str, times: int = 1) -> int:
    points = API_POINTS.get(api_name, 0) * max(1, times)
    if points > 0:
        await add_quota_points(session, points)
    return points

