from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.library import get_by_user, list_by_user
from app.crud.youtube import get_video_for_user, get_video_analysis_for_org, upsert_video_analysis, batch_check_video_analysis
from app.models.library import ModelLibrary, PromptLibrary
from app.models.youtube import YouTubeVideo
from app.schemas.youtube import YouTubeVideoAnalysisResponse, YouTubeVideoAnalyzeRequest
from app.services.field_encryption import try_decrypt
from app.services.llm_openai_factory import LLMClientFactory, LLMClientConfig


router = APIRouter()


def _parse_supported_model_values(raw: str | None) -> list[str]:
    """
    从 model_libraries.supported_models_json 解析出 supported model 的 value 列表。
    支持两种格式：
    - ["ep-xxx", "ark-code-latest"]
    - [{"label":"xx","value":"ep-xxx"}]
    """
    if not raw:
        return []
    s = raw.strip()
    if not s:
        return []
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for item in data:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            v = item.get("value")
            if isinstance(v, str) and v.strip():
                out.append(v.strip())
    return out


async def _resolve_model_library_by_model_id(
    *,
    session: DBSessionDep,
    user_id: int,
    model_id: str,
) -> ModelLibrary | None:
    rows = await list_by_user(session, ModelLibrary, user_id)
    for ml in rows:
        values = _parse_supported_model_values(ml.supported_models_json)
        if model_id in values:
            return ml
    return None


@router.post("/analyze", response_model=YouTubeVideoAnalysisResponse, summary="对视频执行 AI 深度洞察并持久化写入")
async def analyze_video(
    payload: YouTubeVideoAnalyzeRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubeVideoAnalysisResponse:
    video = await get_video_for_user(db, user_id=current_user.id, video_id=payload.video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在或无权限访问")

    if not payload.model_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_id 不能为空")

    ml = await _resolve_model_library_by_model_id(session=db, user_id=current_user.id, model_id=payload.model_id.strip())
    if ml is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到与该 model_id 匹配的模型配置（请在设置中心模型管理中维护支持模型列表）",
        )

    api_key = try_decrypt(ml.api_key_encrypted)
    base_url = (ml.api_base_url or "").strip().rstrip("/")
    if not api_key or not base_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该模型配置缺少 API Key 或 Base URL")

    agent_prompt: str | None = None
    if payload.agent_id is not None:
        pl = await get_by_user(db, PromptLibrary, current_user.id, payload.agent_id)
        if pl is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="智能体不存在或无权访问")
        agent_prompt = (pl.content or "").strip() or None

    system_prompt = (
        "你是资深 YouTube 视频分析师。\n"
        "请基于用户提供的视频标题与描述，输出 AI 深度洞察，必须使用 Markdown 格式，且只输出 Markdown 内容。\n"
        "建议结构（可按需调整）：\n"
        "1) 内容主题与定位\n"
        "2) 结构节奏与信息密度\n"
        "3) 受众画像与传播动机\n"
        "4) 爆款要点拆解\n"
        "5) 可执行的拍摄/脚本改进建议\n"
        "不要输出 JSON，不要输出除 Markdown 之外的任何内容。\n"
    )
    if agent_prompt:
        system_prompt = f"{system_prompt}\n【智能体补充规则】\n{agent_prompt}"

    user_prompt = (
        f"【视频标题】\n{video.title}\n\n"
        f"【视频描述】\n{video.description or ''}\n\n"
        "请开始分析并给出 Markdown 深度洞察。"
    )

    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=api_key, base_url=base_url, model_name=payload.model_id.strip())
    resolved_model = factory.resolve_model_name(cfg)
    if not resolved_model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模型名解析失败，可能与该 Base URL 不兼容")

    try:
        content = await factory.chat_completions_content(
            cfg=cfg,
            temperature=0.35,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI 分析调用失败: {exc}") from exc

    row = await upsert_video_analysis(
        db,
        org_id=current_user.org_id,
        video_id=video.id,
        model_id=payload.model_id.strip(),
        agent_id=payload.agent_id,
        content=content or "",
    )

    return YouTubeVideoAnalysisResponse(
        video_id=row.video_id,
        model_id=row.model_id,
        agent_id=row.agent_id,
        content=row.content,
        updated_at=row.updated_at,
    )


@router.get("/batch-analysis-status")
async def batch_analysis_status(
    current_user: CurrentUserDep,
    db: DBSessionDep,
    video_ids: str = Query(..., description="Comma-separated internal video IDs"),
) -> dict[int, bool]:
    """Check which videos have existing analysis. Returns {video_id: has_analysis}."""
    try:
        ids = [int(x.strip()) for x in video_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="video_ids must be comma-separated integers")
    if not ids:
        return {}
    return await batch_check_video_analysis(db, ids, current_user.org_id)


@router.get("/analysis/{video_id}", response_model=YouTubeVideoAnalysisResponse, summary="获取视频已持久化的 AI 分析结果")
async def get_video_analysis(
    video_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> YouTubeVideoAnalysisResponse:
    video = await get_video_for_user(db, user_id=current_user.id, video_id=video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在或无权限访问")

    row = await get_video_analysis_for_org(db, org_id=current_user.org_id, video_id=video_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该视频尚未生成 AI 分析结果")

    return YouTubeVideoAnalysisResponse(
        video_id=row.video_id,
        model_id=row.model_id,
        agent_id=row.agent_id,
        content=row.content,
        updated_at=row.updated_at,
    )