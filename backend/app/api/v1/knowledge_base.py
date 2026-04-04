"""
知识库手动新建：与 AI 脚本工坊、POST /libraries/scripts 解耦。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.library import ScriptLibrary
from app.schemas.library import ManualKnowledgeScriptCreate, ScriptRead


router = APIRouter()


def _compose_manual_content(*, title: str, plot: str, emotion: str) -> str:
    """与业务展示习惯一致：首行 ### 项目 + 可选核心情绪，正文为剧情。"""
    t = title.strip()
    p = plot.strip()
    e = emotion.strip()
    if e:
        header = f"### 项目: 【{t}】 **{e}**"
    else:
        header = f"### 项目: 【{t}】"
    return f"{header}\n\n{p}"


@router.post("/manual-create", response_model=ScriptRead, summary="知识库手动新建剧本")
async def manual_create_script(
    body: ManualKnowledgeScriptCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ScriptRead:
    composed = _compose_manual_content(title=body.title, plot=body.plot, emotion=body.emotion)
    row = ScriptLibrary(
        user_id=current_user.id,
        title=body.title.strip(),
        content=composed,
        prompt_id=None,
        style_id=None,
        origin_type="MANUAL",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ScriptRead.model_validate(row)
