"""即梦 AI 图片生成路由。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserDep, create_quota_guard
from app.db.session import get_session
from app.crud.library import get_by_user
from app.models.library import ModelLibrary
from app.schemas.jimeng import JimengQueryRequest, JimengSubmitRequest
from app.services.jimeng_service import JimengConfig, query_task_status, submit_task
from app.services.field_encryption import try_decrypt

router = APIRouter()


async def _resolve_jimeng_config(
    db: AsyncSession,
    user_id: int,
    org_id: int,
) -> JimengConfig:
    """从 model_libraries 表解析即梦运行时配置。

    仅查找当前用户关联的 jimeng 模型库，不做 org 级回退。
    若未配置则抛 400，提示用户在智能体管理中配置。
    """
    from app.services.integration_config_service import resolve_integration_config

    # 尝试通过 org 级配置找到 jimeng 的 model_library_id
    integration_cfg = await resolve_integration_config(db, org_id)
    jimeng_library_id = integration_cfg.get("jimeng_model_library_id")

    ml: ModelLibrary | None = None
    if jimeng_library_id:
        ml = await get_by_user(db, ModelLibrary, user_id, int(jimeng_library_id))

    if ml is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置即梦 AI，请在智能体管理中添加即梦模型配置",
        )

    api_key = try_decrypt(ml.api_key_encrypted) if ml.api_key_encrypted else ""
    api_base_url = ml.base_url or ""

    return JimengConfig(api_key=api_key, api_base_url=api_base_url)


@router.post("/submit")
async def jimeng_submit(
    req: JimengSubmitRequest,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_session),
    _quota: bool = Depends(create_quota_guard("cv_api")),
) -> dict[str, Any]:
    cfg = await _resolve_jimeng_config(db, user.id, user.org_id)
    return await submit_task(
        cfg=cfg,
        model_name=req.model_name,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        params=req.params or {},
    )


@router.post("/status")
async def jimeng_status(
    req: JimengQueryRequest,
    user: CurrentUserDep,
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    cfg = await _resolve_jimeng_config(db, user.id, user.org_id)
    return await query_task_status(cfg=cfg, task_id=req.task_id)
