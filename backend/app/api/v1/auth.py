from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import DBSessionDep
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.crud.user import create_user, get_user_by_email
from app.schemas.auth import Token, UserCreate, UserLogin, UserRead


router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(
    user_in: UserCreate,
    db: DBSessionDep,
) -> UserRead:
    """注册新用户。"""
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )

    hashed_password = get_password_hash(user_in.password)
    try:
        user = await create_user(db, user_in, hashed_password)
    except IntegrityError:
        # 再次兜底唯一约束
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
)
async def login(
    login_in: UserLogin,
    db: DBSessionDep,
) -> Token:
    """用户登录并返回 JWT。"""
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

