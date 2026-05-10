from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video_project import VideoProject


async def list_video_projects(session: AsyncSession, user_id: int) -> list[VideoProject]:
    result = await session.execute(
        select(VideoProject)
        .where(VideoProject.user_id == user_id)
        .order_by(VideoProject.status.asc(), VideoProject.order_index.asc(), VideoProject.id.asc())
    )
    return list(result.scalars().all())


async def get_video_project(session: AsyncSession, user_id: int, project_id: int) -> VideoProject | None:
    result = await session.execute(
        select(VideoProject).where(VideoProject.id == project_id, VideoProject.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_video_project(
    session: AsyncSession,
    *,
    user_id: int,
    title: str,
    status: str,
    script_id: int | None,
    due_date,
) -> VideoProject:
    max_order_result = await session.execute(
        select(func.coalesce(func.max(VideoProject.order_index), -1)).where(
            VideoProject.user_id == user_id, VideoProject.status == status
        )
    )
    max_order = int(max_order_result.scalar_one())
    row = VideoProject(
        user_id=user_id,
        title=title,
        status=status,
        script_id=script_id,
        due_date=due_date,
        order_index=max_order + 1,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_video_project(session: AsyncSession, row: VideoProject, payload: dict) -> VideoProject:
    for k, v in payload.items():
        setattr(row, k, v)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_video_project(session: AsyncSession, row: VideoProject) -> None:
    await session.delete(row)
    await session.commit()


async def reorder_video_projects(
    session: AsyncSession,
    *,
    user_id: int,
    items: list[tuple[int, str, int]],
) -> None:
    if not items:
        return
    ids = [x[0] for x in items]
    result = await session.execute(
        select(VideoProject).where(VideoProject.user_id == user_id, VideoProject.id.in_(ids))
    )
    rows = {row.id: row for row in result.scalars().all()}
    for project_id, status, order_index in items:
        row = rows.get(project_id)
        if row is None:
            continue
        row.status = status
        row.order_index = order_index
    await session.commit()

