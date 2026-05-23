import json
from collections import OrderedDict
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep
from app.api.deps import DBSessionDep, create_quota_guard
from app.crud.library import get_by_user, list_by_user
from app.services.llm_openai_factory import LLMClientFactory, LLMClientConfig, normalize_base_url
from app.models.library import ModelLibrary
from app.services.field_encryption import try_decrypt
from app.services.script_user_ai import (
    DEFAULT_MODEL_OPTIONS,
    parse_models_from_user_json,
    resolve_prompt_and_style,
    user_custom_openai_credentials,
)
from app.services.llm_conversation_service import (
    load_conversation_messages,
    save_conversation_turn,
)


router = APIRouter()


class ScriptGenerateRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=128)
    prompt_template: str = Field(..., min_length=1, max_length=8000)
    style: str = Field(..., min_length=1, max_length=8000)
    core_idea: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = Field(None, description="对话 ID（entity_type:entity_id），不传则新建")
    model_library_id: int | None = Field(None, ge=1, description="模型库 ID（无用户自定义 API 时必传）")


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _parse_models_from_library_rows(rows: list[ModelLibrary]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        raw = (row.supported_models_json or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if isinstance(item, str) and item.strip():
                value = item.strip()
                out.append({"value": value, "label": f"{row.name} / {value}"})
            elif isinstance(item, dict):
                value = str(item.get("value") or "").strip()
                if not value:
                    continue
                label = str(item.get("label") or value).strip()
                out.append({"value": value, "label": f"{row.name} / {label}"})
    # 以 value 去重，保留首次出现顺序
    dedup = OrderedDict()
    for item in out:
        dedup[item["value"]] = item
    return list(dedup.values())


@router.get(
    "/models",
    summary="当前用户可用的剧本生成模型列表",
)
async def list_script_models(
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """从用户设置的 ai_models_json 解析；未配置时返回内置默认项。"""
    models = parse_models_from_user_json(current_user.ai_models_json)
    if models == DEFAULT_MODEL_OPTIONS:
        rows = await list_by_user(db, ModelLibrary, current_user.id)
        rows = [r for r in rows if (getattr(r, "library_kind", None) or "chat") == "chat"]
        lib_models = _parse_models_from_library_rows(rows)
        if lib_models:
            models = lib_models
    return {"models": models}


@router.post("/generate")
async def generate_script(
    payload: ScriptGenerateRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    _quota: bool = Depends(create_quota_guard("llm_api")),
) -> StreamingResponse:
    creds = user_custom_openai_credentials(current_user)
    if creds:
        api_key, base_url_raw = creds
        base_url = normalize_base_url(base_url_raw)
        model_name_raw = payload.model
        protocol = "openai"  # 用户自定义凭证走 OpenAI 兼容协议
    else:
        # 无用户自定义凭证时，从 ModelLibrary 获取；需传入 model_library_id
        if not payload.model_library_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LLM 未配置：请在用户设置中配置自建 API，或在请求中指定 model_library_id",
            )
        ml = await get_by_user(db, ModelLibrary, current_user.id, payload.model_library_id)
        if ml is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型配置不存在或无权访问",
            )
        api_key = try_decrypt(ml.api_key_encrypted)
        base_url = normalize_base_url((ml.api_base_url or "").strip())
        protocol = (ml.protocol or "anthropic").strip()
        if not api_key or not base_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该模型配置缺少 API Key 或 Base URL，请在设置中心补全",
            )
        model_name_raw = payload.model
    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=api_key, base_url=base_url, model_name=model_name_raw, protocol=protocol)
    resolved_model = factory.resolve_model_name(cfg)
    if not resolved_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择或填写模型",
        )

    prompt_text, style_text = resolve_prompt_and_style(
        current_user,
        payload.prompt_template.strip(),
        payload.style.strip(),
    )

    system_prompt = (
        "你是一名资深短视频脚本策划与编剧。\n"
        f"【提示词模板】{prompt_text}\n"
        f"【风格要求】{style_text}\n"
        "请输出结构清晰、可直接拍摄的中文内容。"
    )
    user_prompt = f"请围绕以下主题创作完整脚本：{payload.core_idea}"

    # 对话记忆：加载历史消息
    entity_type = "script"
    entity_id = payload.conversation_id or f"script:{payload.core_idea[:64]}"
    history = await load_conversation_messages(
        db,
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    # 构建消息列表：有历史则追加当前 user 消息；无历史则用 system + user
    if history:
        messages = history + [{"role": "user", "content": user_prompt}]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    # 收集完整 assistant 回复用于保存
    collected_deltas: list[str] = []

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for delta in factory.stream_chat_completions_deltas(
                cfg=cfg,
                temperature=0.7,
                messages=messages,
            ):
                collected_deltas.append(delta)
                yield _sse({"type": "delta", "content": delta})
            yield _sse({"type": "done", "conversation_id": f"{entity_type}:{entity_id}"})
            # 流结束后保存对话
            assistant_content = "".join(collected_deltas)
            try:
                await save_conversation_turn(
                    db,
                    user_id=current_user.id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    user_content=user_prompt,
                    assistant_content=assistant_content,
                    system_content=system_prompt if not history else None,
                    model_name=resolved_model,
                )
                await db.commit()
            except Exception:  # noqa: BLE001
                import logging as _logging
                _logging.getLogger(__name__).exception("保存对话历史失败")
                await db.rollback()
        except Exception as exc:  # noqa: BLE001
            import logging as _logging
            _logging.getLogger(__name__).exception("SSE generate 异常 model=%s", resolved_model)
            msg = "AI 生成服务异常，请稍后重试"
            if "404" in str(exc):
                msg = f"模型不可用或未开通（model={resolved_model}），请检查配置"
            yield _sse({"type": "error", "message": msg})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
