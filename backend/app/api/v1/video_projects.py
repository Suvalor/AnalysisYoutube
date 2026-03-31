from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, DBSessionDep
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

