import json

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, CurrentUserDep, DBSessionDep
from app.crud.user import update_user_role, update_user_settings
from app.models.user import User, UserRole
from app.schemas.auth import UserRead
from app.schemas.user import UserRoleUpdate, UserSettingsRead, UserSettingsUpdate
from app.services.field_encryption import encrypt_plaintext


router = APIRouter()


def _to_settings_read(user: User) -> UserSettingsRead:
    return UserSettingsRead(
        feishu_doc_url=user.feishu_doc_url,
        ai_api_base_url=user.ai_api_base_url,
        ai_models_json=user.ai_models_json,
        ai_prompt_config_json=user.ai_prompt_config_json,
        has_ai_api_key=bool(user.ai_api_key_encrypted and user.ai_api_key_encrypted.strip()),
        theme=user.theme,
        locale=user.locale,
    )


def _validate_json_string(field_name: str, raw: str | None) -> None:
    if raw is None:
        return
    s = raw.strip()
    if not s:
        return
    try:
        json.loads(s)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} 必须是合法 JSON：{e}",
        ) from e


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
    incoming = settings_in.model_dump(exclude_unset=True)
    patch: dict = {}

    if "feishu_doc_url" in incoming:
        patch["feishu_doc_url"] = incoming["feishu_doc_url"]

    if "ai_api_base_url" in incoming:
        v = incoming["ai_api_base_url"]
        patch["ai_api_base_url"] = None if v is None else (str(v).strip() or None)

    if "ai_models_json" in incoming:
        v = incoming["ai_models_json"]
        if v is None:
            patch["ai_models_json"] = None
        else:
            s = str(v).strip()
            if s:
                _validate_json_string("ai_models_json", s)
            patch["ai_models_json"] = s or None

    if "ai_prompt_config_json" in incoming:
        v = incoming["ai_prompt_config_json"]
        if v is None:
            patch["ai_prompt_config_json"] = None
        else:
            s = str(v).strip()
            if s:
                _validate_json_string("ai_prompt_config_json", s)
            patch["ai_prompt_config_json"] = s or None

    if "ai_api_key" in incoming:
        key_val = incoming["ai_api_key"]
        if key_val is not None and str(key_val).strip():
            try:
                patch["ai_api_key_encrypted"] = encrypt_plaintext(str(key_val).strip())
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e),
                ) from e

    if "theme" in incoming:
        v = incoming["theme"]
        valid_themes = {"light", "liblib-dark", "deep-blue", "warm-orange"}
        if v is None:
            patch["theme"] = None
        elif str(v).strip() in valid_themes:
            patch["theme"] = str(v).strip()
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效主题值：{v}，可选值：{', '.join(sorted(valid_themes))}",
            )

    if "locale" in incoming:
        v = incoming["locale"]
        valid_locales = {"zh-CN", "en-US", "ja-JP", "ko-KR"}
        if v is None:
            patch["locale"] = None
        elif str(v).strip() in valid_locales:
            patch["locale"] = str(v).strip()
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效语言值：{v}，可选值：{', '.join(sorted(valid_locales))}",
            )

    user = await update_user_settings(db, current_user, patch=patch)
    return _to_settings_read(user)


@router.patch(
    "/{user_id}/role",
    response_model=UserRead,
    summary="管理员修改用户角色",
)
async def patch_user_role(
    user_id: int,
    role_in: UserRoleUpdate,
    db: DBSessionDep,
    _admin: AdminDep,
) -> UserRead:
    """管理员修改指定用户的角色，不允许设为 guest。"""
    # 验证角色值合法性（不允许设为 guest）
    allowed_roles = {UserRole.USER, UserRole.SUBSCRIBER, UserRole.ADMIN}
    if role_in.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不允许的角色值：{role_in.role}，仅允许 {', '.join(sorted(allowed_roles))}",
        )
    try:
        user = await update_user_role(db, user_id, role_in.role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    return UserRead.model_validate(user)
