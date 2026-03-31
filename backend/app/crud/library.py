from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import AssetLibrary, PromptLibrary, ScriptLibrary, StyleLibrary


ModelT = TypeVar("ModelT", PromptLibrary, StyleLibrary, AssetLibrary, ScriptLibrary)


async def list_by_user(session: AsyncSession, model: type[ModelT], user_id: int) -> list[ModelT]:
    result = await session.execute(select(model).where(model.user_id == user_id).order_by(model.id.desc()))
    return list(result.scalars().all())


async def get_by_user(session: AsyncSession, model: type[ModelT], user_id: int, item_id: int) -> ModelT | None:
    result = await session.execute(select(model).where(model.id == item_id, model.user_id == user_id))
    return result.scalar_one_or_none()


async def create_with_user(
    session: AsyncSession,
    model: type[ModelT],
    user_id: int,
    payload: dict[str, Any],
) -> ModelT:
    item = model(user_id=user_id, **payload)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def update_with_user(
    session: AsyncSession,
    item: ModelT,
    payload: dict[str, Any],
) -> ModelT:
    for key, value in payload.items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return item


async def delete_with_user(session: AsyncSession, item: ModelT) -> None:
    await session.delete(item)
    await session.commit()


def ensure_owned_or_404(item: ModelT | None, message: str = "资源不存在") -> ModelT:
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    return item

