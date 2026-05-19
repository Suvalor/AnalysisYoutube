from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole

# update_user_settings 允许写入的字段白名单，防止 Mass Assignment
_ALLOWED_SETTINGS_FIELDS = frozenset({
    "feishu_doc_url",
    "ai_api_base_url",
    "ai_models_json",
    "ai_prompt_config_json",
    "ai_api_key_encrypted",
    "theme",
    "locale",
})


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
    role: str = "user",
) -> User:
    """创建新用户，处理唯一约束冲突由上层捕获。"""
    user = User(
        email=email,
        hashed_password=hashed_password,
        phone=phone,
        org_id=org_id,
        role=role,
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
        if key in _ALLOWED_SETTINGS_FIELDS:
            setattr(user, key, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(user)
    return user


async def update_user_role(
    session: AsyncSession,
    user_id: int,
    new_role: str,
) -> User:
    """更新指定用户的角色，仅允许 user/subscriber/admin 三种角色。"""
    allowed_roles = {UserRole.USER, UserRole.SUBSCRIBER, UserRole.ADMIN}
    if new_role not in allowed_roles:
        raise ValueError(f"不允许的角色值：{new_role}，仅允许 {', '.join(sorted(allowed_roles))}")

    user = await session.get(User, user_id)
    if user is None:
        raise ValueError(f"用户不存在：user_id={user_id}")

    user.role = new_role
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(user)
    return user
