"""
知识库扩展接口：置顶等（与 libraries/scripts 列表排序配合使用）。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.library import ScriptLibrary
from app.schemas.library import KnowledgePinRequest, ScriptRead


router = APIRouter()


@router.post("/pin", response_model=ScriptRead, summary="切换知识库剧本置顶")
async def pin_knowledge_script(
    body: KnowledgePinRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ScriptRead:
    q = select(ScriptLibrary).where(
        ScriptLibrary.id == body.id,
        ScriptLibrary.user_id == current_user.id,
        ScriptLibrary.is_deleted.is_(False),
    )
    res = await db.execute(q)
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在或已删除")

    row.is_pinned = body.is_pinned
    await db.commit()
    await db.refresh(row)
    return ScriptRead.model_validate(row)
