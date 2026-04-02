import json
from collections import OrderedDict
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.api.deps import CurrentUserDep
from app.api.deps import DBSessionDep
from app.crud.library import list_by_user
from app.services.config_manager import resolve_integration_config, resolve_model_alias_for_volcengine
from app.models.library import ModelLibrary
from app.services.script_user_ai import (
    DEFAULT_MODEL_OPTIONS,
    parse_models_from_user_json,
    resolve_prompt_and_style,
    user_custom_openai_credentials,
)


router = APIRouter()


class ScriptGenerateRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=128)
    prompt_template: str = Field(..., min_length=1, max_length=8000)
    style: str = Field(..., min_length=1, max_length=8000)
    core_idea: str = Field(..., min_length=1, max_length=4000)


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
        lib_models = _parse_models_from_library_rows(rows)
        if lib_models:
            models = lib_models
    return {"models": models}


@router.post("/generate")
async def generate_script(
    payload: ScriptGenerateRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    creds = user_custom_openai_credentials(current_user)
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    if creds:
        api_key, base_url = creds
        resolved_model = resolve_model_alias_for_volcengine(payload.model, icfg)
    else:
        api_key = icfg.volcengine_api_key
        base_url = icfg.volcengine_base_url.rstrip("/")
        resolved_model = resolve_model_alias_for_volcengine(payload.model, icfg)
    if not resolved_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择或填写模型",
        )
    if not api_key or not base_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM 未配置：请在用户设置中配置自建 API，或在设置中心填写火山集成配置",
        )

    prompt_text, style_text = resolve_prompt_and_style(
        current_user,
        payload.prompt_template.strip(),
        payload.style.strip(),
    )

    http_client = httpx.AsyncClient(timeout=120.0, trust_env=False)
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=http_client,
    )

    system_prompt = (
        "你是一名资深短视频脚本策划与编剧。\n"
        f"【提示词模板】{prompt_text}\n"
        f"【风格要求】{style_text}\n"
        "请输出结构清晰、可直接拍摄的中文内容。"
    )
    user_prompt = f"请围绕以下主题创作完整脚本：{payload.core_idea}"

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            stream = await client.chat.completions.create(
                model=resolved_model,
                stream=True,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            async for chunk in stream:
                delta = ""
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                if delta:
                    yield _sse({"type": "delta", "content": delta})
            yield _sse({"type": "done"})
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "404" in msg:
                msg = f"模型不可用或未开通（model={resolved_model}）: {msg}"
            yield _sse({"type": "error", "message": msg})
        finally:
            await http_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
