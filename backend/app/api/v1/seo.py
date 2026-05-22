"""SEO 评分 + 热门趋势 API。"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBSessionDep, GuestInfoDep, OptionalUserDep
from app.core.config import get_settings
from app.models.seo_score import SeoScoreRecord
from app.models.library import ModelLibrary
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
from app.services.guest_service import reserve_guest_quota, consume_guest_quota, set_guest_cookie
from app.services.seo_scoring_service import calculate_seo_score
from app.services.trend_discovery_service import fetch_trending
from app.services.trend_cache_service import get_cached_trend, get_saved_trend, save_trend_cache, add_trend_history, list_trend_history
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
    current_user: OptionalUserDep,
    guest_info: GuestInfoDep,
    response: Response,
) -> SeoScoringResponse:
    """
    对视频标题/描述/标签/缩略图进行 SEO 质量评分（0-100）。
    支持游客访问（受限配额），已登录用户使用组织级配置。

    评分维度（各 25 分）：
    - 标题：规则评分 + AI 竞品对标加分
    - 描述：规则评分 + AI 竞品对标加分
    - 标签：规则评分 + AI 竞品对标加分
    - 缩略图：规则评分 + AI 竞品对标加分

    如提供 model_library_id，将调用 AI 进行竞品对标分析。
    如配置了 YouTube API Key，将获取竞品视频数据。
    评分结果自动保存（仅已登录用户），可通过历史接口查看趋势。
    """
    # 游客配额预留检查（不扣减，仅检查是否充足）
    if not current_user:
        guest_id = guest_info.guest_id
        set_guest_cookie(response, guest_id)
        allowed, used, limit = await reserve_guest_quota(db, guest_id, "youtube_api")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="游客配额已用完，请登录以获取更多配额",
            )

    # 解析集成配置：游客使用默认组织的设置中心配置。
    org_id = current_user.org_id if current_user else get_settings().guest_default_org_id
    icfg = await resolve_integration_config(db, org_id=org_id)
    youtube_api_key = icfg.youtube_api_key or None

    # 未配置 YouTube API Key 时返回 503，避免配额先扣后失败
    if not youtube_api_key and (body.target_keyword or body.title):
        if current_user:
            detail = "未配置 YouTube API Key，请在设置中心配置"
        else:
            detail = "服务暂不可用，请稍后重试"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    # 解析模型配置（用于 AI 竞品分析，仅已登录用户可用）
    model_library = None
    if current_user and body.model_library_id:
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

    # API 调用成功后，实际扣减游客配额
    if not current_user:
        await consume_guest_quota(db, guest_info.guest_id, "youtube_api")

    # 记录 YouTube API 配额消耗（search.list 1次 + videos.list 1次）
    if youtube_api_key and (body.target_keyword or body.title):
        await record_api_quota_usage(db, "search", times=1, part_count=1)
        await record_api_quota_usage(db, "videos", times=1, part_count=1)

    # 保存评分记录（仅已登录用户）
    record_id = 0
    if current_user:
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
        record_id = record.id

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
        record_id=record_id,
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


# ── SEO 评分历史（仅已登录用户） ──


@router.get(
    "/seo-score/history",
    response_model=SeoScoreHistoryResponse,
    summary="SEO 评分历史记录（需登录）",
)
async def seo_score_history(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> SeoScoreHistoryResponse:
    """获取当前用户的 SEO 评分历史记录，按时间倒序。仅已登录用户可用。"""
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
    summary="SEO 评分记录详情（需登录）",
)
async def seo_score_record_detail(
    record_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SeoScoreRecordDetail:
    """获取单条 SEO 评分记录的完整详情。仅已登录用户可用。"""
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
    summary="删除 SEO 评分记录（需登录）",
)
async def delete_seo_score_record(
    record_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """删除单条 SEO 评分记录。仅已登录用户可用。"""
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
    current_user: OptionalUserDep,
    guest_info: GuestInfoDep,
    response: Response,
) -> TrendDiscoveryResponse:
    """
    获取指定地区的 YouTube 热门趋势视频。
    支持游客访问（受限配额），已登录用户使用组织级配置。
    相同地区+品类+1小时内复用缓存，不重复调用 YouTube API。

    配额策略：先 reserve 检查 -> 调用 API -> 成功后 consume 扣减，失败不扣减。
    """
    # 游客配额预留检查（不扣减，仅检查是否充足）
    if not current_user:
        guest_id = guest_info.guest_id
        set_guest_cookie(response, guest_id)
        allowed, used, limit = await reserve_guest_quota(db, guest_id, "youtube_api")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="游客配额已用完，请登录以获取更多配额",
            )

    category_id = body.category_id or ""

    # 检查缓存
    cached = await get_cached_trend(db, region=body.region, category_id=category_id)
    if cached is not None:
        # 游客一天只能使用一次 YouTube 相关功能；即使命中缓存，也计为一次功能调用。
        if not current_user:
            await consume_guest_quota(db, guest_info.guest_id, "youtube_api")
        # 缓存命中，仅已登录用户记录历史
        if current_user:
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

    # 解析集成配置：游客使用默认组织的设置中心配置。
    org_id = current_user.org_id if current_user else get_settings().guest_default_org_id
    icfg = await resolve_integration_config(db, org_id=org_id)
    if not icfg.youtube_api_key:
        # 区分游客和管理员的错误提示
        if current_user:
            detail = "未配置 YouTube API Key，请在设置中心配置"
        else:
            detail = "服务暂不可用，请稍后重试"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    result = await fetch_trending(
        youtube_api_key=icfg.youtube_api_key,
        region=body.region,
        category_id=body.category_id,
        max_results=body.max_results,
    )

    # API 调用成功后，实际扣减游客配额
    if not current_user:
        await consume_guest_quota(db, guest_info.guest_id, "youtube_api")

    # 记录配额消耗
    await record_api_quota_usage(db, "videos", times=1, part_count=3)
    await record_api_quota_usage(db, "channels", times=result.get("channels_list_calls", 1), part_count=2)

    # 保存缓存
    await save_trend_cache(db, region=body.region, category_id=category_id, data=result)

    # 已登录用户记录历史
    if current_user:
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


# ── 趋势缓存回溯 ──


@router.get(
    "/trend-cache",
    response_model=TrendDiscoveryResponse,
    summary="获取已缓存的趋势数据（历史回溯，不检查 TTL）",
)
async def get_trend_cache_endpoint(
    db: DBSessionDep,
    current_user: OptionalUserDep,
    region: str = Query(..., max_length=5, description="地区代码，如 US/GB/JP/KR"),
    category_id: str = Query("", max_length=20, description="YouTube 品类 ID（空字符串表示全部品类）"),
    cache_date: str | None = Query(None, description="缓存日期 YYYY-MM-DD，不传则查当天"),
) -> TrendDiscoveryResponse:
    """
    获取已缓存的趋势数据，不检查 TTL。
    支持游客访问（只读缓存，无配额消耗）。
    适用于历史记录回溯场景，避免因缓存过期而重复调用 YouTube API。
    如果没有对应缓存记录则返回 404。
    """
    parsed_date = None
    if cache_date:
        try:
            parsed_date = datetime.strptime(cache_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cache_date 格式错误，应为 YYYY-MM-DD",
            )
    data = await get_saved_trend(db, region=region, category_id=category_id, cache_date=parsed_date)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该趋势数据尚未缓存，请先执行获取趋势查询",
        )
    return TrendDiscoveryResponse(**data)


# ── 趋势历史（仅已登录用户） ──


@router.get(
    "/trend-history",
    response_model=TrendHistoryListResponse,
    summary="趋势查阅历史（需登录）",
)
async def trend_history_list(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=50, description="返回条数"),
) -> TrendHistoryListResponse:
    """获取当前用户最近的趋势查阅历史。仅已登录用户可用，游客无历史记录。"""
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
