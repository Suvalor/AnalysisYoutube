"""关键词研究 API 路由。"""

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import DBSessionDep, GuestInfoDep, OptionalUserDep
from app.models.user import UserRole
from app.schemas.keyword_research import (
    KeywordResearchRequest,
    KeywordResearchResponse,
    RelatedKeywordItem,
    TopVideoItem,
    TrendDataPoint,
)
from app.services.keyword_research_service import research_keyword
from app.services.config_manager import resolve_integration_config
from app.services.guest_service import set_guest_cookie
from app.services.quota_service import record_api_quota_usage
from app.services.rate_limit_service import check_quota, increment_usage

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
    """
    # 游客配额检查与计数
    if not current_user:
        role = UserRole.GUEST
        user_id = None
        guest_id = guest_info.guest_id
        subscription_quotas = None
        set_guest_cookie(response, guest_id)
        allowed, used, limit = await check_quota(
            db, user_id=user_id, role=role, guest_id=guest_id,
            api_type="youtube_api", subscription_quotas=subscription_quotas,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"配额已用尽：youtube_api 已用 {used}/{limit}，请升级套餐或明日再试",
            )
        await increment_usage(
            db, user_id=user_id, role=role, guest_id=guest_id,
            api_type="youtube_api",
        )
        await db.commit()

    # 解析集成配置（游客使用系统级 fallback）
    org_id = current_user.org_id if current_user else None
    icfg = await resolve_integration_config(db, org_id=org_id)

    result = await research_keyword(
        keyword=body.keyword,
        region=body.region,
        language=body.language,
        youtube_api_key=icfg.youtube_api_key,
    )

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
