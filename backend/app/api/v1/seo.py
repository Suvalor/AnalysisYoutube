"""SEO 评分 + 热门趋势 API。"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, DBSessionDep
from app.schemas.seo_scoring import SeoScoringRequest, SeoScoringResponse
from app.schemas.trend_discovery import TrendDiscoveryRequest, TrendDiscoveryResponse
from app.services.config_manager import resolve_integration_config
from app.services.seo_scoring_service import score_seo
from app.services.trend_discovery_service import fetch_trending
from app.services.quota_service import record_api_quota_usage

router = APIRouter()


# ── SEO 评分 ──


@router.post(
    "/seo-score",
    response_model=SeoScoringResponse,
    summary="视频 SEO 评分",
)
async def seo_scoring_endpoint(
    body: SeoScoringRequest,
    current_user: CurrentUserDep,
) -> SeoScoringResponse:
    """
    对视频标题/描述/标签进行 SEO 质量评分（0-100）。
    纯算法评分，不消耗 YouTube API 配额。
    """
    result = score_seo(
        title=body.title,
        description=body.description,
        tags=body.tags,
        target_keyword=body.target_keyword,
    )
    return SeoScoringResponse(**result)


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
    消耗 YouTube API 配额（1 次 videos.list + 1 次 channels.list）。
    """
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

    # 记录配额消耗（videos.list 1次 + channels.list 1次）
    await record_api_quota_usage(db, "videos", times=1, part_count=3)
    await record_api_quota_usage(db, "channels", times=1, part_count=2)
    await db.commit()

    return TrendDiscoveryResponse(**result)
