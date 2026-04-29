from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.download_task import DownloadStatus, DownloadTask
from app.models.youtube import YouTubeChannel, YouTubeVideo
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

    # Pre-fetch video metadata from youtube_videos for all video_ids
    yt_video_ids = [vid for vid in payload.video_ids]
    video_meta: dict[str, tuple[str | None, str | None]] = {}
    if yt_video_ids:
        meta_rows = await db.execute(
            select(YouTubeVideo.yt_video_id, YouTubeVideo.title, YouTubeVideo.thumbnail_url)
            .where(YouTubeVideo.yt_video_id.in_(yt_video_ids))
        )
        for yt_vid, title, thumb in meta_rows.all():
            video_meta[yt_vid] = (title, thumb)

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

        title, thumb = video_meta.get(video_id, (None, None))
        task = DownloadTask(user_id=current_user.id, video_id=video_id, video_title=title, thumbnail_url=thumb)
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

    # Enrich with youtube_videos + youtube_channels data via JOIN
    video_ids = [r.video_id for r in rows]
    video_map: dict[str, dict] = {}
    if video_ids:
        vid_rows = await db.execute(
            select(
                YouTubeVideo.yt_video_id,
                YouTubeVideo.title,
                YouTubeVideo.thumbnail_url,
                YouTubeVideo.published_at,
                YouTubeVideo.view_count,
                YouTubeVideo.like_count,
                YouTubeVideo.comment_count,
                YouTubeChannel.title,
            )
            .outerjoin(YouTubeChannel, YouTubeVideo.channel_id == YouTubeChannel.id)
            .where(YouTubeVideo.yt_video_id.in_(video_ids))
        )
        for yt_vid, title, thumb, pub, views, likes, comments, ch_title in vid_rows.all():
            video_map[yt_vid] = {
                "title": title,
                "thumbnail_url": thumb,
                "published_at": pub,
                "view_count": views,
                "like_count": likes,
                "comment_count": comments,
                "channel_title": ch_title,
            }

    items: list[DownloadTaskRead] = []
    for r in rows:
        d = DownloadTaskRead.model_validate(r)
        vm = video_map.get(r.video_id)
        if vm:
            if not d.video_title and vm["title"]:
                d.video_title = vm["title"]
            if not d.thumbnail_url and vm["thumbnail_url"]:
                d.thumbnail_url = vm["thumbnail_url"]
            d.video_channel_title = vm["channel_title"]
            d.video_published_at = vm["published_at"]
            d.video_view_count = vm["view_count"]
            d.video_like_count = vm["like_count"]
            d.video_comment_count = vm["comment_count"]
        items.append(d)

    return DownloadTaskListResponse(items=items, total=total)


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

    d = DownloadTaskRead.model_validate(task)
    # Enrich with youtube_videos + youtube_channels
    vid_row = await db.execute(
        select(
            YouTubeVideo.title,
            YouTubeVideo.thumbnail_url,
            YouTubeVideo.published_at,
            YouTubeVideo.view_count,
            YouTubeVideo.like_count,
            YouTubeVideo.comment_count,
            YouTubeChannel.title,
        )
        .outerjoin(YouTubeChannel, YouTubeVideo.channel_id == YouTubeChannel.id)
        .where(YouTubeVideo.yt_video_id == task.video_id)
    )
    row = vid_row.first()
    if row:
        v_title, thumb, pub, views, likes, comments, ch_title = row._asdict() if hasattr(row, '_asdict') else row
        if not d.video_title and v_title:
            d.video_title = v_title
        if not d.thumbnail_url and thumb:
            d.thumbnail_url = thumb
        d.video_channel_title = ch_title
        d.video_published_at = pub
        d.video_view_count = views
        d.video_like_count = likes
        d.video_comment_count = comments
    return d


@router.get("/download-tasks/{task_id}/file")
async def serve_download_task_file(
    task_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> FileResponse:
    """Serve the downloaded video file for playback.

    Only available when the task status is COMPLETED and the file exists on disk.
    """
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    if task.status != DownloadStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="下载尚未完成")

    file_path = Path(task.local_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    # Determine media type from extension.
    media_type = "video/mp4"
    if file_path.suffix.lower() in (".webm",):
        media_type = "video/webm"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )


@router.post("/download-tasks/{task_id}/retry", response_model=DownloadTaskRead)
async def retry_download_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> DownloadTaskRead:
    """Retry a failed download task by resetting its status and re-queueing."""
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    if task.status not in (DownloadStatus.FAILED, DownloadStatus.COMPLETED):
        raise HTTPException(status_code=400, detail="仅失败或已完成的任务可重试")

    # Clean up existing file if retrying a completed task
    if task.local_path:
        old_file = Path(task.local_path)
        if old_file.is_file():
            old_file.unlink(missing_ok=True)

    task.status = DownloadStatus.PENDING
    task.progress = 0.0
    task.error_message = ""
    task.local_path = ""
    task.file_size = 0
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(run_download_task, task.id, current_user.id)
    return DownloadTaskRead.model_validate(task)
