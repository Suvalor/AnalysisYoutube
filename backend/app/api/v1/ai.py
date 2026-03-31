import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from app.api.deps import CurrentUserDep, DBSessionDep
from app.core.config import settings
from app.crud.library import get_by_user
from app.models.library import PromptLibrary, StyleLibrary
from app.schemas.library import GenerateScriptStreamRequest


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

    if not settings.volcengine_api_key or not settings.volcengine_base_url or not settings.volcengine_endpoint_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="火山引擎配置不完整",
        )

    client = AsyncOpenAI(
        api_key=settings.volcengine_api_key,
        base_url=settings.volcengine_base_url,
    )
    system_prompt = (
        "你是一个专业的内容创作者。\n"
        f"【核心任务】: {prompt.content}\n"
        f"【文风与格式】: {style.content}"
    )
    user_message = f"请以【{payload.topic}】为主题创作。"

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            stream = await client.chat.completions.create(
                model=settings.volcengine_endpoint_id,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
            )
            async for chunk in stream:
                delta = ""
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                if delta:
                    yield _sse({"type": "delta", "content": delta})
            yield _sse({"type": "done"})
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

