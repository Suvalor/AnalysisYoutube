"""yt-dlp based YouTube video download service.

Provides:
- ``download_youtube_video``: synchronous download function (safe to call in a thread).
- ``run_download_task``: async background-task entry point for FastAPI BackgroundTasks.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

import yt_dlp
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.download_task import DownloadStatus, DownloadTask

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RAW_MATERIALS_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_materials"
RAW_MATERIALS_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


# ---------------------------------------------------------------------------
# Synchronous download
# ---------------------------------------------------------------------------


def download_youtube_video(video_id: str) -> str:
    """Download a YouTube video by *video_id* and return the local file path.

    If the target file already exists and is non-empty the download is skipped
    and the existing path is returned immediately.

    Raises:
        ValueError: If video_id is not a valid YouTube video ID.
        RuntimeError: If yt-dlp reports a download error.
    """
    if not VIDEO_ID_RE.match(video_id):
        raise ValueError(f"Invalid video_id: {video_id!r}")

    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = RAW_MATERIALS_DIR / f"{video_id}.mp4"

    # Skip re-download when the file is already present and non-empty.
    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info("视频已存在，跳过下载: %s", output_path)
        return str(output_path.resolve())

    ydl_opts: dict[str, object] = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4/best",
        "outtmpl": str(output_path),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }

    if settings.download_proxy:
        logger.info("Using download proxy: %s", settings.download_proxy)
        ydl_opts["proxy"] = settings.download_proxy

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(f"下载失败 video_id={video_id}: {exc}") from exc

    return str(output_path.resolve())


# ---------------------------------------------------------------------------
# Async background task
# ---------------------------------------------------------------------------


async def run_download_task(task_id: int, user_id: int) -> None:
    """Background task: download a video and update the DownloadTask row.

    Uses a **new** database session because FastAPI BackgroundTasks execute
    after the response has been sent, at which point the request-scoped
    session is already closed.
    """
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(DownloadTask).where(
                DownloadTask.id == task_id,
                DownloadTask.user_id == user_id,
            )
            result = await db.execute(stmt)
            task = result.scalar_one_or_none()

            if task is None:
                logger.warning("DownloadTask not found: id=%d user_id=%d", task_id, user_id)
                return

            task.status = DownloadStatus.DOWNLOADING
            await db.commit()

            # Run blocking yt-dlp download in a thread to avoid freezing the event loop.
            local_path = await asyncio.to_thread(download_youtube_video, task.video_id)

            # Determine file size after successful download.
            file_path = Path(local_path)
            file_size = file_path.stat().st_size if file_path.exists() else 0

            task.status = DownloadStatus.COMPLETED
            task.local_path = local_path
            task.file_size = file_size
            await db.commit()

        except Exception as exc:
            logger.exception("run_download_task failed: task_id=%d", task_id)
            # Re-fetch the task inside a fresh transaction so we can record the
            # failure even if the current transaction is broken.
            try:
                async with AsyncSessionLocal() as db2:
                    stmt = select(DownloadTask).where(
                        DownloadTask.id == task_id,
                        DownloadTask.user_id == user_id,
                    )
                    result2 = await db2.execute(stmt)
                    task2 = result2.scalar_one_or_none()
                    if task2 is not None:
                        task2.status = DownloadStatus.FAILED
                        task2.error_message = f"下载失败: {type(exc).__name__}"
                        await db2.commit()
            except Exception:
                logger.exception(
                    "Failed to record error status for DownloadTask id=%d",
                    task_id,
                )
