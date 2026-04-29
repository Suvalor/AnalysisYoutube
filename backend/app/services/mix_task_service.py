"""Mix task orchestration service.

Handles the background execution of video mix tasks:
1. Resolve source video local paths from DownloadTask (with AssetLibrary fallback)
2. Resolve audio source (TTS or uploaded file)
3. Query highlights for each video (if use_highlights=True)
4. Call video_mixer_service.mix_videos()
5. Update MixTask status
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.mix_task import MixTask, MixTaskStatus
from app.crud.mix_task import get_mix_task, update_mix_task_status
from app.crud.video_highlight import get_highlights_by_video
from app.services.video_mixer_service import mix_videos

logger = logging.getLogger(__name__)

# Output directory for mixed videos
MIX_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "mixed"
MIX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Allowed base directories for resolved file paths (prevent path traversal)
_ALLOWED_DATA_DIRS: list[Path] = [
    (Path(__file__).resolve().parent.parent / "data"),
]
# Add common download directories
for _candidate in [Path("/data"), Path.home() / "data", Path.home() / "downloads"]:
    if _candidate.is_dir():
        _ALLOWED_DATA_DIRS.append(_candidate)


def _is_safe_path(path_str: str) -> bool:
    """Validate that a resolved path is within allowed directories and is a regular file."""
    try:
        resolved = Path(path_str).resolve()
    except (ValueError, OSError):
        return False
    if not resolved.is_file():
        return False
    for allowed in _ALLOWED_DATA_DIRS:
        try:
            resolved.relative_to(allowed)
            return True
        except ValueError:
            continue
    return False


async def _resolve_video_path(db: AsyncSession, user_id: int, vid_id: str) -> str | None:
    """Resolve a video ID to a local file path via DownloadTask."""
    from app.models.download_task import DownloadTask, DownloadStatus

    # First try: vid_id as YouTube video_id string
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.user_id == user_id,
            DownloadTask.video_id == vid_id,
            DownloadTask.status == DownloadStatus.COMPLETED,
        )
    )
    dt = result.scalar_one_or_none()
    if dt and dt.local_path and _is_safe_path(dt.local_path):
        return dt.local_path

    # Second try: vid_id as integer DownloadTask.id (if it's numeric)
    try:
        int_id = int(vid_id)
    except (ValueError, TypeError):
        pass
    else:
        result = await db.execute(
            select(DownloadTask).where(
                DownloadTask.id == int_id,
                DownloadTask.user_id == user_id,
                DownloadTask.status == DownloadStatus.COMPLETED,
            )
        )
        dt = result.scalar_one_or_none()
        if dt and dt.local_path and _is_safe_path(dt.local_path):
            return dt.local_path

    # Third try: check AssetLibrary if it exists
    try:
        from app.models.library import AssetLibrary
        result = await db.execute(
            select(AssetLibrary).where(
                AssetLibrary.id == vid_id,
                AssetLibrary.user_id == user_id,
            )
        )
        asset = result.scalar_one_or_none()
        if asset and asset.file_url and not asset.file_url.startswith(("http://", "https://")):
            if _is_safe_path(asset.file_url):
                return asset.file_url
    except ImportError:
        pass

    return None


async def _resolve_audio(db: AsyncSession, user_id: int, task: MixTask) -> str | None:
    """Resolve audio source to a local file path."""
    if task.audio_source_type == "none":
        # No audio source specified — generate silent audio via ffmpeg
        import subprocess
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=str(MIX_OUTPUT_DIR))
        tmp.close()
        try:
            subprocess.run(
                ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                 "-t", "30", "-q:a", "9", "-acodec", "libmp3lame",
                 tmp.name, "-y"],
                capture_output=True, check=True, timeout=30,
            )
            return tmp.name
        except Exception as exc:
            logger.warning("Failed to create silent audio: %s", exc)
            Path(tmp.name).unlink(missing_ok=True)
            return None

    if task.audio_source_type == "file" and task.audio_source_ref:
        try:
            audio_id = int(task.audio_source_ref)
        except (ValueError, TypeError):
            return None
        return await _resolve_video_path(db, user_id, audio_id)

    if task.audio_source_type == "tts" and task.audio_source_ref:
        # TTS placeholder: generate silent audio via ffmpeg
        import subprocess
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=str(MIX_OUTPUT_DIR))
        tmp.close()
        try:
            subprocess.run(
                ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                 "-t", "30", "-q:a", "9", "-acodec", "libmp3lame",
                 tmp.name, "-y"],
                capture_output=True, check=True, timeout=30,
            )
            return tmp.name
        except Exception as exc:
            logger.warning("Failed to create placeholder audio: %s", exc)
            Path(tmp.name).unlink(missing_ok=True)
            return None

    return None


async def _resolve_highlights(
    db: AsyncSession,
    user_id: int,
    task: MixTask,
    source_paths: list[str],
) -> dict[str, list[tuple[float, float]]] | None:
    """Resolve highlight segments for each source video."""
    if not task.use_highlights or not task.source_video_ids:
        return None

    from app.models.youtube import YouTubeVideo
    from app.models.download_task import DownloadTask, DownloadStatus

    highlights: dict[str, list[tuple[float, float]]] = {}

    for path in source_paths:
        path_hls: list[tuple[float, float]] = []
        result = await db.execute(
            select(DownloadTask).where(
                DownloadTask.user_id == user_id,
                DownloadTask.status == DownloadStatus.COMPLETED,
                DownloadTask.local_path == path,
            )
        )
        dt = result.scalar_one_or_none()
        if dt is None:
            continue

        yt_result = await db.execute(
            select(YouTubeVideo).where(YouTubeVideo.yt_video_id == dt.video_id)
        )
        yt_video = yt_result.scalar_one_or_none()
        if yt_video is None:
            continue

        hl_rows = await get_highlights_by_video(db, yt_video.id, user_id)
        for hl in hl_rows:
            path_hls.append((hl.start_sec, hl.end_sec))

        if path_hls:
            highlights[path] = path_hls

    return highlights if highlights else None


async def run_mix_task(task_id: int, user_id: int) -> None:
    """Background task: execute a video mix operation."""
    async with AsyncSessionLocal() as db:
        try:
            task = await get_mix_task(db, user_id, task_id)
            if task is None:
                logger.warning("MixTask not found: id=%d user_id=%d", task_id, user_id)
                return

            await update_mix_task_status(db, task, MixTaskStatus.PROCESSING)

            # Step 1: Resolve source video paths from DownloadTask
            source_paths: list[str] = []
            if task.source_video_ids:
                for vid_id in task.source_video_ids:
                    local_path = await _resolve_video_path(db, user_id, vid_id)
                    if local_path:
                        source_paths.append(local_path)
                    else:
                        logger.warning("No local file for video_id=%s, skipping", vid_id)

            if not source_paths:
                await update_mix_task_status(
                    db, task, MixTaskStatus.FAILED,
                    error_message="没有可用的本地视频文件",
                )
                return

            # Step 2: Resolve audio source
            audio_path = await _resolve_audio(db, user_id, task)
            if not audio_path:
                await update_mix_task_status(
                    db, task, MixTaskStatus.FAILED,
                    error_message="音频文件不可用",
                )
                return

            # Step 3: Resolve highlights
            highlights = await _resolve_highlights(db, user_id, task, source_paths)

            # Step 4: Determine output dimensions and run mix
            target_w = 1080 if task.aspect_ratio == "9:16" else 1920
            target_h = 1920 if task.aspect_ratio == "9:16" else 1080
            output_path = str(MIX_OUTPUT_DIR / f"mix_{task_id}.mp4")

            result_path = await asyncio.to_thread(
                mix_videos,
                source_video_paths=source_paths,
                new_audio_path=audio_path,
                output_path=output_path,
                target_width=target_w,
                target_height=target_h,
                highlights=highlights,
            )

            # Clean up TTS temp audio file after mixing
            if audio_path and audio_path.startswith(str(MIX_OUTPUT_DIR)):
                Path(audio_path).unlink(missing_ok=True)

            await update_mix_task_status(db, task, MixTaskStatus.COMPLETED, output_path=result_path)
            logger.info("Mix task %d completed: %s", task_id, result_path)

        except Exception as exc:
            logger.exception("run_mix_task failed: task_id=%d", task_id)
            try:
                async with AsyncSessionLocal() as db2:
                    task2 = await get_mix_task(db2, user_id, task_id)
                    if task2 is not None:
                        await update_mix_task_status(
                            db2, task2, MixTaskStatus.FAILED,
                            error_message=f"混剪失败: {type(exc).__name__}",
                        )
            except Exception:
                logger.exception("Failed to record error for MixTask id=%d", task_id)
