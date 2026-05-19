"""订阅管理服务：套餐查询、分配、用户订阅状态查询。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.subscription_crud import (
    create_subscription_plan,
    create_user_subscription,
    get_active_user_subscription,
    get_subscription_plan,
    list_active_subscription_plans,
    update_subscription_plan,
)
from app.models.user import User, UserRole
from app.schemas.subscription import (
    SubscriptionPlanCreate,
    SubscriptionPlanRead,
    SubscriptionPlanUpdate,
    UserSubscriptionCreate,
    UserSubscriptionRead,
)


async def list_plans(session: AsyncSession) -> list[SubscriptionPlanRead]:
    """列出所有启用的订阅套餐。"""
    plans = await list_active_subscription_plans(session)
    return [SubscriptionPlanRead.model_validate(p) for p in plans]


async def create_plan(
    session: AsyncSession,
    data: SubscriptionPlanCreate,
) -> SubscriptionPlanRead:
    """创建订阅套餐。"""
    plan = await create_subscription_plan(
        session,
        name=data.name,
        description=data.description,
        quotas_json=data.quotas_json,
        price_monthly=data.price_monthly,
    )
    await session.commit()
    return SubscriptionPlanRead.model_validate(plan)


async def update_plan(
    session: AsyncSession,
    plan_id: int,
    data: SubscriptionPlanUpdate,
) -> SubscriptionPlanRead:
    """更新订阅套餐。"""
    plan = await get_subscription_plan(session, plan_id)
    if plan is None:
        raise ValueError("订阅套餐不存在")
    patch = data.model_dump(exclude_unset=True)
    plan = await update_subscription_plan(session, plan, patch=patch)
    await session.commit()
    return SubscriptionPlanRead.model_validate(plan)


async def assign_subscription(
    session: AsyncSession,
    data: UserSubscriptionCreate,
) -> UserSubscriptionRead:
    """为用户分配订阅套餐，同时升级用户角色为 subscriber。"""
    # 验证套餐存在
    plan = await get_subscription_plan(session, data.plan_id)
    if plan is None:
        raise ValueError("订阅套餐不存在")

    # 创建订阅记录
    subscription = await create_user_subscription(
        session,
        user_id=data.user_id,
        plan_id=data.plan_id,
        expires_at=data.expires_at,
    )

    # 升级用户角色为 subscriber
    user = await session.get(User, data.user_id)
    if user is not None and user.role != UserRole.SUBSCRIBER:
        user.role = UserRole.SUBSCRIBER
        session.add(user)

    await session.commit()
    await session.refresh(subscription)

    # 加载关联的 plan 对象
    plan = await get_subscription_plan(session, subscription.plan_id)
    read_data = UserSubscriptionRead.model_validate(subscription)
    read_data.plan = SubscriptionPlanRead.model_validate(plan) if plan else None
    return read_data


async def get_my_subscription(
    session: AsyncSession,
    user: User,
) -> UserSubscriptionRead | None:
    """获取当前用户激活的订阅。"""
    subscription = await get_active_user_subscription(session, user.id)
    if subscription is None:
        return None
    plan = await get_subscription_plan(session, subscription.plan_id)
    read_data = UserSubscriptionRead.model_validate(subscription)
    read_data.plan = SubscriptionPlanRead.model_validate(plan) if plan else None
    return read_data
