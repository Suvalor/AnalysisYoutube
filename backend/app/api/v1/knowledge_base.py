"""
知识库手动新建：与 AI 脚本工坊、POST /libraries/scripts 解耦。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.library import ScriptLibrary
from app.schemas.library import ManualKnowledgeScriptCreate, ScriptRead
from app.services.markdown_sanitize import sanitize_manual_knowledge_markdown


router = APIRouter()


@router.post("/manual-create", response_model=ScriptRead, summary="知识库手动新建剧本")
async def manual_create_script(
    body: ManualKnowledgeScriptCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ScriptRead:
    """
    与 AI 脚本工坊保存逻辑对齐：title 独立字段，content 为 Markdown 正文（工坊侧为模型流式输出原文）。
    正文经消毒后再写入，避免危险 HTML/链接协议进入库内。
    """
    try:
        plot_safe = sanitize_manual_knowledge_markdown(body.plot)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    row = ScriptLibrary(
        user_id=current_user.id,
        title=body.title.strip(),
        content=plot_safe,
        prompt_id=None,
        style_id=None,
        origin_type="MANUAL",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ScriptRead.model_validate(row)
