"""订阅管理路由：套餐列表、分配套餐、查看我的订阅。"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, CurrentUserDep, DBSessionDep
from app.schemas.subscription import (
    SubscriptionPlanRead,
    UserSubscriptionCreate,
    UserSubscriptionRead,
)
from app.services.subscription_service import (
    assign_subscription,
    create_plan,
    list_plans,
    update_plan,
    get_my_subscription,
)

router = APIRouter()


@router.get(
    "/plans",
    response_model=list[SubscriptionPlanRead],
    summary="列出所有启用的订阅套餐",
)
async def get_subscription_plans(
    db: DBSessionDep,
) -> list[SubscriptionPlanRead]:
    """获取所有启用的订阅套餐列表。"""
    return await list_plans(db)


@router.post(
    "/assign",
    response_model=UserSubscriptionRead,
    status_code=status.HTTP_201_CREATED,
    summary="为用户分配订阅套餐",
)
async def assign_user_subscription(
    admin: AdminDep,
    db: DBSessionDep,
    data: UserSubscriptionCreate,
) -> UserSubscriptionRead:
    """管理员为指定用户分配订阅套餐。"""
    try:
        result = await assign_subscription(db, data)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/my",
    response_model=UserSubscriptionRead | None,
    summary="查看我的订阅",
)
async def get_my_subscription_status(
    current_user: CurrentUserDep,
    db: DBSessionDep,
) -> UserSubscriptionRead | None:
    """获取当前用户激活的订阅状态。"""
    return await get_my_subscription(db, current_user)