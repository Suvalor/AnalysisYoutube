"""蓝海雷达参数迭代服务：CRUD + 自动复盘 + 效果追踪。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.radar_param_iteration import RadarParamIteration

logger = logging.getLogger(__name__)


async def create_iteration(
    session: AsyncSession,
    *,
    user_id: int,
    org_id: int,
    scan_params: dict,
    recommended_params: dict | None = None,
    scan_result_summary: dict | None = None,
    iteration_type: str = "manual",
) -> RadarParamIteration:
    """创建参数迭代记录，并计算与上一轮的效果对比。"""
    # 查找上一轮迭代记录，用于效果对比
    prev = await _get_latest_iteration(session, user_id=user_id)
    iteration_effect: dict | None = None
    if prev and prev.scan_result_summary and scan_result_summary:
        iteration_effect = _compute_iteration_effect(
            prev_scan_summary=prev.scan_result_summary,
            curr_scan_summary=scan_result_summary,
            prev_params=prev.scan_params,
            curr_params=scan_params,
        )

    row = RadarParamIteration(
        user_id=user_id,
        org_id=org_id,
        iteration_type=iteration_type,
        scan_params=scan_params,
        recommended_params=recommended_params,
        scan_result_summary=scan_result_summary,
        iteration_effect=iteration_effect,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def get_latest_iteration(
    session: AsyncSession, *, user_id: int
) -> RadarParamIteration | None:
    """获取用户最新的迭代记录。"""
    return await _get_latest_iteration(session, user_id=user_id)


async def get_latest_recommended_params(
    session: AsyncSession, *, user_id: int
) -> dict[str, Any] | None:
    """获取最新已应用的推荐参数。"""
    row = await _get_latest_iteration(session, user_id=user_id)
    if row and row.recommended_params:
        return row.recommended_params
    return None


async def list_iterations(
    session: AsyncSession,
    *,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[RadarParamIteration], int]:
    """分页查询迭代历史。"""
    count_q = select(sa_func.count()).select_from(RadarParamIteration).where(
        RadarParamIteration.user_id == user_id
    )
    total = (await session.execute(count_q)).scalar() or 0

    q = (
        select(RadarParamIteration)
        .where(RadarParamIteration.user_id == user_id)
        .order_by(RadarParamIteration.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list((await session.execute(q)).scalars().all())
    return rows, total


async def apply_iteration(
    session: AsyncSession, *, user_id: int, iteration_id: int
) -> bool:
    """标记某次迭代参数为已应用。"""
    q = (
        select(RadarParamIteration)
        .where(RadarParamIteration.id == iteration_id, RadarParamIteration.user_id == user_id)
    )
    row = (await session.execute(q)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="迭代记录不存在")
    if row.is_applied:
        return False
    row.is_applied = True
    row.applied_at = datetime.now()
    await session.flush()
    return True


async def auto_retrospective_for_user(
    session: AsyncSession,
    *,
    user_id: int,
    org_id: int,
) -> RadarParamIteration | None:
    """
    为单个用户执行自动复盘：调用 AI 复盘服务，持久化推荐参数。
    返回新创建的迭代记录，失败返回 None。
    """
    from app.services.youtube_ai_service import analyze_radar_retrospective
    from app.models.library import ModelLibrary, PromptLibrary

    # 使用默认模型配置（取用户第一个 chat 模型库）
    ml_q = (
        select(ModelLibrary)
        .where(ModelLibrary.user_id == user_id, ModelLibrary.library_kind == "chat")
        .order_by(ModelLibrary.id.asc())
        .limit(1)
    )
    ml = (await session.execute(ml_q)).scalar_one_or_none()
    if not ml:
        logger.warning("自动复盘：用户 %s 无 chat 模型配置，跳过", user_id)
        return None

    prompt_q = (
        select(PromptLibrary)
        .where(PromptLibrary.user_id == user_id)
        .order_by(PromptLibrary.id.asc())
        .limit(1)
    )
    prompt = (await session.execute(prompt_q)).scalar_one_or_none()
    if not prompt:
        logger.warning("自动复盘：用户 %s 无智能体配置，跳过", user_id)
        return None

    from app.services.field_encryption import try_decrypt

    api_key = try_decrypt(ml.api_key_encrypted)
    base_url = (ml.api_base_url or "").strip().rstrip("/")
    # 提取第一个支持的模型名
    import json
    supported_models = []
    try:
        data = json.loads(ml.supported_models_json or "[]")
        for item in data:
            if isinstance(item, dict) and item.get("value"):
                supported_models.append(item["value"])
            elif isinstance(item, str):
                supported_models.append(item)
    except json.JSONDecodeError:
        pass
    llm_model_name = supported_models[0] if supported_models else ""

    if not api_key or not base_url or not llm_model_name:
        logger.warning("自动复盘：用户 %s LLM 配置不完整，跳过", user_id)
        return None

    try:
        result = await analyze_radar_retrospective(
            session,
            user_id=user_id,
            org_id=org_id,
            lookback_days=14,
            top_n=8,
            model_library_id=ml.id,
            llm_model_name=llm_model_name,
            agent_id=prompt.id,
        )
    except Exception:
        logger.exception("自动复盘：用户 %s AI 复盘调用失败", user_id)
        return None

    # 获取当前扫描参数（从最新迭代记录或使用默认值）
    latest = await _get_latest_iteration(session, user_id=user_id)
    current_scan_params = latest.scan_params if latest else {
        "max_subscribers": 15000,
        "outlier_multiplier": 10,
        "published_after": 30,
    }

    # 持久化迭代记录
    row = await create_iteration(
        session,
        user_id=user_id,
        org_id=org_id,
        scan_params=current_scan_params,
        recommended_params=result.get("recommended_parameters"),
        scan_result_summary={
            "analysis_summary": result.get("analysis_summary", ""),
            "sample_meta": result.get("sample_meta", {}),
        },
        iteration_type="auto",
    )
    # 自动标记为已应用
    row.is_applied = True
    row.applied_at = datetime.now()
    await session.flush()
    return row


async def _get_latest_iteration(
    session: AsyncSession, *, user_id: int
) -> RadarParamIteration | None:
    """获取用户最新的迭代记录（内部方法）。"""
    q = (
        select(RadarParamIteration)
        .where(RadarParamIteration.user_id == user_id)
        .order_by(RadarParamIteration.created_at.desc())
        .limit(1)
    )
    return (await session.execute(q)).scalar_one_or_none()


def _compute_iteration_effect(
    *,
    prev_scan_summary: dict,
    curr_scan_summary: dict,
    prev_params: dict,
    curr_params: dict,
) -> dict[str, Any]:
    """计算两次迭代间的效果对比。"""
    return {
        "params_delta": {
            "max_subscribers": curr_params.get("max_subscribers", 0) - prev_params.get("max_subscribers", 0),
            "outlier_multiplier": round(
                curr_params.get("outlier_multiplier", 0) - prev_params.get("outlier_multiplier", 0), 2
            ),
        },
        "prev_summary": prev_scan_summary,
        "curr_summary": curr_scan_summary,
    }
