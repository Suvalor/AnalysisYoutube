from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inspiration import Inspiration


async def list_inspirations(session: AsyncSession, user_id: int) -> list[Inspiration]:
    q = (
        select(Inspiration)
        .where(Inspiration.user_id == user_id)
        .order_by(Inspiration.recorded_at.desc(), Inspiration.id.desc())
    )
    r = await session.execute(q)
    return list(r.scalars().all())


async def get_inspiration(session: AsyncSession, user_id: int, inspiration_id: int) -> Inspiration | None:
    q = select(Inspiration).where(Inspiration.id == inspiration_id, Inspiration.user_id == user_id)
    r = await session.execute(q)
    return r.scalar_one_or_none()


async def create_inspiration(session: AsyncSession, user_id: int, payload: dict) -> Inspiration:
    row = Inspiration(user_id=user_id, **payload)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def update_inspiration(session: AsyncSession, row: Inspiration, payload: dict) -> Inspiration:
    for k, v in payload.items():
        setattr(row, k, v)
    await session.flush()
    await session.refresh(row)
    return row


async def delete_inspiration(session: AsyncSession, row: Inspiration) -> None:
    await session.delete(row)
    await session.flush()
