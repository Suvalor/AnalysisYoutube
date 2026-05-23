from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep, DBSessionDep, create_quota_guard
from app.crud.video_project import (
    create_video_project,
    delete_video_project,
    get_video_project,
    list_video_projects,
    reorder_video_projects,
    update_video_project,
)
from app.schemas.video_project import (
    VALID_STATUSES,
    VideoProjectCreate,
    VideoProjectRead,
    VideoProjectReorderItem,
    VideoProjectUpdate,
)


router = APIRouter()


@router.get("", response_model=list[VideoProjectRead])
async def list_projects(db: DBSessionDep, current_user: CurrentUserDep) -> list[VideoProjectRead]:
    rows = await list_video_projects(db, current_user.id)
    return [VideoProjectRead.model_validate(x) for x in rows]


@router.post("", response_model=VideoProjectRead)
async def create_project(
    payload: VideoProjectCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> VideoProjectRead:
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="非法状态")
    row = await create_video_project(
        db,
        user_id=current_user.id,
        title=payload.title,
        status=payload.status,
        script_id=payload.script_id,
        due_date=payload.due_date,
    )
    return VideoProjectRead.model_validate(row)


@router.put("/reorder")
async def reorder_projects(
    payload: list[VideoProjectReorderItem],
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict[str, str]:
    for item in payload:
        if item.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"非法状态: {item.status}")
    await reorder_video_projects(
        db,
        user_id=current_user.id,
        items=[(item.id, item.status, item.order_index) for item in payload],
    )
    return {"message": "排序更新成功"}


@router.get("/{project_id}", response_model=VideoProjectRead)
async def get_project(project_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> VideoProjectRead:
    row = await get_video_project(db, current_user.id, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return VideoProjectRead.model_validate(row)


@router.put("/{project_id}", response_model=VideoProjectRead)
async def update_project(
    project_id: int,
    payload: VideoProjectUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> VideoProjectRead:
    row = await get_video_project(db, current_user.id, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="非法状态")
    row = await update_video_project(db, row, updates)
    return VideoProjectRead.model_validate(row)


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = await get_video_project(db, current_user.id, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    await delete_video_project(db, row)
    return {"message": "删除成功"}


@router.post("/ai-suggest", summary="AI 内容策略建议")
async def ai_suggest(
    body: dict,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    _quota: bool = Depends(create_quota_guard("llm_api")),
) -> dict:
    """
    基于视频看板项目数据，调用 LLM 生成内容策略建议。
    入参: { project_ids?: list[int], model_library_id?: int, llm_model_name?: str, agent_id?: int }
    """
    from app.services.video_board_ai_service import generate_video_board_ai_suggestion
    from app.services.llm_conversation_service import save_conversation_turn

    result = await generate_video_board_ai_suggestion(
        db,
        user_id=current_user.id,
        project_ids=body.get("project_ids"),
        model_library_id=body.get("model_library_id"),
        llm_model_name=body.get("llm_model_name"),
        agent_id=body.get("agent_id"),
    )

    # 保存对话历史
    entity_type = "video_board_suggest"
    entity_id = f"user:{current_user.id}"
    if result.get("_user_prompt") and result.get("_assistant_content"):
        try:
            await save_conversation_turn(
                db,
                user_id=current_user.id,
                entity_type=entity_type,
                entity_id=entity_id,
                user_content=result["_user_prompt"],
                assistant_content=result["_assistant_content"],
                system_content=result.get("_system_prompt"),
                model_name=body.get("llm_model_name"),
            )
            await db.commit()
        except Exception:  # noqa: BLE001
            import logging as _logging
            _logging.getLogger(__name__).exception("保存视频看板 AI 建议对话历史失败")
            await db.rollback()

    return {
        "suggestion": result.get("suggestion", {}),
        "conversation_id": f"{entity_type}:{entity_id}",
    }
