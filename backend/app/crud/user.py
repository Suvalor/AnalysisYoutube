from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> Optional[User]:
    """根据邮箱查询用户。"""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_phone(
    session: AsyncSession,
    phone: str,
) -> Optional[User]:
    """根据手机号查询用户。"""
    result = await session.execute(select(User).where(User.phone == phone))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    phone: str | None = None,
    org_id: int = 1,
) -> User:
    """创建新用户，处理唯一约束冲突由上层捕获。"""
    user = User(
        email=email,
        hashed_password=hashed_password,
        phone=phone,
        org_id=org_id,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(user)
    return user


async def update_user_settings(
    session: AsyncSession,
    user: User,
    *,
    patch: dict[str, Any],
) -> User:
    """按 patch 更新用户设置字段（仅包含需要写入的键）。"""
    for key, value in patch.items():
        if hasattr(user, key):
            setattr(user, key, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(user)
    return user
