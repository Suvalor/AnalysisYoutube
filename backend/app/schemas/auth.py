from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """用户公共字段."""

    email: EmailStr = Field(..., description="邮箱")


class UserCreate(UserBase):
    """注册请求体."""

    password: str = Field(..., min_length=8, max_length=128, description="明文密码")


class UserLogin(UserBase):
    """登录请求体."""

    password: str = Field(..., min_length=8, max_length=128, description="明文密码")


class UserRead(UserBase):
    """返回给前端的用户信息."""

    id: int
    created_at: datetime
    is_active: bool

    model_config = {
        "from_attributes": True,
    }


class Token(BaseModel):
    """JWT 访问令牌响应."""

    access_token: str
    token_type: str = "bearer"

