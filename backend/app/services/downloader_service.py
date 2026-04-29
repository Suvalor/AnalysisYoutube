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
from typing import Callable

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

# How often (in seconds) the background task flushes progress to DB.
_PROGRESS_FLUSH_INTERVAL = 3.0


# ---------------------------------------------------------------------------
# Synchronous download
# ---------------------------------------------------------------------------


def download_youtube_video(
    video_id: str,
    progress_callback: Callable[[float], None] | None = None,
) -> tuple[str, str | None, str | None]:
    """Download a YouTube video by *video_id* and return the local file path.

    If the target file already exists and is non-empty the download is skipped
    and the existing path is returned immediately.

    Args:
        video_id: Valid YouTube video ID (11 chars).
        progress_callback: Optional callable receiving progress percentage (0-100).

    Returns:
        Tuple of (local_file_path, video_title, thumbnail_url).
        video_title and thumbnail_url come from yt-dlp info_dict.

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
        if progress_callback is not None:
            progress_callback(100.0)
        # M-01: Still extract metadata even when skipping download, but with a
        # short timeout to avoid blocking the download thread on slow networks.
        try:
            info_opts: dict = {"quiet": True, "no_warnings": True, "noprogress": True, "socket_timeout": 5}
            if settings.download_proxy:
                info_opts["proxy"] = settings.download_proxy
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return (
                    str(output_path.resolve()),
                    info.get("title") if info else None,
                    info.get("thumbnail") if info else None,
                )
        except Exception:
            return str(output_path.resolve()), None, None

    def _progress_hook(d: dict[str, object]) -> None:
        """yt-dlp progress hook that forwards percentage to the callback."""
        if progress_callback is None:
            return
        status = d.get("_status") or d.get("status")
        if status == "finished":
            progress_callback(100.0)
            return
        if status != "downloading":
            return
        # Prefer the pre-formatted percent string from yt-dlp.
        percent_str = d.get("_percent_str")
        if percent_str is not None:
            try:
                progress_callback(float(str(percent_str).strip().replace("%", "")))
                return
            except (ValueError, TypeError):
                pass
        # Fallback: compute from byte counters.
        downloaded = d.get("downloaded_bytes") or 0
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        if total and total > 0:
            progress_callback(min(float(downloaded) / float(total) * 100.0, 100.0))

    ydl_opts: dict[str, object] = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4/best",
        "outtmpl": str(output_path),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [_progress_hook],
    }

    if settings.download_proxy:
        logger.info("Using download proxy: %s", settings.download_proxy)
        ydl_opts["proxy"] = settings.download_proxy

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get("title") if info else None
            thumbnail_url = info.get("thumbnail") if info else None
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(f"下载失败 video_id={video_id}: {exc}") from exc

    return str(output_path.resolve()), video_title, thumbnail_url


# ---------------------------------------------------------------------------
# Async background task
# ---------------------------------------------------------------------------


async def run_download_task(task_id: int, user_id: int) -> None:
    """Background task: download a video and update the DownloadTask row.

    Uses a **new** database session because FastAPI BackgroundTasks execute
    after the response has been sent, at which point the request-scoped
    session is already closed.
    """
    # Shared container for progress value (written by the download thread,
    # read by the periodic flush coroutine).  Thread-safe via GIL for
    # simple float assignment.
    progress_container: dict[str, float] = {"value": 0.0}

    def _progress_cb(pct: float) -> None:
        progress_container["value"] = pct

    async def _flush_progress() -> None:
        """Periodically write progress to the database."""
        while True:
            await asyncio.sleep(_PROGRESS_FLUSH_INTERVAL)
            current = progress_container["value"]
            try:
                async with AsyncSessionLocal() as flush_db:
                    stmt = select(DownloadTask).where(
                        DownloadTask.id == task_id,
                        DownloadTask.user_id == user_id,
                    )
                    result = await flush_db.execute(stmt)
                    t = result.scalar_one_or_none()
                    if t is not None and t.progress != current:
                        t.progress = current
                        await flush_db.commit()
            except Exception:
                logger.warning(
                    "Failed to flush progress for DownloadTask id=%d",
                    task_id,
                    exc_info=True,
                )

    async with AsyncSessionLocal() as db:
        flush_handle: asyncio.Task[None] | None = None
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
            task.progress = 0.0
            await db.commit()

            # Start the periodic progress flusher.
            flush_handle = asyncio.ensure_future(_flush_progress())

            # Run blocking yt-dlp download in a thread to avoid freezing the event loop.
            local_path, yt_title, yt_thumbnail = await asyncio.to_thread(
                download_youtube_video, task.video_id, _progress_cb,
            )

            # Stop the flusher and do a final progress update.
            flush_handle.cancel()
            try:
                await flush_handle
            except asyncio.CancelledError:
                pass

            # Determine file size after successful download.
            file_path = Path(local_path)
            file_size = file_path.stat().st_size if file_path.exists() else 0

            task.status = DownloadStatus.COMPLETED
            task.local_path = local_path
            task.file_size = file_size
            task.progress = 100.0
            # Save video metadata from yt-dlp if not already present.
            if yt_title and not task.video_title:
                task.video_title = yt_title
            if yt_thumbnail and not task.thumbnail_url:
                task.thumbnail_url = yt_thumbnail
            await db.commit()

        except Exception as exc:
            # Cancel the flusher on error path as well.
            if flush_handle is not None:
                flush_handle.cancel()
                try:
                    await flush_handle
                except asyncio.CancelledError:
                    pass

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
