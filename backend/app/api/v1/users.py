from fastapi import APIRouter, Depends

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.user import update_user_settings
from app.models.user import User
from app.schemas.user import UserSettingsRead, UserSettingsUpdate


router = APIRouter()


def _to_settings_read(user: User) -> UserSettingsRead:
    return UserSettingsRead(
        feishu_doc_url=user.feishu_doc_url,
    )


@router.get(
    "/me/settings",
    response_model=UserSettingsRead,
    summary="获取当前用户设置",
)
async def get_me_settings(
    current_user: CurrentUserDep,
) -> UserSettingsRead:
    """获取当前登录用户的个性化设置。"""
    return _to_settings_read(current_user)


@router.put(
    "/me/settings",
    response_model=UserSettingsRead,
    summary="更新当前用户设置",
)
async def update_me_settings(
    settings_in: UserSettingsUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> UserSettingsRead:
    """更新当前登录用户的个性化设置。"""
    user = await update_user_settings(
        db,
        current_user,
        feishu_doc_url=settings_in.feishu_doc_url,
    )
    return _to_settings_read(user)

