"""SEO 评分 + 热门趋势 API。"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.models.seo_score import SeoScoreRecord
from app.models.library import ModelLibrary
from app.models.trend_cache import TrendHistory
from app.crud.library import get_by_user
from app.schemas.seo_scoring import (
    SeoScoringRequest,
    SeoScoringResponse,
    SeoScoreHistoryResponse,
    SeoScoreRecordDetail,
    AiBenchmarkResult,
    CompetitorSummaryItem,
    ScoreBreakdown,
)
from app.schemas.trend_discovery import TrendDiscoveryRequest, TrendDiscoveryResponse
from app.schemas.trend_cache import TrendHistoryItem, TrendHistoryListResponse
from app.services.config_manager import resolve_integration_config
from app.services.seo_scoring_service import calculate_seo_score
from app.services.trend_discovery_service import fetch_trending
from app.services.trend_cache_service import get_cached_trend, save_trend_cache, add_trend_history, list_trend_history
from app.services.quota_service import record_api_quota_usage

router = APIRouter()


# ── SEO 评分 ──


@router.post(
    "/seo-score",
    response_model=SeoScoringResponse,
    summary="视频 SEO 评分（AI + YouTube API 竞品对标）",
)
async def seo_scoring_endpoint(
    body: SeoScoringRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SeoScoringResponse:
    """
    对视频标题/描述/标签/缩略图进行 SEO 质量评分（0-100）。

    评分维度（各 25 分）：
    - 标题：规则评分 + AI 竞品对标加分
    - 描述：规则评分 + AI 竞品对标加分
    - 标签：规则评分 + AI 竞品对标加分
    - 缩略图：规则评分 + AI 竞品对标加分

    如提供 model_library_id，将调用 AI 进行竞品对标分析。
    如配置了 YouTube API Key，将获取竞品视频数据。
    评分结果自动保存，可通过历史接口查看趋势。
    """
    # 解析集成配置
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    youtube_api_key = icfg.youtube_api_key or None

    # 解析模型配置（用于 AI 竞品分析）
    model_library = None
    if body.model_library_id:
        model_library = await get_by_user(db, ModelLibrary, current_user.id, body.model_library_id)

    # 执行评分
    result = await calculate_seo_score(
        title=body.title,
        description=body.description,
        tags=body.tags,
        thumbnail_url=body.thumbnail_url,
        target_keyword=body.target_keyword,
        youtube_api_key=youtube_api_key,
        model_library=model_library,
    )

    # 记录 YouTube API 配额消耗（search.list 1次 + videos.list 1次）
    if youtube_api_key and (body.target_keyword or body.title):
        await record_api_quota_usage(db, "search", times=1, part_count=1)
        await record_api_quota_usage(db, "videos", times=1, part_count=1)

    # 保存评分记录
    record = SeoScoreRecord(
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        tags=body.tags,
        thumbnail_url=body.thumbnail_url,
        target_keyword=body.target_keyword,
        total_score=result["total_score"],
        title_score=result["title_score"],
        description_score=result["description_score"],
        tags_score=result["tags_score"],
        thumbnail_score=result["thumbnail_score"],
        suggestions=result.get("suggestions", []),
        ai_benchmark=result.get("ai_benchmark"),
        competitor_summary=result.get("competitor_summary"),
        score_breakdown=result.get("score_breakdown"),
        model_library_id=body.model_library_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # 构建响应
    ai_benchmark = None
    if result.get("ai_benchmark"):
        ab = result["ai_benchmark"]
        ai_benchmark = AiBenchmarkResult(
            title_benchmark=ab.get("title_benchmark", ""),
            description_benchmark=ab.get("description_benchmark", ""),
            tags_benchmark=ab.get("tags_benchmark", ""),
            thumbnail_benchmark=ab.get("thumbnail_benchmark", ""),
        )

    competitor_summary = None
    if result.get("competitor_summary"):
        competitor_summary = [
            CompetitorSummaryItem(title=c.get("title", ""), channel_title=c.get("channel_title", ""))
            for c in result["competitor_summary"]
        ]

    score_breakdown = None
    if result.get("score_breakdown"):
        sb = result["score_breakdown"]
        score_breakdown = ScoreBreakdown(**sb)

    return SeoScoringResponse(
        record_id=record.id,
        total_score=result["total_score"],
        title_score=result["title_score"],
        title_max=result["title_max"],
        description_score=result["description_score"],
        description_max=result["description_max"],
        tags_score=result["tags_score"],
        tags_max=result["tags_max"],
        thumbnail_score=result["thumbnail_score"],
        thumbnail_max=result["thumbnail_max"],
        suggestions=result.get("suggestions", []),
        ai_benchmark=ai_benchmark,
        competitor_summary=competitor_summary or [],
        score_breakdown=score_breakdown,
    )


# ── SEO 评分历史 ──


@router.get(
    "/seo-score/history",
    response_model=SeoScoreHistoryResponse,
    summary="SEO 评分历史记录",
)
async def seo_score_history(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> SeoScoreHistoryResponse:
    """获取当前用户的 SEO 评分历史记录，按时间倒序。"""
    # 总数
    count_q = select(func.count()).select_from(SeoScoreRecord).where(
        SeoScoreRecord.user_id == current_user.id
    )
    total = (await db.execute(count_q)).scalar() or 0

    # 分页查询
    q = (
        select(SeoScoreRecord)
        .where(SeoScoreRecord.user_id == current_user.id)
        .order_by(SeoScoreRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    records = list((await db.execute(q)).scalars().all())

    return SeoScoreHistoryResponse(
        items=records,
        total=total,
    )


@router.get(
    "/seo-score/history/{record_id}",
    response_model=SeoScoreRecordDetail,
    summary="SEO 评分记录详情",
)
async def seo_score_record_detail(
    record_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SeoScoreRecordDetail:
    """获取单条 SEO 评分记录的完整详情。"""
    q = select(SeoScoreRecord).where(
        SeoScoreRecord.id == record_id,
        SeoScoreRecord.user_id == current_user.id,
    )
    record = (await db.execute(q)).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评分记录不存在")

    # 手动构建详情响应（ai_benchmark/competitor_summary/score_breakdown 是 JSON 字段）
    ai_benchmark = None
    if record.ai_benchmark:
        ai_benchmark = AiBenchmarkResult(**record.ai_benchmark)

    competitor_summary = None
    if record.competitor_summary:
        competitor_summary = [CompetitorSummaryItem(**c) for c in record.competitor_summary]

    score_breakdown = None
    if record.score_breakdown:
        score_breakdown = ScoreBreakdown(**record.score_breakdown)

    return SeoScoreRecordDetail(
        id=record.id,
        title=record.title,
        description=record.description,
        tags=record.tags,
        thumbnail_url=record.thumbnail_url,
        target_keyword=record.target_keyword,
        total_score=record.total_score,
        title_score=record.title_score,
        description_score=record.description_score,
        tags_score=record.tags_score,
        thumbnail_score=record.thumbnail_score,
        suggestions=record.suggestions,
        ai_benchmark=ai_benchmark,
        competitor_summary=competitor_summary,
        score_breakdown=score_breakdown,
        model_library_id=record.model_library_id,
        created_at=record.created_at,
    )


@router.delete(
    "/seo-score/history/{record_id}",
    summary="删除 SEO 评分记录",
)
async def delete_seo_score_record(
    record_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """删除单条 SEO 评分记录。"""
    q = select(SeoScoreRecord).where(
        SeoScoreRecord.id == record_id,
        SeoScoreRecord.user_id == current_user.id,
    )
    record = (await db.execute(q)).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评分记录不存在")

    await db.delete(record)
    await db.commit()
    return {"message": "删除成功"}


# ── 热门趋势 ──


@router.post(
    "/trending",
    response_model=TrendDiscoveryResponse,
    summary="热门趋势发现",
)
async def trend_discovery_endpoint(
    body: TrendDiscoveryRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> TrendDiscoveryResponse:
    """
    获取指定地区的 YouTube 热门趋势视频。
    相同地区+品类+1小时内复用缓存，不重复调用 YouTube API。
    """
    category_id = body.category_id or ""

    # 检查缓存
    cached = await get_cached_trend(db, region=body.region, category_id=category_id)
    if cached is not None:
        # 缓存命中，仅记录历史
        await add_trend_history(
            db,
            user_id=current_user.id,
            region=body.region,
            category_id=category_id,
            region_label=body.region_label,
            category_label=body.category_label,
        )
        await db.commit()
        return TrendDiscoveryResponse(**cached)

    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    if not icfg.youtube_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置 YouTube API Key，请在设置中心配置",
        )

    result = await fetch_trending(
        youtube_api_key=icfg.youtube_api_key,
        region=body.region,
        category_id=body.category_id,
        max_results=body.max_results,
    )

    # 记录配额消耗
    await record_api_quota_usage(db, "videos", times=1, part_count=3)
    await record_api_quota_usage(db, "channels", times=result.get("channels_list_calls", 1), part_count=2)

    # 保存缓存
    await save_trend_cache(db, region=body.region, category_id=category_id, data=result)

    # 记录历史
    await add_trend_history(
        db,
        user_id=current_user.id,
        region=body.region,
        category_id=category_id,
        region_label=body.region_label,
        category_label=body.category_label,
    )
    await db.commit()

    return TrendDiscoveryResponse(**result)


# ── 趋势历史 ──


@router.get(
    "/trend-history",
    response_model=TrendHistoryListResponse,
    summary="趋势查阅历史",
)
async def trend_history_list(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=50, description="返回条数"),
) -> TrendHistoryListResponse:
    """获取当前用户最近的趋势查阅历史。"""
    items = await list_trend_history(db, user_id=current_user.id, limit=limit)
    return TrendHistoryListResponse(
        items=[
            TrendHistoryItem(
                id=h.id,
                cache_date=h.cache_date.strftime("%Y/%m/%d"),
                region=h.region,
                category_id=h.category_id,
                region_label=h.region_label,
                category_label=h.category_label,
                created_at=h.created_at.isoformat(),
            )
            for h in items
        ],
        total=len(items),
    )
