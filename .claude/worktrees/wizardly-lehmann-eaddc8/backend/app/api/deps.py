"""API 依赖与当前用户解析。

数据隔离说明：用户归属 ``org_id``（组织）；云存储、YouTube 等集成配置以 **组织** 维度共享（``org_settings``）。
业务资源仍以 ``current_user.id`` 为主键隔离（灵感、素材、模型库、SOP 等），避免横向越权。
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jose.exceptions import ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.crud.user import get_user_by_email
from app.db.session import get_session
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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

