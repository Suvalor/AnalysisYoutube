"""配额查询路由：查看当前用户配额使用情况。"""

from fastapi import APIRouter

from app.api.deps import DBSessionDep, GuestInfoDep, OptionalUserDep
from app.models.user import UserRole
from app.schemas.quota import QuotaUsageRead
from app.services.rate_limit_service import get_user_quota_usage

router = APIRouter()


@router.get(
    "/usage",
    response_model=QuotaUsageRead,
    summary="查看配额使用情况",
)
async def get_quota_usage(
    db: DBSessionDep,
    user: OptionalUserDep,
    guest_info: GuestInfoDep,
) -> QuotaUsageRead:
    """获取当前用户（或游客）的配额使用情况。"""
    if user:
        role = user.role
        user_id = user.id
        guest_id = None
    else:
        role = UserRole.GUEST
        user_id = None
        guest_id = guest_info.guest_id

    usage = await get_user_quota_usage(
        db,
        user_id=user_id,
        role=role,
        guest_id=guest_id,
    )
    return QuotaUsageRead(**usage)