"""蓝海雷达 API（仅查询 YouTube，不落库）。"""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.schemas.radar import (
    BlueOceanChannelItem,
    BlueOceanRadarRequest,
    BlueOceanRadarResponse,
    CategoryOpportunityRequest,
    CategoryOpportunityResponse,
    CrossRegionCompareRequest,
    CrossRegionCompareResponse,
    ExportReportRequest,
    ExportReportResponse,
    RadarAiRetrospectiveRequest,
    RadarAiRetrospectiveResponse,
    NavigationGuideRequest,
    NavigationGuideResponse,
)
from app.services.config_manager import resolve_integration_config
from app.services.quota_service import record_api_quota_usage
from app.services.youtube_service import blue_ocean_radar_scan, category_opportunity_scan, cross_region_compare
from app.services.youtube_ai_service import analyze_radar_retrospective
from app.services.radar_report_service import generate_radar_report
from app.services.radar_navigation_service import navigation_guide
from app.services.llm_conversation_service import (
    load_conversation_messages,
    save_conversation_turn,
)

router = APIRouter()


@router.post(
    "/scan",
    response_model=BlueOceanRadarResponse,
    summary="蓝海雷达深度扫描（仅查询，不落库）",
)
async def blue_ocean_scan(
    body: BlueOceanRadarRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> BlueOceanRadarResponse:
    """
    调用 YouTube search.list + videos.list + channels.list，按粉丝上限与爆款系数过滤。
    成功后会记入当日 API 配额用量。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    vd = body.video_duration
    result = await blue_ocean_radar_scan(
        keyword=body.keyword,
        published_after_days=body.published_after,
        max_subscribers=body.max_subscribers,
        outlier_multiplier=body.outlier_multiplier,
        youtube_api_key=icfg.youtube_api_key,
        video_duration=vd,
    )
    if result.search_calls > 0:
        await record_api_quota_usage(db, "search", times=result.search_calls)
    if result.videos_list_calls > 0:
        await record_api_quota_usage(db, "videos", times=result.videos_list_calls)
    if result.channels_list_calls > 0:
        await record_api_quota_usage(db, "channels", times=result.channels_list_calls)
    await db.commit()

    items = [BlueOceanChannelItem.model_validate(x) for x in result.items]
    return BlueOceanRadarResponse(items=items, warnings=result.warnings)


@router.post(
    "/ai-retrospective",
    response_model=RadarAiRetrospectiveResponse,
    summary="蓝海雷达 AI 参数复盘与推荐",
)
async def radar_ai_retrospective(
    body: RadarAiRetrospectiveRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> RadarAiRetrospectiveResponse:
    # 加载对话记忆
    entity_type = "radar_retro"
    entity_id = body.conversation_id or f"lookback:{body.lookback_days}:top:{body.top_n}"
    history = await load_conversation_messages(
        db,
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    result = await analyze_radar_retrospective(
        db,
        user_id=current_user.id,
        org_id=current_user.org_id,
        lookback_days=body.lookback_days,
        top_n=body.top_n,
        model_library_id=body.model_library_id,
        llm_model_name=body.llm_model_name,
        agent_id=body.agent_id,
        conversation_history=history,
    )

    # 保存对话
    if result.get("_user_prompt") and result.get("_assistant_content"):
        try:
            await save_conversation_turn(
                db,
                user_id=current_user.id,
                entity_type=entity_type,
                entity_id=entity_id,
                user_content=result["_user_prompt"],
                assistant_content=result["_assistant_content"],
                system_content=result.get("_system_prompt"),
                model_name=body.llm_model_name,
            )
            await db.commit()
        except Exception:  # noqa: BLE001
            import logging as _logging
            _logging.getLogger(__name__).exception("保存雷达复盘对话历史失败")
            await db.rollback()

    response_data = result.copy()
    response_data["conversation_id"] = f"{entity_type}:{entity_id}"
    return RadarAiRetrospectiveResponse.model_validate(response_data)


@router.post(
    "/category-opportunity",
    response_model=CategoryOpportunityResponse,
    summary="品类机会报告",
)
async def category_opportunity(
    body: CategoryOpportunityRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> CategoryOpportunityResponse:
    """
    输入品类关键词，输出该品类的市场机会分析：
    头部频道增速、内容缺口、新入局者成功率。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    result = await category_opportunity_scan(
        keyword=body.keyword,
        region=body.region,
        lookback_months=body.lookback_months,
        youtube_api_key=icfg.youtube_api_key,
    )
    await record_api_quota_usage(db, "search", times=1)
    await db.commit()
    return CategoryOpportunityResponse(
        keyword=body.keyword,
        region=body.region,
        top_channels_growth=result["top_channels_growth"],
        content_gaps=result["content_gaps"],
        newcomer_stats=result["newcomer_stats"],
    )


@router.post(
    "/cross-region-compare",
    response_model=CrossRegionCompareResponse,
    summary="跨地区对比",
)
async def cross_region_compare_endpoint(
    body: CrossRegionCompareRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> CrossRegionCompareResponse:
    """
    同一关键词，对比不同地区的市场情况（US/SEA/ME 等）。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    snapshots = await cross_region_compare(
        keyword=body.keyword,
        regions=body.regions,
        published_after_days=body.published_after,
        youtube_api_key=icfg.youtube_api_key,
    )
    await record_api_quota_usage(db, "search", times=len(body.regions))
    await db.commit()
    return CrossRegionCompareResponse(keyword=body.keyword, regions=snapshots)


@router.post(
    "/export-report",
    response_model=ExportReportResponse,
    summary="一键出报告",
)
async def export_report(
    body: ExportReportRequest,
    current_user: CurrentUserDep,
) -> ExportReportResponse:
    """
    将扫描结果生成 Markdown 格式报告，前端可渲染为 PDF/图片。
    """
    markdown_content = generate_radar_report(
        scan_items=body.scan_items,
        keyword=body.keyword,
        ai_summary=body.ai_summary,
    )
    return ExportReportResponse(markdown_content=markdown_content)


@router.post(
    "/navigation-guide",
    response_model=NavigationGuideResponse,
    summary="出海导航",
)
async def navigation_guide_endpoint(
    body: NavigationGuideRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> NavigationGuideResponse:
    """
    输入自身资源（语言能力、内容形式、预算），推荐最适合的品类+地区组合，
    并给出 Top5 频道的内容策略拆解。
    """
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    result = await navigation_guide(
        db=db,
        user_id=current_user.id,
        org_id=current_user.org_id,
        languages=body.languages,
        content_format=body.content_format,
        budget_level=body.budget_level,
        youtube_api_key=icfg.youtube_api_key,
        model_library_id=body.model_library_id,
        llm_model_name=body.llm_model_name,
        agent_id=body.agent_id,
    )
    return NavigationGuideResponse.model_validate(result)
