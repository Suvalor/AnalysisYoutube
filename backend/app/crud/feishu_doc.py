from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feishu_doc import FeishuDoc


async def list_feishu_docs(
    session: AsyncSession,
    *,
    org_id: int,
    page: int,
    page_size: int,
    search: str | None,
) -> tuple[list[FeishuDoc], int]:
    cond = [FeishuDoc.org_id == org_id]
    s = (search or "").strip()
    if s:
        cond.append(FeishuDoc.title.contains(s))

    count_stmt = select(func.count()).select_from(FeishuDoc).where(*cond)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)

    stmt = (
        select(FeishuDoc)
        .where(*cond)
        .order_by(desc(FeishuDoc.created_at), desc(FeishuDoc.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


async def create_feishu_doc(
    session: AsyncSession,
    *,
    org_id: int,
    title: str,
    url: str,
) -> FeishuDoc:
    row = FeishuDoc(org_id=org_id, title=title, url=url)
    session.add(row)
    await session.flush()
    return row


async def get_feishu_doc(
    session: AsyncSession,
    *,
    org_id: int,
    doc_id: int,
) -> FeishuDoc | None:
    stmt = select(FeishuDoc).where(FeishuDoc.org_id == org_id, FeishuDoc.id == doc_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def delete_feishu_doc(
    session: AsyncSession,
    *,
    org_id: int,
    doc_id: int,
) -> bool:
    row = await get_feishu_doc(session, org_id=org_id, doc_id=doc_id)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True

