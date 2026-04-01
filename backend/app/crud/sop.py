from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sop import SopAsset, SopMedia, SopScript, SopSegment, SopShot


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def list_sop_scripts(session: AsyncSession, user_id: int) -> list[SopScript]:
    q = select(SopScript).where(SopScript.user_id == user_id, SopScript.is_deleted.is_(False)).order_by(SopScript.id.desc())
    res = await session.execute(q)
    return list(res.scalars().all())


async def get_sop_script(session: AsyncSession, user_id: int, script_id: int) -> SopScript | None:
    q = select(SopScript).where(
        SopScript.id == script_id,
        SopScript.user_id == user_id,
        SopScript.is_deleted.is_(False),
    )
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def create_sop_script(session: AsyncSession, user_id: int, payload: dict) -> SopScript:
    row = SopScript(user_id=user_id, **payload)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_sop_script(session: AsyncSession, row: SopScript, payload: dict) -> SopScript:
    for k, v in payload.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return row


async def soft_delete_sop_script(session: AsyncSession, row: SopScript) -> None:
    row.is_deleted = True
    row.deleted_at = _utcnow()
    await session.commit()


async def list_sop_segments(session: AsyncSession, user_id: int, script_id: int | None = None) -> list[SopSegment]:
    q = (
        select(SopSegment)
        .join(SopScript, SopSegment.script_id == SopScript.id)
        .where(SopScript.user_id == user_id, SopSegment.is_deleted.is_(False), SopScript.is_deleted.is_(False))
        .order_by(SopSegment.id.desc())
    )
    if script_id is not None:
        q = q.where(SopSegment.script_id == script_id)
    res = await session.execute(q)
    return list(res.scalars().all())


async def get_sop_segment(session: AsyncSession, user_id: int, segment_id: int) -> SopSegment | None:
    q = (
        select(SopSegment)
        .join(SopScript, SopSegment.script_id == SopScript.id)
        .where(
            SopSegment.id == segment_id,
            SopScript.user_id == user_id,
            SopSegment.is_deleted.is_(False),
            SopScript.is_deleted.is_(False),
        )
    )
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def create_sop_segment(session: AsyncSession, payload: dict) -> SopSegment:
    row = SopSegment(**payload)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_sop_segment(session: AsyncSession, row: SopSegment, payload: dict) -> SopSegment:
    for k, v in payload.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return row


async def soft_delete_sop_segment(session: AsyncSession, row: SopSegment) -> None:
    row.is_deleted = True
    row.deleted_at = _utcnow()
    await session.commit()


async def list_sop_shots(session: AsyncSession, user_id: int, segment_id: int | None = None) -> list[SopShot]:
    q = (
        select(SopShot)
        .join(SopSegment, SopShot.segment_id == SopSegment.id)
        .join(SopScript, SopSegment.script_id == SopScript.id)
        .where(
            SopScript.user_id == user_id,
            SopShot.is_deleted.is_(False),
            SopSegment.is_deleted.is_(False),
            SopScript.is_deleted.is_(False),
        )
        .order_by(SopShot.id.desc())
    )
    if segment_id is not None:
        q = q.where(SopShot.segment_id == segment_id)
    res = await session.execute(q)
    return list(res.scalars().all())


async def get_sop_shot(session: AsyncSession, user_id: int, shot_id: int) -> SopShot | None:
    q = (
        select(SopShot)
        .join(SopSegment, SopShot.segment_id == SopSegment.id)
        .join(SopScript, SopSegment.script_id == SopScript.id)
        .where(
            SopShot.id == shot_id,
            SopScript.user_id == user_id,
            SopShot.is_deleted.is_(False),
            SopSegment.is_deleted.is_(False),
            SopScript.is_deleted.is_(False),
        )
    )
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def create_sop_shot(session: AsyncSession, payload: dict) -> SopShot:
    row = SopShot(**payload)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_sop_shot(session: AsyncSession, row: SopShot, payload: dict) -> SopShot:
    for k, v in payload.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return row


async def soft_delete_sop_shot(session: AsyncSession, row: SopShot) -> None:
    row.is_deleted = True
    row.deleted_at = _utcnow()
    await session.commit()


