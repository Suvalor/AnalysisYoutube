"""关键词研究 API 路由。"""

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUserDep, DBSessionDep, GuestInfoDep, OptionalUserDep
from app.crud.keyword_history import create_keyword_history, list_keyword_history_by_user
from app.schemas.keyword_history import KeywordHistoryItem, KeywordHistoryListResponse
from app.schemas.keyword_research import (
    KeywordResearchRequest,
    KeywordResearchResponse,
    RelatedKeywordItem,
    TopVideoItem,
    TrendDataPoint,
)
from app.services.keyword_research_service import research_keyword
from app.services.config_manager import resolve_integration_config
from app.services.guest_service import reserve_guest_quota, consume_guest_quota, set_guest_cookie
from app.services.quota_service import record_api_quota_usage

router = APIRouter()


@router.post(
    "/research",
    response_model=KeywordResearchResponse,
    summary="关键词研究",
)
async def keyword_research(
    body: KeywordResearchRequest,
    db: DBSessionDep,
    current_user: OptionalUserDep,
    guest_info: GuestInfoDep,
    response: Response,
) -> KeywordResearchResponse:
    """
    执行关键词研究，返回搜索量/竞争度/KD/机会得分/趋势等评分数据。
    支持游客访问（受限配额），已登录用户使用组织级配置。

    - 调用 YouTube Data API 获取搜索数据
    - 使用启发式评分算法计算各维度评分
    - 消耗约 3-4 次 search.list 配额（300-400 单位）

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

    # 解析集成配置（游客使用系统级 fallback）
    org_id = current_user.org_id if current_user else None
    icfg = await resolve_integration_config(db, org_id=org_id)

    # 检查 YouTube API Key 是否可用，不可用时返回 503
    if not icfg.youtube_api_key:
        if current_user:
            detail = "未配置 YouTube API Key，请在设置中心配置"
        else:
            detail = "服务暂不可用，请稍后重试"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    result = await research_keyword(
        keyword=body.keyword,
        region=body.region,
        language=body.language,
        youtube_api_key=icfg.youtube_api_key,
    )

    # API 调用成功后，实际扣减游客配额
    if not current_user:
        await consume_guest_quota(db, guest_info.guest_id, "youtube_api")

    # 记录 YouTube API 配额消耗
    search_calls = result.get("search_calls", 0)
    channels_calls = result.get("channels_calls", 0)
    videos_calls = result.get("videos_calls", 0)
    if search_calls > 0:
        await record_api_quota_usage(db, "search", times=search_calls, part_count=2)
    if channels_calls > 0:
        await record_api_quota_usage(db, "channels", times=channels_calls, part_count=2)
    if videos_calls > 0:
        await record_api_quota_usage(db, "videos", times=videos_calls, part_count=2)

    # 已登录用户：写入搜索历史
    if current_user:
        await create_keyword_history(
            db,
            user_id=current_user.id,
            keyword=body.keyword,
            region=body.region,
            language=body.language,
            search_volume=result.get("search_volume_score"),
            competition=result.get("competition_score"),
        )

    await db.commit()
    return KeywordResearchResponse(
        keyword=result["keyword"],
        region=result["region"],
        keyword_score=result["keyword_score"],
        search_volume_score=result["search_volume_score"],
        competition_score=result["competition_score"],
        keyword_difficulty=result["keyword_difficulty"],
        opportunity_score=result["opportunity_score"],
        trend_direction=result["trend_direction"],
        total_results=result["total_results"],
        related_keywords=result["related_keywords"],
        related_keywords_with_scores=[
            RelatedKeywordItem(**r) for r in result["related_keywords_with_scores"]
        ],
        trend_data=[TrendDataPoint(**t) for t in result["trend_data"]],
        top_videos=[TopVideoItem(**v) for v in result["top_videos"]],
        channel_count=result["channel_count"],
        avg_channel_subscribers=result["avg_channel_subscribers"],
        content_gap_ratio=result["content_gap_ratio"],
        search_calls=search_calls,
    )


@router.get(
    "/keyword-history",
    response_model=KeywordHistoryListResponse,
    summary="关键词研究历史（需登录）",
)
async def keyword_history(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=50, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> KeywordHistoryListResponse:
    """获取当前用户的关键词搜索历史，按时间倒序。仅已登录用户可用。"""
    rows, total = await list_keyword_history_by_user(
        db, user_id=current_user.id, limit=limit, offset=offset,
    )
    return KeywordHistoryListResponse(
        items=[
            KeywordHistoryItem(
                id=r.id,
                keyword=r.keyword,
                region=r.region,
                language=r.language,
                search_volume=r.search_volume,
                competition=r.competition,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
    )
