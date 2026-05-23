"""API 依赖与当前用户解析。

数据隔离说明：用户归属 ``org_id``（组织）；云存储、YouTube 等集成配置以 **组织** 维度共享（``org_settings``）。
业务资源仍以 ``current_user.id`` 为主键隔离（灵感、素材、模型库、SOP 等），避免横向越权。
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jose.exceptions import ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.crud.user import get_user_by_email
from app.db.session import get_session
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# 可选认证：未登录时不抛异常，返回 None
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


DBSessionDep = Annotated[AsyncSession, Depends(get_session)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(
    db: DBSessionDep,
    token: TokenDep,
) -> User:
    """根据 JWT 解析当前用户，后续受保护接口可复用。"""
    www = {"WWW-Authenticate": "Bearer"}
    try:
        payload = decode_access_token(token)
        subject: str | None = payload.get("sub")  # type: ignore[assignment]
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌缺少主体信息，请重新登录",
                headers=www,
            )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录",
            headers=www,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或密钥已变更，请重新登录",
            headers=www,
        )

    user = await get_user_by_email(db, subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在，请重新注册或登录",
            headers=www,
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers=www,
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    db: DBSessionDep,
    token: str | None = Depends(oauth2_scheme_optional),
) -> User | None:
    """获取当前用户，未登录时返回 None 而非 401。用于配额检查等可选认证场景。"""
    if token is None:
        return None
    try:
        payload = decode_access_token(token)
        subject: str | None = payload.get("sub")  # type: ignore[assignment]
        if subject is None:
            return None
        user = await get_user_by_email(db, subject)
        if user is None or not user.is_active:
            return None
        return user
    except (JWTError, ExpiredSignatureError):
        return None


OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]


async def require_admin(
    user: CurrentUserDep,
) -> User:
    """要求当前用户必须是 admin 角色，否则 403。"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


AdminDep = Annotated[User, Depends(require_admin)]


async def enforce_user_quota(db: DBSessionDep, user: User, api_type: str) -> None:
    """对已登录用户执行一次指定 API 类型的配额检查并计数。"""
    from app.services.rate_limit_service import check_quota, increment_usage
    from app.crud.subscription_crud import get_active_user_subscription

    subscription_quotas = None
    if user.role == UserRole.SUBSCRIBER:
        sub = await get_active_user_subscription(db, user.id)
        if sub and sub.plan:
            subscription_quotas = sub.plan.quotas_json

    allowed, used, limit = await check_quota(
        db,
        user_id=user.id,
        role=user.role,
        guest_id=None,
        api_type=api_type,
        subscription_quotas=subscription_quotas,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"配额已用尽：{api_type} 已用 {used}/{limit}，请升级套餐或明日再试",
        )

    await increment_usage(
        db,
        user_id=user.id,
        role=user.role,
        guest_id=None,
        api_type=api_type,
    )
    await db.commit()


async def get_guest_info(
    request: Request,
    db: DBSessionDep,
) -> "GuestInfo":
    """从 Cookie/IP 识别游客，返回 GuestInfo 对象。"""
    from app.services.guest_service import identify_guest

    return await identify_guest(request, db)


GuestInfoDep = Annotated["GuestInfo", Depends(get_guest_info)]


def create_quota_guard(api_type: str):
    """创建配额检查依赖工厂，用于在 YouTube/LLM/CV API 调用前检查配额。

    用法：在路由函数参数中添加 quota_check: bool = Depends(create_quota_guard("youtube_api"))
    """
    async def _check_quota(
        db: DBSessionDep,
        user: OptionalUserDep,
        guest_info: GuestInfoDep,
    ) -> bool:
        """执行配额检查，超限则抛出 429。"""
        from app.services.rate_limit_service import check_quota, increment_usage

        if user:
            await enforce_user_quota(db, user, api_type)
            return True
        else:
            role = UserRole.GUEST
            user_id = None
            guest_id = guest_info.guest_id
            subscription_quotas = None

        allowed, used, limit = await check_quota(
            db,
            user_id=user_id,
            role=role,
            guest_id=guest_id,
            api_type=api_type,
            subscription_quotas=subscription_quotas,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"配额已用尽：{api_type} 已用 {used}/{limit}，请升级套餐或明日再试",
            )
        # 检查通过后立即计数
        await increment_usage(
            db,
            user_id=user_id,
            role=role,
            guest_id=guest_id,
            api_type=api_type,
        )
        await db.commit()
        return True

    return _check_quota
