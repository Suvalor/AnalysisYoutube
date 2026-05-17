from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import DBSessionDep
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, get_password_hash, verify_password
from app.crud.user import create_user, get_user_by_email, get_user_by_phone
from app.schemas.auth import (
    CaptchaResponse,
    ForgotPasswordRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SendEmailCodeRequest,
    Token,
    UserLogin,
    UserRead,
)
from app.services.captcha_service import generate_captcha, verify_captcha
from app.services.email_service import (
    _email_code_store,
    can_send_code,
    create_reset_token,
    generate_email_code,
    send_reset_password_email,
    send_verification_code_email,
    store_email_code,
    verify_email_code,
    verify_reset_token,
)

router = APIRouter()


@router.get(
    "/captcha",
    response_model=CaptchaResponse,
    summary="获取图形验证码",
)
async def get_captcha() -> CaptchaResponse:
    """生成图形验证码，返回 captcha_id + base64 图片。"""
    captcha_id, captcha_image = generate_captcha()
    return CaptchaResponse(captcha_id=captcha_id, captcha_image=captcha_image)


@router.post(
    "/send-email-code",
    status_code=status.HTTP_200_OK,
    summary="发送邮箱验证码",
)
@limiter.limit("3/minute")
async def send_email_code(
    request: Request,
    body: SendEmailCodeRequest,
) -> dict:
    """发送6位数字验证码到邮箱，60秒内不可重发。"""
    allowed, msg = can_send_code(body.email)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=msg,
        )

    code = generate_email_code()
    # 先存储占位，防止并发绕过频率限制
    store_email_code(body.email, code)
    ok = await send_verification_code_email(to_email=body.email, code=code)
    if not ok:
        # 发送失败，回滚删除已存储的验证码
        _email_code_store.pop(body.email, None)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="邮件发送失败，请稍后再试",
        )

    return {"message": "验证码已发送"}


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_in: RegisterRequest,
    db: DBSessionDep,
) -> UserRead:
    """注册新用户：邮箱+邮箱验证码，手机号可选。"""
    # 1. 先检查邮箱是否已注册（避免消耗验证码）
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )

    # 2. 手机号非空时检查是否已注册
    if user_in.phone:
        existing_phone = await get_user_by_phone(db, user_in.phone)
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号已被注册",
            )

    # 3. 校验邮箱验证码（一次性使用，放在重复检查之后）
    if not verify_email_code(user_in.email, user_in.email_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱验证码错误或已过期",
        )

    # 4. 创建用户
    hashed_password = get_password_hash(user_in.password)
    try:
        user = await create_user(
            db,
            email=user_in.email,
            hashed_password=hashed_password,
            phone=user_in.phone,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="注册信息冲突，请检查邮箱和手机号",
        )
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_in: UserLogin,
    db: DBSessionDep,
) -> Token:
    """用户登录：校验图形验证码 + 邮箱密码，返回 JWT。"""
    # 1. 校验图形验证码
    if not verify_captcha(login_in.captcha_id, login_in.captcha_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图形验证码错误或已过期",
        )

    # 2. 校验邮箱密码
    user = await get_user_by_email(db, login_in.email)
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="忘记密码",
)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: DBSessionDep,
) -> dict:
    """根据邮箱发送密码重置链接。"""
    user = await get_user_by_email(db, body.email)
    if not user:
        # 安全考虑：不透露邮箱是否存在
        return {"message": "如果该邮箱已注册，重置链接已发送"}

    token = create_reset_token(body.email)
    reset_url = f"{settings.frontend_base_url}/reset-password?token={token}"
    # 发送邮件，失败时返回错误提示（不透露邮箱是否存在的情况已在上文处理）
    ok = await send_reset_password_email(to_email=body.email, reset_url=reset_url)
    if not ok:
        # 邮件发送失败，清理 token 并返回错误
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="邮件发送失败，请检查SMTP配置或稍后再试",
        )
    return {"message": "如果该邮箱已注册，重置链接已发送"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="重置密码",
)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: DBSessionDep,
) -> dict:
    """通过重置Token设置新密码。"""
    email = verify_reset_token(body.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置链接无效或已过期",
        )

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账户已被禁用",
        )

    user.hashed_password = get_password_hash(body.new_password)
    await db.commit()
    return {"message": "密码重置成功"}
