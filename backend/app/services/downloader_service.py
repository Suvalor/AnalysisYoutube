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

# error_message 字段为 String(500)，截断时保留尾部（最有价值的错误详情在尾部）
_ERROR_MESSAGE_MAX_LEN = 500

# 网络相关错误关键词，用于检测是否需要提示代理配置
# 注意：使用正则表达式模式，避免子串误匹配（如 "non-network error" 不应匹配 "network error"）
_NETWORK_ERROR_PATTERNS = (
    r"unable to download",
    r"unable to connect",
    r"connection refused",
    r"connection timed out",
    r"(?<!\-)network error",  # 排除 "non-network error"
    r"name or service not known",
    r"no route to host",
    r"could not resolve",
    r"errno\s+\d+",
    r"timed?\s*out",
    r"proxy\s+error",
    r"ssl\s*error",
    r"certif(icate|ication|icate)",
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _truncate_error_message(msg: str, max_len: int = _ERROR_MESSAGE_MAX_LEN) -> str:
    """截断错误消息到指定长度，保留尾部（最有价值的错误详情在尾部）。

    当 max_len 不足以容纳截断前缀时，直接保留消息尾部 max_len 个字符。
    当 max_len <= 0 时，返回空字符串。
    """
    if max_len <= 0:
        return ""
    if len(msg) <= max_len:
        return msg
    # 保留尾部，头部用省略标记
    prefix = "...[截断]"
    available = max_len - len(prefix)
    if available <= 0:
        return msg[-max_len:]
    return prefix + msg[-available:]


def _build_error_message(exc: Exception, video_id: str | None = None) -> str:
    """构建包含异常详情和代理提示的错误消息。

    根据异常类型和错误内容生成有意义的中文错误消息；
    如果检测到网络相关错误且未配置代理，追加 DOWNLOAD_PROXY 配置提示。
    """
    # 提取异常的完整信息
    exc_str = str(exc)
    exc_type = type(exc).__name__

    # 根据异常类型生成中文错误描述
    if isinstance(exc, yt_dlp.utils.DownloadError):
        detail = f"下载失败: {exc_str}"
    elif isinstance(exc, yt_dlp.utils.ExtractorError):
        detail = f"视频信息提取失败: {exc_str}"
    elif isinstance(exc, ConnectionError):
        detail = f"网络连接失败: {exc_str}"
    elif isinstance(exc, TimeoutError):
        detail = f"网络超时: {exc_str}"
    elif isinstance(exc, OSError) and "network" in exc_str.lower():
        detail = f"网络IO错误: {exc_str}"
    else:
        # 对于未匹配到特定类型的异常（包括 RuntimeError、ExtractorError 等），保留完整类型和消息信息
        detail = f"下载失败[{exc_type}]: {exc_str}"

    if video_id is not None:
        detail = f"video_id={video_id}: {detail}"

    # BUG-4: 检测网络相关错误，追加代理配置提示
    lower_detail = detail.lower()
    is_network_error = any(
        re.search(pattern, lower_detail) for pattern in _NETWORK_ERROR_PATTERNS
    )
    if is_network_error and not settings.download_proxy:
        proxy_hint = " (提示: 可能需要配置 DOWNLOAD_PROXY 环境变量以访问 YouTube)"
        detail = _truncate_error_message(detail + proxy_hint)
    else:
        detail = _truncate_error_message(detail)

    return detail


# ---------------------------------------------------------------------------
# Synchronous download
# ---------------------------------------------------------------------------


def download_youtube_video(
    video_id: str,
    progress_callback: Callable[[float, int], None] | None = None,
) -> tuple[str, str | None, str | None]:
    """Download a YouTube video by *video_id* and return the local file path.

    If the target file already exists and is non-empty the download is skipped
    and the existing path is returned immediately.

    Args:
        video_id: Valid YouTube video ID (11 chars).
        progress_callback: Optional callable receiving (progress_percentage, total_bytes).
            progress_percentage is 0-100; total_bytes is the estimated total file size
            (0 if unknown).

            .. versionchanged:: 2.0
               The second parameter ``total_bytes`` is newly added. Previously the
               callback signature was ``Callable[[float], None]``; it is now
               ``Callable[[float, int], None]``.

    Returns:
        Tuple of (local_file_path, video_title, thumbnail_url).
        video_title and thumbnail_url come from yt-dlp info_dict.

    Raises:
        ValueError: If video_id is not a valid YouTube video ID.
        RuntimeError: If yt-dlp reports a download error or network failure.
    """
    if not VIDEO_ID_RE.match(video_id):
        raise ValueError(f"Invalid video_id: {video_id!r}")

    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = RAW_MATERIALS_DIR / f"{video_id}.mp4"

    # Skip re-download when the file is already present and non-empty.
    if output_path.exists() and output_path.stat().st_size > 0:
        logger.info("视频已存在，跳过下载: %s", output_path)
        if progress_callback is not None:
            file_size = output_path.stat().st_size
            progress_callback(100.0, file_size)
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
        """yt-dlp progress hook that forwards percentage and total_bytes to the callback."""
        if progress_callback is None:
            return
        status = d.get("_status") or d.get("status")
        if status == "finished":
            # 下载完成时传递实际下载字节数
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            progress_callback(100.0, int(total_bytes))
            return
        if status != "downloading":
            return
        # 提取总字节数
        total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        total_bytes_int = int(total_bytes) if total_bytes else 0
        # Prefer the pre-formatted percent string from yt-dlp.
        percent_str = d.get("_percent_str")
        if percent_str is not None:
            try:
                progress_callback(float(str(percent_str).strip().replace("%", "")), total_bytes_int)
                return
            except (ValueError, TypeError):
                pass
        # Fallback: compute from byte counters.
        downloaded = d.get("downloaded_bytes") or 0
        total = total_bytes or 0
        if total and total > 0:
            progress_callback(min(float(downloaded) / float(total) * 100.0, 100.0), total_bytes_int)
        else:
            # 无法计算百分比时，仅传递 total_bytes（可能为 0）
            progress_callback(0.0, total_bytes_int)

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
        # BUG-3: 使用 _build_error_message 构建包含详情和代理提示的错误消息
        raise RuntimeError(_build_error_message(exc, video_id=video_id)) from exc
    except (ConnectionError, TimeoutError) as exc:
        # BUG-3: 捕获常见网络异常，提供有意义的中文错误消息
        raise RuntimeError(_build_error_message(exc, video_id=video_id)) from exc

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
    # Shared container for progress and file_size (written by the download thread,
    # read by the periodic flush coroutine).  Thread-safe via GIL for
    # simple float/int assignment.
    progress_container: dict[str, float | int] = {"value": 0.0, "total_bytes": 0}

    def _progress_cb(pct: float, total_bytes: int = 0) -> None:
        """进度回调：更新进度百分比和总字节数到共享容器。"""
        progress_container["value"] = pct
        if total_bytes > 0:
            progress_container["total_bytes"] = total_bytes

    async def _flush_progress() -> None:
        """定期将进度和文件大小写入数据库。"""
        while True:
            await asyncio.sleep(_PROGRESS_FLUSH_INTERVAL)
            current = progress_container["value"]
            current_total = progress_container["total_bytes"]
            try:
                async with AsyncSessionLocal() as flush_db:
                    stmt = select(DownloadTask).where(
                        DownloadTask.id == task_id,
                        DownloadTask.user_id == user_id,
                    )
                    result = await flush_db.execute(stmt)
                    t = result.scalar_one_or_none()
                    if t is not None:
                        # BUG-2: 同时更新 progress 和 file_size
                        needs_update = False
                        if t.progress != current:
                            t.progress = current
                            needs_update = True
                        # 下载过程中更新 file_size（total_bytes 为预估大小）
                        if current_total > 0 and t.file_size != current_total:
                            t.file_size = current_total
                            needs_update = True
                        if needs_update:
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
                        # download_youtube_video 内部已用 _build_error_message 处理，
                        # RuntimeError 的 str(exc) 已包含完整信息，此处仅截断避免二次包装
                        task2.error_message = _truncate_error_message(str(exc))
                        await db2.commit()
            except Exception:
                logger.exception(
                    "Failed to record error status for DownloadTask id=%d",
                    task_id,
                )
