"""蓝海雷达 API（仅查询 YouTube，不落库）。"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserDep, DBSessionDep, create_quota_guard
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
    NavigationGuideResponse,
    NavigationQuotaUsage,
    NicheRecommendation,
    AvoidNiche,
    QuotaCheckInfo,
    RadarAiRetrospectiveRequest,
    RadarAiRetrospectiveResponse,
    NavigationGuideRequest,
    NavigationChatRequest,
    NavigationChatResponse,
    NavigationGuideRecordItem,
    NavigationGuideRecordDetail,
    NavigationGuideRecordListResponse,
)
from app.schemas.radar_param_iteration import (
    RadarParamIterationCreate,
    RadarParamIterationItem,
    RadarParamIterationListResponse,
    RadarParamLatestResponse,
    RadarParamApplyResponse,
    AutoRetroRequest,
    AutoRetroResponse,
)
from app.services.config_manager import resolve_integration_config
from app.services.quota_service import record_api_quota_usage
from app.services.youtube_service import blue_ocean_radar_scan, category_opportunity_scan, cross_region_compare
from app.services.youtube_ai_service import analyze_radar_retrospective
from app.services.radar_report_service import generate_radar_report
from app.services.radar_navigation_service import navigation_guide, navigation_chat
from app.services.quota_guard_service import check_quota_before_navigation
from app.services.radar_param_iteration_service import (
    create_iteration,
    get_latest_iteration,
    get_latest_recommended_params,
    list_iterations,
    apply_iteration,
    auto_retrospective_for_user,
)
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
    _quota: bool = Depends(create_quota_guard("youtube_api")),
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
        await record_api_quota_usage(db, "videos", times=result.videos_list_calls, part_count=2)
    if result.channels_list_calls > 0:
        await record_api_quota_usage(db, "channels", times=result.channels_list_calls, part_count=2)
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
    _quota: bool = Depends(create_quota_guard("llm_api")),
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

    # 自动持久化参数迭代记录
    try:
        from app.services.radar_param_iteration_service import create_iteration
        await create_iteration(
            db,
            user_id=current_user.id,
            org_id=current_user.org_id,
            scan_params={
                "max_subscribers": body.lookback_days,
                "lookback_days": body.lookback_days,
                "top_n": body.top_n,
            },
            recommended_params=result.get("recommended_parameters"),
            scan_result_summary={
                "analysis_summary": result.get("analysis_summary", ""),
                "sample_meta": result.get("sample_meta", {}),
            },
            iteration_type="manual",
        )
    except Exception:  # noqa: BLE001
        import logging as _logging2
        _logging2.getLogger(__name__).exception("自动保存参数迭代记录失败，不影响复盘结果")

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
    # 配额：1 search + N videos + M channels（估算：search=1, videos=1, channels=1）
    await record_api_quota_usage(db, "search", times=1)
    await record_api_quota_usage(db, "videos", times=result.get("videos_list_calls", 1), part_count=2)
    await record_api_quota_usage(db, "channels", times=result.get("channels_list_calls", 1), part_count=2)
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
    result = await cross_region_compare(
        keyword=body.keyword,
        regions=body.regions,
        published_after_days=body.published_after,
        youtube_api_key=icfg.youtube_api_key,
    )
    snapshots = result["snapshots"]
    channels_calls = result.get("channels_calls", 0)
    await record_api_quota_usage(db, "search", times=len(body.regions))
    if channels_calls > 0:
        await record_api_quota_usage(db, "channels", times=channels_calls, part_count=2)
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
    出海导航：基于用户完整资源画像（语言+形式+预算+核心技能+变现目标），
    LLM 深度推荐细分品类，YouTube API 补充市场数据。
    """
    from fastapi import HTTPException, status

    # ── 配额前置检查 ──
    quota_check = await check_quota_before_navigation(
        db, estimated_search_calls=6, estimated_channel_calls=6,
    )
    if not quota_check.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "YouTube API 配额不足，无法执行导航",
                "remaining": quota_check.remaining,
                "estimated_cost": quota_check.estimated_cost,
                "today_used": quota_check.today_used,
                "today_total": quota_check.today_total,
            },
        )

    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    result = await navigation_guide(
        db=db,
        user_id=current_user.id,
        org_id=current_user.org_id,
        languages=body.languages,
        content_format=body.content_format,
        budget_level=body.budget_level,
        core_skills=body.core_skills,
        monetization_goal=body.monetization_goal,
        existing_channel_url=body.existing_channel_url,
        target_regions=body.target_regions,
        weekly_hours=body.weekly_hours,
        youtube_api_key=icfg.youtube_api_key,
        model_library_id=body.model_library_id,
        llm_model_name=body.llm_model_name,
        agent_id=body.agent_id,
    )

    # ── 记录 API 配额消耗 ──
    quota_usage = result.get("quota_usage", {})
    search_calls = quota_usage.get("search_calls", 0)
    channels_calls = quota_usage.get("channels_calls", 0)
    if search_calls > 0:
        await record_api_quota_usage(db, "search", times=search_calls)
    if channels_calls > 0:
        await record_api_quota_usage(db, "channels", times=channels_calls, part_count=2)
    await db.commit()

    # 重新获取最新配额状态
    quota_check_after = await check_quota_before_navigation(
        db, estimated_search_calls=0, estimated_channel_calls=0,
    )

    # ── 构建响应 ──
    recommendations = [
        NicheRecommendation.model_validate(r) for r in result.get("recommendations", [])
    ]
    avoid_niche_data = result.get("avoid_niche")
    avoid_niche = AvoidNiche.model_validate(avoid_niche_data) if avoid_niche_data else None

    # 生成对话 ID 供多轮追问使用
    import uuid
    conversation_id = f"nav_guide:{current_user.id}:{uuid.uuid4().hex[:8]}"

    response = NavigationGuideResponse(
        recommendations=recommendations,
        avoid_niche=avoid_niche,
        ai_summary=result.get("ai_summary"),
        quota_usage=NavigationQuotaUsage(
            search_calls=search_calls,
            channels_calls=channels_calls,
            total_points=search_calls * 100 + channels_calls * 1,
        ),
        quota_check=QuotaCheckInfo(
            allowed=quota_check_after.remaining > 0,
            remaining=quota_check_after.remaining,
            estimated_cost=0,
            today_used=quota_check_after.today_used,
            today_total=quota_check_after.today_total,
        ),
        conversation_id=conversation_id,
        channel_info=result.get("channel_info"),
    )

    # ── 自动保存推荐记录 ──
    try:
        from app.models.navigation_guide_record import NavigationGuideRecord
        record = NavigationGuideRecord(
            user_id=current_user.id,
            org_id=current_user.org_id,
            request_params=body.model_dump(),
            result={
                "recommendations": [r.model_dump() for r in recommendations],
                "avoid_niche": avoid_niche.model_dump() if avoid_niche else None,
                "ai_summary": result.get("ai_summary"),
                "channel_info": result.get("channel_info"),
            },
        )
        db.add(record)
        await db.commit()
    except Exception:  # noqa: BLE001
        import logging as _nav_log
        _nav_log.getLogger(__name__).exception("自动保存导航推荐记录失败，不影响推荐结果")
        await db.rollback()

    return response


