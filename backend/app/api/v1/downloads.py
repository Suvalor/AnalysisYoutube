from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.download_task import DownloadStatus, DownloadTask
from app.schemas.download_task import DownloadRequest, DownloadTaskListResponse, DownloadTaskRead
from app.services.downloader_service import VIDEO_ID_RE, run_download_task

router = APIRouter()


@router.post("/download", response_model=dict)
async def create_download_tasks(
    payload: DownloadRequest,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """Submit video download tasks. Returns immediately; downloads run in background."""
    # Validate all video_ids before creating any tasks
    invalid_ids = [vid for vid in payload.video_ids if not VIDEO_ID_RE.match(vid)]
    if invalid_ids:
        raise HTTPException(status_code=400, detail=f"无效的视频 ID: {invalid_ids[:3]}")

    tasks: list[DownloadTask] = []
    skipped: list[str] = []

    for video_id in payload.video_ids:
        # Skip if a non-terminal task already exists for this user+video
        existing = await db.execute(
            select(DownloadTask).where(
                DownloadTask.user_id == current_user.id,
                DownloadTask.video_id == video_id,
                DownloadTask.status.in_([DownloadStatus.PENDING, DownloadStatus.DOWNLOADING]),
            )
        )
        if existing.scalar_one_or_none() is not None:
            skipped.append(video_id)
            continue

        task = DownloadTask(user_id=current_user.id, video_id=video_id)
        db.add(task)
        tasks.append(task)

    if tasks:
        await db.commit()
        for task in tasks:
            await db.refresh(task)
            background_tasks.add_task(run_download_task, task.id, current_user.id)

    return {
        "message": "下载任务已加入队列",
        "task_count": len(tasks),
        "skipped": skipped,
    }


@router.get("/download-tasks", response_model=DownloadTaskListResponse)
async def list_download_tasks(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    status: DownloadStatus | None = Query(default=None, description="筛选状态"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> DownloadTaskListResponse:
    """List download tasks for the current user with optional status filter."""
    base = select(DownloadTask).where(DownloadTask.user_id == current_user.id)
    count_base = select(func.count()).select_from(DownloadTask).where(DownloadTask.user_id == current_user.id)

    if status is not None:
        base = base.where(DownloadTask.status == status.value)
        count_base = count_base.where(DownloadTask.status == status.value)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (
        await db.execute(base.order_by(DownloadTask.id.desc()).offset(offset).limit(limit))
    ).scalars().all()

    return DownloadTaskListResponse(items=[DownloadTaskRead.model_validate(r) for r in rows], total=total)


@router.get("/download-tasks/{task_id}", response_model=DownloadTaskRead)
async def get_download_task(
    task_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> DownloadTaskRead:
    """Get a single download task by ID."""
    result = await db.execute(
        select(DownloadTask).where(DownloadTask.id == task_id, DownloadTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    return DownloadTaskRead.model_validate(task)
