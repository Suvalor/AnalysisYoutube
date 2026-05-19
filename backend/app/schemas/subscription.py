"""订阅套餐与用户订阅 Pydantic Schema。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SubscriptionPlanCreate(BaseModel):
    """创建订阅套餐请求体。"""

    name: str = Field(..., min_length=1, max_length=100, description="套餐名称")
    description: str | None = Field(None, max_length=500, description="套餐描述")
    quotas_json: dict = Field(
        ...,
        description='配额 JSON，如 {"youtube_api": 100, "llm_api": 50, "cv_api": 20}',
    )
    price_monthly: Decimal = Field(..., ge=0, description="月价格")


class SubscriptionPlanRead(BaseModel):
    """订阅套餐返回体。"""

    id: int
    name: str
    description: str | None = None
    quotas_json: dict
    price_monthly: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionPlanUpdate(BaseModel):
    """更新订阅套餐请求体；未出现的字段表示不修改。"""

    name: str | None = Field(None, min_length=1, max_length=100, description="套餐名称")
    description: str | None = Field(None, max_length=500, description="套餐描述")
    quotas_json: dict | None = Field(None, description="配额 JSON")
    price_monthly: Decimal | None = Field(None, ge=0, description="月价格")
    is_active: bool | None = Field(None, description="是否启用")


class UserSubscriptionCreate(BaseModel):
    """为用户分配订阅套餐请求体。"""

    user_id: int = Field(..., gt=0, description="用户 ID")
    plan_id: int = Field(..., gt=0, description="套餐 ID")
    expires_at: datetime | None = Field(None, description="到期时间，null 表示永不过期")


class UserSubscriptionRead(BaseModel):
    """用户订阅返回体。"""

    id: int
    user_id: int
    plan_id: int
    started_at: datetime
    expires_at: datetime | None = None
    is_active: bool
    plan: SubscriptionPlanRead | None = None

    model_config = {"from_attributes": True}