async def list_sop_assets(session: AsyncSession, user_id: int, shot_id: int | None = None) -> list[SopAsset]:
    q = (
        select(SopAsset)
        .join(SopShot, SopAsset.shot_id == SopShot.id)
        .join(SopSegment, SopShot.segment_id == SopSegment.id)
        .join(SopScript, SopSegment.script_id == SopScript.id)
        .where(
            SopScript.user_id == user_id,
            SopAsset.is_deleted.is_(False),
            SopShot.is_deleted.is_(False),
            SopSegment.is_deleted.is_(False),
            SopScript.is_deleted.is_(False),
        )
        .order_by(SopAsset.id.desc())
    )
    if shot_id is not None:
        q = q.where(SopAsset.shot_id == shot_id)
    res = await session.execute(q)
    return list(res.scalars().all())


async def get_sop_asset(session: AsyncSession, user_id: int, asset_id: int) -> SopAsset | None:
    q = (
        select(SopAsset)
        .join(SopShot, SopAsset.shot_id == SopShot.id)
        .join(SopSegment, SopShot.segment_id == SopSegment.id)
        .join(SopScript, SopSegment.script_id == SopScript.id)
        .where(
            SopAsset.id == asset_id,
            SopScript.user_id == user_id,
            SopAsset.is_deleted.is_(False),
            SopShot.is_deleted.is_(False),
            SopSegment.is_deleted.is_(False),
            SopScript.is_deleted.is_(False),
        )
    )
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def create_sop_asset(session: AsyncSession, payload: dict) -> SopAsset:
    source_asset_id = payload.get("source_asset_id")
    if source_asset_id:
        source = await session.get(SopAsset, source_asset_id)
        if source and not payload.get("file_url"):
            payload["file_url"] = source.file_url
        if source and not payload.get("prompt_text"):
            payload["prompt_text"] = source.prompt_text
        if source and not payload.get("asset_type"):
            payload["asset_type"] = source.asset_type
        if source and not payload.get("name"):
            payload["name"] = source.name
    row = SopAsset(**payload)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_sop_asset(session: AsyncSession, row: SopAsset, payload: dict) -> SopAsset:
    for k, v in payload.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return row


async def soft_delete_sop_asset(session: AsyncSession, row: SopAsset) -> None:
    row.is_deleted = True
    row.deleted_at = _utcnow()
    await session.commit()


async def list_sop_media(session: AsyncSession, user_id: int, shot_id: int | None = None) -> list[SopMedia]:
    q = (
        select(SopMedia)
        .join(SopShot, SopMedia.shot_id == SopShot.id)
        .join(SopSegment, SopShot.segment_id == SopSegment.id)
        .join(SopScript, SopSegment.script_id == SopScript.id)
        .where(
            SopScript.user_id == user_id,
            SopMedia.is_deleted.is_(False),
            SopShot.is_deleted.is_(False),
            SopSegment.is_deleted.is_(False),
            SopScript.is_deleted.is_(False),
        )
        .order_by(SopMedia.id.desc())
    )
    if shot_id is not None:
        q = q.where(SopMedia.shot_id == shot_id)
    res = await session.execute(q)
    return list(res.scalars().all())


async def get_sop_media(session: AsyncSession, user_id: int, media_id: int) -> SopMedia | None:
    q = (
        select(SopMedia)
        .join(SopShot, SopMedia.shot_id == SopShot.id)
        .join(SopSegment, SopShot.segment_id == SopSegment.id)
        .join(SopScript, SopSegment.script_id == SopScript.id)
        .where(
            SopMedia.id == media_id,
            SopScript.user_id == user_id,
            SopMedia.is_deleted.is_(False),
            SopShot.is_deleted.is_(False),
            SopSegment.is_deleted.is_(False),
            SopScript.is_deleted.is_(False),
        )
    )
    res = await session.execute(q)
    return res.scalar_one_or_none()


async def create_sop_media(session: AsyncSession, payload: dict) -> SopMedia:
    row = SopMedia(**payload)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_sop_media(session: AsyncSession, row: SopMedia, payload: dict) -> SopMedia:
    for k, v in payload.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return row


async def soft_delete_sop_media(session: AsyncSession, row: SopMedia) -> None:
    row.is_deleted = True
    row.deleted_at = _utcnow()
    await session.commit()