@router.post(
    "/navigation-chat",
    response_model=NavigationChatResponse,
    summary="出海导航追问",
)
async def navigation_chat_endpoint(
    body: NavigationChatRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> NavigationChatResponse:
    """
    出海导航多轮对话：用户对推荐结果追问，AI 基于上下文继续分析。
    """
    result = await navigation_chat(
        db=db,
        user_id=current_user.id,
        org_id=current_user.org_id,
        conversation_id=body.conversation_id,
        user_message=body.user_message,
        model_library_id=body.model_library_id,
        llm_model_name=body.llm_model_name,
        agent_id=body.agent_id,
    )
    return NavigationChatResponse(
        assistant_message=result["assistant_message"],
        conversation_id=result["conversation_id"],
    )


# ── 出海导航推荐记录 API ──


@router.get(
    "/navigation-records",
    response_model=NavigationGuideRecordListResponse,
    summary="查询出海导航推荐历史",
)
async def list_navigation_records(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> NavigationGuideRecordListResponse:
    """分页查询当前用户的出海导航推荐历史记录。"""
    from sqlalchemy import select, func as sa_func
    from app.models.navigation_guide_record import NavigationGuideRecord

    count_q = select(sa_func.count()).select_from(NavigationGuideRecord).where(
        NavigationGuideRecord.user_id == current_user.id
    )
    total = (await db.execute(count_q)).scalar() or 0

    rows_q = (
        select(NavigationGuideRecord)
        .where(NavigationGuideRecord.user_id == current_user.id)
        .order_by(NavigationGuideRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(rows_q)).scalars().all()

    items = []
    for row in rows:
        recs = (row.result or {}).get("recommendations", [])
        top_rec = recs[0] if recs else None
        items.append(NavigationGuideRecordItem(
            id=row.id,
            request_params=row.request_params or {},
            top_niche_title=top_rec.get("niche_title") if top_rec else None,
            top_match_score=top_rec.get("match_score") if top_rec else None,
            recommendation_count=len(recs),
            created_at=row.created_at,
        ))

    return NavigationGuideRecordListResponse(items=items, total=total)


@router.get(
    "/navigation-records/{record_id}",
    response_model=NavigationGuideRecordDetail,
    summary="查看出海导航推荐详情",
)
async def get_navigation_record(
    record_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> NavigationGuideRecordDetail:
    """查看单条出海导航推荐记录的完整内容。"""
    from fastapi import HTTPException, status
    from sqlalchemy import select
    from app.models.navigation_guide_record import NavigationGuideRecord

    q = select(NavigationGuideRecord).where(
        NavigationGuideRecord.id == record_id,
        NavigationGuideRecord.user_id == current_user.id,
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")

    return NavigationGuideRecordDetail(
        id=row.id,
        request_params=row.request_params or {},
        result=row.result or {},
        created_at=row.created_at,
    )


@router.delete(
    "/navigation-records/{record_id}",
    summary="删除出海导航推荐记录",
)
async def delete_navigation_record(
    record_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """删除单条出海导航推荐记录。"""
    from fastapi import HTTPException, status
    from sqlalchemy import select
    from app.models.navigation_guide_record import NavigationGuideRecord

    q = select(NavigationGuideRecord).where(
        NavigationGuideRecord.id == record_id,
        NavigationGuideRecord.user_id == current_user.id,
    )
    row = (await db.execute(q)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")

    await db.delete(row)
    await db.commit()
    return {"message": "已删除"}


# ── 参数迭代 API ──


@router.get(
    "/param-iterations/latest",
    response_model=RadarParamLatestResponse,
    summary="获取最新推荐参数",
)
async def get_latest_params(
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> RadarParamLatestResponse:
    """获取当前用户最新的 AI 推荐参数，用于扫描页面自动回填。"""
    from sqlalchemy import select, func as sa_func
    from app.models.radar_param_iteration import RadarParamIteration

    latest = await get_latest_iteration(db, user_id=current_user.id)
    count_q = select(sa_func.count()).select_from(RadarParamIteration).where(
        RadarParamIteration.user_id == current_user.id
    )
    total = (await db.execute(count_q)).scalar() or 0

    return RadarParamLatestResponse(
        recommended_params=latest.recommended_params if latest else None,
        iteration_count=total,
        last_iteration_at=latest.created_at if latest else None,
    )


@router.post(
    "/param-iterations",
    response_model=RadarParamIterationItem,
    summary="保存迭代记录",
)
async def save_iteration(
    body: RadarParamIterationCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> RadarParamIterationItem:
    """手动保存一次参数迭代记录。"""
    row = await create_iteration(
        db,
        user_id=current_user.id,
        org_id=current_user.org_id,
        scan_params=body.scan_params,
        recommended_params=body.recommended_params,
        scan_result_summary=body.scan_result_summary,
        iteration_type=body.iteration_type,
    )
    await db.commit()
    await db.refresh(row)
    return RadarParamIterationItem.model_validate(row)


@router.get(
    "/param-iterations",
    response_model=RadarParamIterationListResponse,
    summary="查询迭代历史",
)
async def list_iteration_history(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> RadarParamIterationListResponse:
    """分页查询参数迭代历史记录。"""
    rows, total = await list_iterations(db, user_id=current_user.id, limit=limit, offset=offset)
    return RadarParamIterationListResponse(
        items=[RadarParamIterationItem.model_validate(r) for r in rows],
        total=total,
    )


@router.post(
    "/param-iterations/apply/{iteration_id}",
    response_model=RadarParamApplyResponse,
    summary="应用迭代参数",
)
async def apply_iteration_params(
    iteration_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> RadarParamApplyResponse:
    """标记某次迭代参数为已应用，下次扫描将自动回填。"""
    changed = await apply_iteration(db, user_id=current_user.id, iteration_id=iteration_id)
    await db.commit()
    return RadarParamApplyResponse(
        success=True,
        message="参数已应用" if changed else "参数已处于应用状态",
    )


@router.post(
    "/param-iterations/auto-retro",
    response_model=AutoRetroResponse,
    summary="手动触发自动复盘",
)
async def trigger_auto_retrospective(
    body: AutoRetroRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> AutoRetroResponse:
    """手动触发一次自动复盘，AI 分析历史数据并推荐下一轮参数。"""
    row = await auto_retrospective_for_user(
        db,
        user_id=current_user.id,
        org_id=current_user.org_id,
    )
    if not row:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自动复盘失败：请检查是否有足够的扫描数据，以及 LLM 配置是否完整",
        )
    await db.commit()
    return AutoRetroResponse(
        iteration_id=row.id,
        recommended_params=row.recommended_params or {},
        analysis_summary=(row.scan_result_summary or {}).get("analysis_summary", ""),
    )
