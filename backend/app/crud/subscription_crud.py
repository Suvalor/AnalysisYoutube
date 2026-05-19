"""订阅套餐与用户订阅 CRUD 操作。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription


async def create_subscription_plan(
    session: AsyncSession,
    *,
    name: str,
    quotas_json: dict,
    price_monthly,
    description: str | None = None,
) -> SubscriptionPlan:
    """创建订阅套餐。"""
    plan = SubscriptionPlan(
        name=name,
        description=description,
        quotas_json=quotas_json,
        price_monthly=price_monthly,
    )
    session.add(plan)
    await session.flush()
    await session.refresh(plan)
    return plan


async def get_subscription_plan(
    session: AsyncSession,
    plan_id: int,
) -> SubscriptionPlan | None:
    """根据 ID 查询订阅套餐。"""
    result = await session.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id),
    )
    return result.scalar_one_or_none()


async def list_active_subscription_plans(
    session: AsyncSession,
) -> list[SubscriptionPlan]:
    """列出所有启用的订阅套餐。"""
    result = await session.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.id.asc()),
    )
    return list(result.scalars().all())


async def update_subscription_plan(
    session: AsyncSession,
    plan: SubscriptionPlan,
    *,
    patch: dict,
) -> SubscriptionPlan:
    """按 patch 更新订阅套餐字段。"""
    for key, value in patch.items():
        if value is not None and hasattr(plan, key):
            setattr(plan, key, value)
    await session.flush()
    await session.refresh(plan)
    return plan


async def create_user_subscription(
    session: AsyncSession,
    *,
    user_id: int,
    plan_id: int,
    expires_at: datetime | None = None,
) -> UserSubscription:
    """为用户分配订阅套餐，自动停用该用户之前的订阅。"""
    # 停用该用户之前所有激活的订阅
    result = await session.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_active.is_(True),
        ),
    )
    for old_sub in result.scalars().all():
        old_sub.is_active = False

    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan_id,
        expires_at=expires_at,
    )
    session.add(subscription)
    await session.flush()
    await session.refresh(subscription)
    return subscription


async def get_active_user_subscription(
    session: AsyncSession,
    user_id: int,
) -> UserSubscription | None:
    """获取用户当前激活的订阅。"""
    result = await session.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_active.is_(True),
        ).order_by(UserSubscription.started_at.desc()),
    )
    return result.scalars().first()
