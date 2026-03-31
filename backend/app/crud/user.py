from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import UserCreate


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> Optional[User]:
    """根据邮箱查询用户。"""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
    hashed_password: str,
) -> User:
    """创建新用户，处理唯一约束冲突由上层捕获。"""
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
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
    feishu_doc_url: str | None,
) -> User:
    """更新用户设置相关字段。"""
    user.feishu_doc_url = feishu_doc_url
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(user)
    return user

