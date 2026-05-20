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
    """按 org_id 分页查询飞书文档列表，支持标题模糊搜索。"""
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
    user_id: int | None = None,
    title: str,
    url: str,
) -> FeishuDoc:
    """创建飞书文档记录，写入 org_id 和 user_id。"""
    row = FeishuDoc(org_id=org_id, user_id=user_id, title=title, url=url)
    session.add(row)
    await session.flush()
    return row


async def get_feishu_doc(
    session: AsyncSession,
    *,
    org_id: int,
    doc_id: int,
) -> FeishuDoc | None:
    """按 org_id + doc_id 查询单个飞书文档。"""
    stmt = select(FeishuDoc).where(FeishuDoc.org_id == org_id, FeishuDoc.id == doc_id)
    return (await session.execute(stmt)).scalar_one_or_none()


def check_doc_ownership(doc: FeishuDoc, user_id: int) -> bool:
    """检查用户是否有权操作该文档：user_id 为 None（历史数据）或与当前用户一致时允许。"""
    if doc.user_id is None:
        return True
    return doc.user_id == user_id

