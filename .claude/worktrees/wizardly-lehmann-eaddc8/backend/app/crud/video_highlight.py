from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video_highlight import VideoHighlight


async def create_highlight(
    db: AsyncSession,
    *,
    video_id: int,
    user_id: int,
    start_sec: float,
    end_sec: float,
    score: float = 0.5,
    label: str = "",
    source: str = "ai",
) -> VideoHighlight:
    row = VideoHighlight(
        video_id=video_id,
        user_id=user_id,
        start_sec=start_sec,
        end_sec=end_sec,
        score=score,
        label=label,
        source=source,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_highlights_by_video(
    db: AsyncSession,
    video_id: int,
    user_id: int,
) -> list[VideoHighlight]:
    result = await db.execute(
        select(VideoHighlight)
        .where(VideoHighlight.video_id == video_id, VideoHighlight.user_id == user_id)
        .order_by(VideoHighlight.start_sec)
    )
    return list(result.scalars().all())


async def delete_highlight(
    db: AsyncSession,
    video_id: int,
    user_id: int,
    highlight_id: int,
) -> bool:
    result = await db.execute(
        select(VideoHighlight).where(
            VideoHighlight.id == highlight_id,
            VideoHighlight.video_id == video_id,
            VideoHighlight.user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    return True


async def bulk_create_highlights(
    db: AsyncSession,
    *,
    video_id: int,
    user_id: int,
    highlights: list[dict],
    source: str = "ai",
) -> list[VideoHighlight]:
    # Dedup: skip highlights that overlap with existing ones (0.5s quantization tolerance)
    existing = await get_highlights_by_video(db, video_id, user_id)
    existing_keys = set()
    for ex in existing:
        # Quantize to 0.5s grid to handle float precision
        key = (round(ex.start_sec * 2) / 2, round(ex.end_sec * 2) / 2)
        existing_keys.add(key)

    rows = []
    for h in highlights:
        key = (round(h["start_sec"] * 2) / 2, round(h["end_sec"] * 2) / 2)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        row = VideoHighlight(
            video_id=video_id,
            user_id=user_id,
            start_sec=h["start_sec"],
            end_sec=h["end_sec"],
            score=h.get("score", 0.5),
            label=h.get("label", ""),
            source=source,
        )
        db.add(row)
        rows.append(row)
    if not rows:
        return []
    await db.commit()
    for row in rows:
        await db.refresh(row)
    return rows
