"""关键词研究 API 路由。"""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.schemas.keyword_research import (
    KeywordResearchRequest,
    KeywordResearchResponse,
    RelatedKeywordItem,
    TopVideoItem,
    TrendDataPoint,
)
from app.services.keyword_research_service import research_keyword
from app.services.config_manager import resolve_integration_config
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
    current_user: CurrentUserDep,
) -> KeywordResearchResponse:
    """
    执行关键词研究，返回搜索量/竞争度/KD/机会得分/趋势等评分数据。

    - 调用 YouTube Data API 获取搜索数据
    - 使用启发式评分算法计算各维度评分
    - 消耗约 3-4 次 search.list 配额（300-400 单位）
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)

    result = await research_keyword(
        keyword=body.keyword,
        region=body.region,
        language=body.language,
        youtube_api_key=icfg.youtube_api_key,
    )

    # 记录配额消耗
    search_calls = result.get("search_calls", 0)
    if search_calls > 0:
        await record_api_quota_usage(
            db, "search", times=search_calls, part_count=2
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
