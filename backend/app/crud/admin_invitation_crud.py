"""管理员邀请码 CRUD 操作。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_invitation import AdminInvitation


async def create_admin_invitation(
    session: AsyncSession,
    *,
    created_by: int,
    code: str,
    expires_hours: int = 168,
) -> AdminInvitation:
    """创建管理员邀请码，默认有效期 7 天（168 小时）。"""
    invitation = AdminInvitation(
        code=code,
        created_by=created_by,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
    )
    session.add(invitation)
    await session.flush()
    await session.refresh(invitation)
    return invitation


async def get_invitation_by_code(
    session: AsyncSession,
    code: str,
) -> AdminInvitation | None:
    """根据邀请码查询邀请记录。"""
    result = await session.execute(
        select(AdminInvitation).where(AdminInvitation.code == code),
    )
    return result.scalar_one_or_none()


async def mark_invitation_used(
    session: AsyncSession,
    invitation: AdminInvitation,
    used_by: int,
) -> AdminInvitation:
    """标记邀请码为已使用。"""
    invitation.used_by = used_by
    invitation.used_at = datetime.now(timezone.utc)
    invitation.is_active = False
    await session.flush()
    await session.refresh(invitation)
    return invitation
