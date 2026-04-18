from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    """登录请求体."""

    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, max_length=128, description="明文密码")
    captcha_id: str = Field(..., description="验证码ID")
    captcha_code: str = Field(..., min_length=4, max_length=4, description="验证码")


class UserRead(BaseModel):
    """返回给前端的用户信息."""

    id: int
    email: EmailStr
    phone: str | None = None
    email_verified: bool = False
    created_at: datetime
    is_active: bool

    model_config = {
        "from_attributes": True,
    }


class Token(BaseModel):
    """JWT 访问令牌响应."""

    access_token: str
    token_type: str = "bearer"


# ---------- 新增：图形验证码 ----------

class CaptchaResponse(BaseModel):
    """图形验证码响应."""

    captcha_id: str = Field(..., description="验证码ID")
    captcha_image: str = Field(..., description="Base64编码的验证码图片")


# ---------- 新增：注册（手机号+邮箱+验证码） ----------

class RegisterRequest(BaseModel):
    """注册请求体（手机号+邮箱+验证码）."""

    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, max_length=128, description="明文密码")
    email_code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")


# ---------- 新增：发送邮箱验证码 ----------

class SendEmailCodeRequest(BaseModel):
    """发送邮箱验证码请求."""

    email: EmailStr = Field(..., description="邮箱地址")


# ---------- 新增：忘记密码 ----------

class ForgotPasswordRequest(BaseModel):
    """忘记密码请求（通过邮箱发送重置链接）."""

    email: EmailStr = Field(..., description="注册时使用的邮箱")


# ---------- 新增：重置密码 ----------

class ResetPasswordRequest(BaseModel):
    """重置密码请求."""

    token: str = Field(..., description="重置Token")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
