import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.library import get_by_user
from app.models.library import ModelLibrary, PromptLibrary, StyleLibrary
from app.schemas.library import GenerateScriptStreamRequest
from app.services.field_encryption import try_decrypt
from app.services.llm_openai_factory import LLMClientFactory, LLMClientConfig, normalize_base_url
from app.services.llm_conversation_service import (
    load_conversation_messages,
    save_conversation_turn,
)


router = APIRouter()


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/generate-script-stream")
async def generate_script_stream(
    payload: GenerateScriptStreamRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    prompt = await get_by_user(db, PromptLibrary, current_user.id, payload.prompt_id)
    style = await get_by_user(db, StyleLibrary, current_user.id, payload.style_id)
    if prompt is None or style is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提示词或风格不存在",
        )

    ml = await get_by_user(db, ModelLibrary, current_user.id, payload.model_library_id)
    if ml is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型配置不存在或无权访问",
        )
    api_key = try_decrypt(ml.api_key_encrypted)
    base_url = normalize_base_url((ml.api_base_url or "").strip())
    if not api_key or not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该模型配置缺少 API Key 或 Base URL，请在设置中心补全",
        )

    # 解析模型名称：优先使用请求中指定的，否则取模型库默认首个
    model_name = (payload.model_name or "").strip()
    if not model_name:
        supported = ml.supported_models_json
        if supported:
            try:
                models = json.loads(supported)
                if isinstance(models, list) and models:
                    first = models[0]
                    if isinstance(first, str):
                        model_name = first.strip()
                    elif isinstance(first, dict):
                        model_name = str(first.get("value") or "").strip()
            except (json.JSONDecodeError, TypeError):
                pass
    if not model_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="模型名不能为空，请在请求中指定或在模型库中维护支持模型列表",
        )

    protocol = (ml.protocol or "anthropic").strip()
    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=api_key, base_url=base_url, model_name=model_name, protocol=protocol)
    resolved_model = factory.resolve_model_name(cfg)
    system_prompt = (
        "你是一个专业的内容创作者。\n"
        f"【核心任务】: {prompt.content}\n"
        f"【文风与格式】: {style.content}"
    )
    user_message = f"请以【{payload.topic}】为主题创作。"

    # 对话记忆
    entity_type = "ai_script"
    entity_id = f"prompt:{payload.prompt_id}:style:{payload.style_id}"
    history = await load_conversation_messages(
        db,
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    if history:
        messages = history + [{"role": "user", "content": user_message}]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

    collected_deltas: list[str] = []

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for delta in factory.stream_chat_completions_deltas(
                cfg=cfg,
                messages=messages,
                temperature=0.7,
            ):
                collected_deltas.append(delta)
                yield _sse({"type": "delta", "content": delta})
            yield _sse({"type": "done", "conversation_id": f"{entity_type}:{entity_id}"})
            # 保存对话
            assistant_content = "".join(collected_deltas)
            try:
                await save_conversation_turn(
                    db,
                    user_id=current_user.id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    user_content=user_message,
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
            _logging.getLogger(__name__).exception("SSE generate-script-stream 异常")
            yield _sse({"type": "error", "message": "AI 生成服务异常，请稍后重试"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

