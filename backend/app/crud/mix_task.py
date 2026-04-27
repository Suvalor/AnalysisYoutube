from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mix_task import MixTask, MixTaskStatus


async def create_mix_task(
    db: AsyncSession,
    *,
    user_id: int,
    source_video_ids: list[int],
    audio_source_type: str,
    audio_source_ref: str,
    aspect_ratio: str,
    use_highlights: bool = True,
) -> MixTask:
    row = MixTask(
        user_id=user_id,
        source_video_ids=source_video_ids,
        audio_source_type=audio_source_type,
        audio_source_ref=audio_source_ref,
        aspect_ratio=aspect_ratio,
        use_highlights=use_highlights,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_mix_task(db: AsyncSession, user_id: int, task_id: int) -> MixTask | None:
    result = await db.execute(
        select(MixTask).where(MixTask.id == task_id, MixTask.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_mix_tasks(
    db: AsyncSession,
    user_id: int,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[MixTask], int]:
    base = select(MixTask).where(MixTask.user_id == user_id)
    count_q = select(func.count()).select_from(MixTask).where(MixTask.user_id == user_id)
    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(base.order_by(MixTask.id.desc()).offset(offset).limit(limit))).scalars().all()
    return rows, total


async def update_mix_task_status(
    db: AsyncSession,
    task: MixTask,
    status: MixTaskStatus,
    output_path: str = "",
    error_message: str = "",
) -> MixTask:
    task.status = status
    if output_path:
        task.output_path = output_path
    if error_message:
        task.error_message = error_message
    await db.commit()
    await db.refresh(task)
    return task
