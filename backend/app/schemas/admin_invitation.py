"""管理员邀请码 Pydantic Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class AdminInvitationCreate(BaseModel):
    """生成管理员邀请码请求体（当前无额外参数，预留扩展）。"""

    pass


class AdminInvitationRead(BaseModel):
    """管理员邀请码返回体。"""

    id: int
    code: str
    created_by: int
    used_by: int | None = None
    used_at: datetime | None = None
    expires_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class AdminInvitationVerify(BaseModel):
    """验证邀请码返回体。"""

    valid: bool = Field(..., description="邀请码是否有效")
    code: str = Field(..., description="邀请码")
