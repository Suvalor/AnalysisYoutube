"""关键词搜索历史 CRUD 操作。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword_history import KeywordHistory


async def create_keyword_history(
    session: AsyncSession,
    *,
    user_id: int,
    keyword: str,
    region: str = "US",
    language: str = "zh",
    search_volume: int | None = None,
    competition: float | None = None,
) -> KeywordHistory:
    """创建一条关键词搜索历史记录。"""
    record = KeywordHistory(
        user_id=user_id,
        keyword=keyword,
        region=region,
        language=language,
        search_volume=search_volume,
        competition=competition,
    )
    session.add(record)
    await session.flush()
    return record


async def list_keyword_history_by_user(
    session: AsyncSession,
    *,
    user_id: int,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[KeywordHistory], int]:
    """分页查询指定用户的关键词搜索历史，按创建时间降序。返回 (记录列表, 总数)。"""
    # 总数
    count_stmt = select(func.count()).select_from(KeywordHistory).where(
        KeywordHistory.user_id == user_id,
    )
    total = (await session.execute(count_stmt)).scalar() or 0

    # 分页查询
    stmt = (
        select(KeywordHistory)
        .where(KeywordHistory.user_id == user_id)
        .order_by(KeywordHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return rows, total
