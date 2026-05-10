from __future__ import annotations

import secrets
import time
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.download_task import DownloadStatus, DownloadTask
from app.models.youtube import YouTubeChannel, YouTubeVideo
from app.schemas.download_task import DownloadRequest, DownloadTaskListResponse, DownloadTaskRead
from app.services.downloader_service import VIDEO_ID_RE, run_download_task

router = APIRouter()

# ---------------------------------------------------------------------------
# Play-token store (C-01: short-lived, single-use tokens for video playback)
# ---------------------------------------------------------------------------
_play_tokens: dict[str, tuple[int, int, float]] = {}  # token -> (task_id, user_id, expires_at)
_PLAY_TOKEN_TTL = 60  # seconds

# Optional OAuth2 scheme for the file-serving endpoint: when a play_token is
# provided we skip header-based auth entirely, so this must not auto-error.
_optional_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


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
    """List download tasks for the current user with optional status filter.
    Only the most recent task per video_id is returned (deduplication).
    """
    # Subquery: max id per video_id for this user (deduplication).
    # C-02: status filter must be inside the subquery so that dedup only
    # considers tasks matching the current filter, preventing semantic errors
    # where a non-matching newer task shadows an older matching one.
    dedup_base = select(func.max(DownloadTask.id)).where(DownloadTask.user_id == current_user.id)
    if status is not None:
        dedup_base = dedup_base.where(DownloadTask.status == status.value)
    max_id_subq = dedup_base.group_by(DownloadTask.video_id).scalar_subquery()

    base = select(DownloadTask).where(
        DownloadTask.user_id == current_user.id,
        DownloadTask.id.in_(max_id_subq),
    )
    count_base = select(func.count()).select_from(DownloadTask).where(
        DownloadTask.user_id == current_user.id,
        DownloadTask.id.in_(max_id_subq),
    )

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
        v_title, thumb, pub, views, likes, comments, ch_title = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
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


@router.post("/download-tasks/{task_id}/play-token", response_model=dict)
async def create_play_token(
    task_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """Generate a short-lived, single-use play token for video playback.

    The token replaces the previous approach of passing the full JWT in the URL
    query parameter, which leaked credentials to server logs, browser history,
    and referrer headers.
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
    if not task.local_path:
        raise HTTPException(status_code=400, detail="文件不存在")

    token = secrets.token_urlsafe(32)
    _play_tokens[token] = (task_id, current_user.id, time.monotonic() + _PLAY_TOKEN_TTL)
    return {"play_token": token}


@router.get("/download-tasks/{task_id}/file")
async def serve_download_task_file(
    task_id: int,
    db: DBSessionDep,
    play_token: str | None = Query(default=None, description="Short-lived play token"),
    authorization: str | None = Depends(_optional_oauth2),
) -> FileResponse:
    """Serve the downloaded video file for playback.

    Only available when the task status is COMPLETED and the file exists on disk.
    Authenticates via a short-lived play_token query parameter (preferred) or
    falls back to Authorization header for backward compatibility.
    """
    from app.core.security import decode_access_token
    from app.crud.user import get_user_by_email
    from jose import JWTError

    resolved_user_id: int | None = None

    if play_token is not None:
        # C-01: use short-lived, single-use play token
        entry = _play_tokens.pop(play_token, None)
        if entry is None:
            raise HTTPException(status_code=401, detail="播放令牌无效或已使用")
        stored_task_id, stored_user_id, expires_at = entry
        if time.monotonic() > expires_at:
            raise HTTPException(status_code=401, detail="播放令牌已过期")
        if stored_task_id != task_id:
            raise HTTPException(status_code=403, detail="播放令牌与任务不匹配")
        resolved_user_id = stored_user_id
    elif authorization is not None:
        # Backward-compatible fallback: resolve JWT from Authorization header
        www = {"WWW-Authenticate": "Bearer"}
        try:
            payload = decode_access_token(authorization)
            subject: str | None = payload.get("sub")
            if subject is None:
                raise HTTPException(status_code=401, detail="令牌缺少主体信息", headers=www)
        except JWTError:
            raise HTTPException(status_code=401, detail="令牌无效或已过期", headers=www)
        user = await get_user_by_email(db, subject)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="用户不存在或已被禁用", headers=www)
        resolved_user_id = user.id
    else:
        raise HTTPException(status_code=401, detail="未认证")

    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == resolved_user_id,
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


@router.delete("/download-tasks/{task_id}", response_model=dict)
async def delete_download_task(
    task_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """Delete a failed download task and clean up its local file."""
    # C-03: lock the row to prevent race condition between status check and delete
    result = await db.execute(
        select(DownloadTask)
        .where(DownloadTask.id == task_id, DownloadTask.user_id == current_user.id)
        .with_for_update()
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    if task.status != DownloadStatus.FAILED:
        raise HTTPException(status_code=400, detail="仅失败的任务可删除")

    # Clean up local file if it exists
    if task.local_path:
        old_file = Path(task.local_path)
        if old_file.is_file():
            old_file.unlink(missing_ok=True)

    await db.delete(task)
    await db.commit()
    return {"message": "已删除"}
