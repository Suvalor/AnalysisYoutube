"""认证路由：注册、登录、邀请码、密码重置等。"""

from datetime import datetime, timedelta, timezone
import logging
import secrets
import string
import time

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminDep, DBSessionDep
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, get_password_hash, verify_password
from app.crud.admin_invitation_crud import (
    create_admin_invitation,
    get_invitation_by_code,
    mark_invitation_used,
)
from app.crud.user import create_user, get_user_by_email, get_user_by_phone
from app.models.user import UserRole
from app.schemas.admin_invitation import (
    AdminInvitationCreate,
    AdminInvitationRead,
    AdminInvitationVerify,
)
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
    """注册新用户：邮箱+邮箱验证码，手机号可选，邀请码可选（注册为 admin）。"""
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

    # 4. 处理邀请码：如果提供了 invite_code，验证并决定角色
    role = UserRole.USER
    invitation = None
    if user_in.invite_code:
        invitation = await get_invitation_by_code(db, user_in.invite_code)
        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请码不存在",
            )
        if not invitation.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请码已被使用",
            )
        if invitation.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请码已过期",
            )
        role = UserRole.ADMIN

    # 5. 创建用户
    hashed_password = get_password_hash(user_in.password)
    try:
        user = await create_user(
            db,
            email=user_in.email,
            hashed_password=hashed_password,
            phone=user_in.phone,
            role=role,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="注册信息冲突，请检查邮箱和手机号",
        )

    # 6. 如果使用了邀请码，标记为已使用
    if invitation:
        await mark_invitation_used(db, invitation, user.id)
        await db.commit()
        await db.refresh(user)

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
    """用户登录：校验图形验证码 + 邮箱密码，返回 JWT（含 role）。"""
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
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer", role=user.role)


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
    # 发送邮件，失败时返回错误提示
    ok = await send_reset_password_email(to_email=body.email, reset_url=reset_url)
    if not ok:
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


# ---------- 邀请码验证速率限制（IP 级别防枚举） ----------

# {ip: {"fail_count": int, "locked_until": float | None}}
_invite_verify_attempts: dict[str, dict] = {}

_INVITE_VERIFY_MAX_FAILS = 5  # 连续失败 5 次后锁定
_INVITE_VERIFY_LOCK_SECONDS = 15 * 60  # 锁定 15 分钟
_INVITE_VERIFY_PER_MINUTE = 5  # 每 IP 每分钟最多 5 次验证

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    """从请求中提取客户端 IP，优先读取反向代理头。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def _check_invite_verify_rate_limit(ip: str) -> None:
    """检查邀请码验证的 IP 级别速率限制，超限则抛出 429。"""
    now = time.time()
    record = _invite_verify_attempts.get(ip, {"fail_count": 0, "locked_until": None})

    # 检查是否处于锁定状态
    if record.get("locked_until") and now < record["locked_until"]:
        remaining = int(record["locked_until"] - now)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"验证尝试过于频繁，请 {remaining} 秒后再试",
        )

    # 检查每分钟调用次数（滑动窗口：简单实现，清理超过 1 分钟的记录）
    # 此处仅做基础防护，精确滑动窗口由 slowapi @limiter 处理


def _record_invite_verify_failure(ip: str) -> None:
    """记录邀请码验证失败，连续失败达阈值后锁定 IP。"""
    now = time.time()
    record = _invite_verify_attempts.get(ip, {"fail_count": 0, "locked_until": None})

    # 如果之前锁定已过期，重置计数
    if record.get("locked_until") and now >= record["locked_until"]:
        record["fail_count"] = 0
        record["locked_until"] = None

    record["fail_count"] = record.get("fail_count", 0) + 1

    if record["fail_count"] >= _INVITE_VERIFY_MAX_FAILS:
        record["locked_until"] = now + _INVITE_VERIFY_LOCK_SECONDS
        logger.warning("邀请码验证 IP 锁定: ip=%s, fail_count=%d", ip, record["fail_count"])

    _invite_verify_attempts[ip] = record


def _record_invite_verify_success(ip: str) -> None:
    """邀请码验证成功时重置该 IP 的失败计数。"""
    _invite_verify_attempts.pop(ip, None)


# ---------- 管理员邀请码 ----------


def _generate_invite_code(length: int = 6) -> str:
    """生成随机邀请码（大写字母+数字，排除易混淆字符）。"""
    chars = string.ascii_uppercase + string.digits
    # 排除易混淆字符 O/0, I/1, L
    safe_chars = [c for c in chars if c not in {"O", "0", "I", "1", "L"}]
    return "".join(secrets.choice(safe_chars) for _ in range(length))


@router.post(
    "/admin-invite",
    response_model=AdminInvitationRead,
    status_code=status.HTTP_201_CREATED,
    summary="生成管理员邀请码",
)
async def create_admin_invite(
    admin: AdminDep,
    db: DBSessionDep,
) -> AdminInvitationRead:
    """管理员生成邀请码，有效期 7 天。"""
    code = _generate_invite_code()
    invitation = await create_admin_invitation(db, created_by=admin.id, code=code)
    await db.commit()
    await db.refresh(invitation)
    return AdminInvitationRead.model_validate(invitation)


@router.get(
    "/admin-invite/verify",
    response_model=AdminInvitationVerify,
    summary="验证管理员邀请码",
)
@limiter.limit("5/minute")
async def verify_admin_invite(
    request: Request,
    code: str,
    db: DBSessionDep,
) -> AdminInvitationVerify:
    """验证邀请码是否有效（未使用、未过期、激活状态）。

    安全措施：IP 级别速率限制，连续失败 5 次后锁定 15 分钟；
    验证失败时返回通用错误消息，不区分不存在/已使用/已过期。
    """
    ip = _get_client_ip(request)
    _check_invite_verify_rate_limit(ip)

    invitation = await get_invitation_by_code(db, code)
    # 统一判断：不存在、已使用、已过期均视为无效，不暴露具体原因
    is_valid = (
        invitation is not None
        and invitation.is_active
        and invitation.expires_at >= datetime.now(timezone.utc)
    )

    if is_valid:
        _record_invite_verify_success(ip)
        return AdminInvitationVerify(valid=True, code=code)

    _record_invite_verify_failure(ip)
    return AdminInvitationVerify(valid=False, code=code)