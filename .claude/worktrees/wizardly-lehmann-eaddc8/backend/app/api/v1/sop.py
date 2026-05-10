import asyncio
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException, Query
from fastapi import status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.sop import (
    create_sop_asset,
    create_sop_media,
    create_sop_script,
    create_sop_segment,
    create_sop_shot,
    get_sop_asset,
    get_sop_media,
    get_sop_script,
    get_sop_segment,
    get_sop_shot,
    list_sop_assets,
    list_sop_media,
    list_sop_scripts,
    list_sop_segments,
    list_sop_shots,
    soft_delete_sop_asset,
    soft_delete_sop_media,
    soft_delete_sop_script,
    soft_delete_sop_segment,
    soft_delete_sop_shot,
    update_sop_asset,
    update_sop_media,
    update_sop_script,
    update_sop_segment,
    update_sop_shot,
)
from app.crud.library import get_by_user
from app.models.library import PromptLibrary
from app.services.asset_access_service import sop_file_access_url
from app.services.config_manager import resolve_integration_config
from app.schemas.sop import (
    SopAssetCreate,
    SopAiSplitRequest,
    SopAiSplitStartRequest,
    SopAiSplitStartResponse,
    SopShotsFromSegmentsRequest,
    SopAssetRead,
    SopAssetUpdate,
    SopMediaCreate,
    SopMediaRead,
    SopMediaUpdate,
    SopScriptCreate,
    SopScriptRead,
    SopScriptUpdate,
    SopSegmentCreate,
    SopSegmentRead,
    SopSegmentUpdate,
    SopShotCreate,
    SopShotRead,
    SopShotUpdate,
)
from app.services.sop_ai_service import split_outline_markdown_with_ai_stream
from app.services.llm_conversation_service import (
    load_conversation_messages,
    save_conversation_turn,
)


router = APIRouter()


def _sop_asset_read_with_access(icfg, row) -> SopAssetRead:
    au = sop_file_access_url(
        storage_platform=row.storage_platform,
        storage_object_key=row.storage_object_key,
        file_url=row.file_url,
        cfg=icfg,
    )
    return SopAssetRead.model_validate(row).model_copy(update={"access_url": au})


def _sop_media_read_with_access(icfg, row) -> SopMediaRead:
    au = sop_file_access_url(
        storage_platform=row.storage_platform,
        storage_object_key=row.storage_object_key,
        file_url=row.file_url,
        cfg=icfg,
    )
    return SopMediaRead.model_validate(row).model_copy(update={"access_url": au})


@dataclass
class _AiSplitTaskState:
    user_id: int
    user_snapshot: dict
    outline_markdown: str
    model: str | None
    status: str = "queued"
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    chunks: list[str] = field(default_factory=list)
    error: str | None = None
    done: bool = False
    queue: asyncio.Queue[dict] = field(default_factory=asyncio.Queue)


_AI_SPLIT_TASKS: dict[str, _AiSplitTaskState] = {}
_AI_SPLIT_TASKS_LOCK = asyncio.Lock()
_AI_SPLIT_TASK_TTL_SECONDS = 30 * 60


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _cleanup_ai_split_tasks() -> None:
    now = time.time()
    async with _AI_SPLIT_TASKS_LOCK:
        expired = [
            task_id
            for task_id, state in _AI_SPLIT_TASKS.items()
            if now - state.updated_at > _AI_SPLIT_TASK_TTL_SECONDS
        ]
        for task_id in expired:
            _AI_SPLIT_TASKS.pop(task_id, None)


async def _run_ai_split_task(task_id: str) -> None:
    state = _AI_SPLIT_TASKS.get(task_id)
    if state is None:
        return
    state.status = "running"
    state.updated_at = time.time()
    await state.queue.put({"type": "status", "status": "running"})
    user_obj = SimpleNamespace(**state.user_snapshot)
    try:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            from app.models.user import User as UserModel

            u = await session.get(UserModel, state.user_id)
            oid = int(u.org_id) if u and u.org_id is not None else None
            icfg = await resolve_integration_config(session, org_id=oid)
        async for delta in split_outline_markdown_with_ai_stream(
            user=user_obj,
            outline_markdown=state.outline_markdown,
            model=state.model,
            integration=icfg,
        ):
            if not delta:
                continue
            state.chunks.append(delta)
            state.updated_at = time.time()
            await state.queue.put({"type": "delta", "content": delta})
        state.status = "done"
        state.done = True
        state.updated_at = time.time()
        await state.queue.put({"type": "done", "status": "done"})
    except Exception as exc:  # noqa: BLE001
        state.status = "failed"
        state.done = True
        state.error = str(exc)
        state.updated_at = time.time()
        await state.queue.put({"type": "error", "message": state.error})


@router.post("/segments/ai-split/start", response_model=SopAiSplitStartResponse)
async def ai_split_segments_start(
    payload: SopAiSplitStartRequest,
    current_user: CurrentUserDep,
) -> SopAiSplitStartResponse:
    await _cleanup_ai_split_tasks()
    task_id = uuid.uuid4().hex
    state = _AiSplitTaskState(
        user_id=current_user.id,
        user_snapshot={
            "id": current_user.id,
            "ai_api_base_url": current_user.ai_api_base_url,
            "ai_api_key_encrypted": current_user.ai_api_key_encrypted,
            "ai_models_json": current_user.ai_models_json,
        },
        outline_markdown=payload.outline_markdown.strip(),
        model=payload.model.strip() if payload.model else None,
    )
    async with _AI_SPLIT_TASKS_LOCK:
        _AI_SPLIT_TASKS[task_id] = state
    asyncio.create_task(_run_ai_split_task(task_id))
    return SopAiSplitStartResponse(task_id=task_id, status="queued")


@router.get("/segments/ai-split/stream/{task_id}")
async def ai_split_segments_stream(
    task_id: str,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    state = _AI_SPLIT_TASKS.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    if state.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限访问该任务")

    async def event_generator():
        # 已有累计内容先补发，支持断线重连时快速恢复。
        joined = "".join(state.chunks)
        if joined:
            yield _sse({"type": "snapshot", "content": joined, "status": state.status})
        if state.error:
            yield _sse({"type": "error", "message": state.error, "status": state.status})
            return
        if state.done:
            yield _sse({"type": "done", "status": state.status})
            return

        while True:
            try:
                event = await asyncio.wait_for(state.queue.get(), timeout=15.0)
                yield _sse(event)
                if event.get("type") in {"done", "error"}:
                    return
            except asyncio.TimeoutError:
                # 心跳防止网关空闲超时
                yield _sse({"type": "heartbeat", "status": state.status})
                if state.done:
                    return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/segments/ai-split")
async def ai_split_segments(
    payload: SopAiSplitRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    outline = payload.outline_markdown.strip()
    if not outline:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="outline_markdown 不能为空")

    selected_model: str | None = None
    selected_agent_prompt: str | None = None
    if payload.model_id is not None:
        selected_model = str(payload.model_id).strip() or None
    if payload.agent_id is not None:
        row = await get_by_user(db, PromptLibrary, current_user.id, payload.agent_id)
        if row is None:
            raise HTTPException(status_code=404, detail="智能体/提示词不存在")
        selected_agent_prompt = (row.content or "").strip() or None

    icfg = await resolve_integration_config(db, org_id=current_user.org_id)

    # 对话记忆
    entity_type = "sop_split"
    entity_id = f"outline:{hash(outline) & 0xFFFFFFFF}"
    history = await load_conversation_messages(
        db,
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    collected_deltas: list[str] = []

    async def event_generator():
        try:
            async for delta in split_outline_markdown_with_ai_stream(
                user=current_user,
                outline_markdown=outline,
                model=selected_model,
                agent_prompt=selected_agent_prompt,
                integration=icfg,
            ):
                if not delta:
                    continue
                collected_deltas.append(delta)
                yield _sse({"type": "delta", "text": delta})
            yield _sse({"type": "done", "conversation_id": f"{entity_type}:{entity_id}"})
            # 保存对话
            assistant_content = "".join(collected_deltas)
            try:
                await save_conversation_turn(
                    db,
                    user_id=current_user.id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    user_content=outline[:2000],
                    assistant_content=assistant_content,
                    model_name=selected_model,
                )
                await db.commit()
            except Exception:  # noqa: BLE001
                import logging as _logging
                _logging.getLogger(__name__).exception("保存 SOP 拆解对话历史失败")
                await db.rollback()
        except ValueError as exc:
            yield _sse({"type": "error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            import logging as _logging
            _logging.getLogger(__name__).exception("AI 拆解失败")
            yield _sse({"type": "error", "message": "AI 拆解服务异常，请稍后重试"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _parse_shot_blocks_from_segment(content: str) -> list[dict]:
    text = (content or "").strip()
    if not text:
        return []
    blocks = re.split(r"\n(?=###\s*镜头|\*\*镜头|##\s*片段)", text)
    out: list[dict] = []
    for idx, blk in enumerate([b.strip() for b in blocks if b.strip()], start=1):
        title_line = blk.splitlines()[0] if blk.splitlines() else f"镜头{idx}"
        shot_no_match = re.search(r"镜头\s*([0-9]+)", title_line)
        shot_no = int(shot_no_match.group(1)) if shot_no_match else idx
        dialogue = ""
        visual_prompt = blk
        duration_seconds = 3.5
        m_dialogue = re.search(r"\*\*(台词|对白)\*\*[:：]\s*(.+)", blk)
        if m_dialogue:
            dialogue = m_dialogue.group(2).strip()
        m_visual = re.search(r"\*\*画面内容\*\*[:：]\s*(.+)", blk)
        if m_visual:
            visual_prompt = m_visual.group(1).strip()
        m_duration = re.search(r"\*\*参考时长\*\*[:：]\s*([0-9]+(?:\.[0-9]+)?)", blk)
        if m_duration:
            duration_seconds = float(m_duration.group(1))
        out.append(
            {
                "shot_no": shot_no,
                "shot_type": "中景",
                "visual_prompt": visual_prompt,
                "dialogue": dialogue or None,
                "duration_seconds": duration_seconds,
                "status": "draft",
            }
        )
    if out:
        return out
    paras = [x.strip() for x in re.split(r"\n{2,}", text) if x.strip()]
    return [
        {
            "shot_no": i + 1,
            "shot_type": "中景",
            "visual_prompt": p,
            "dialogue": None,
            "duration_seconds": 3.5,
            "status": "draft",
        }
        for i, p in enumerate(paras[:6])
    ]


@router.post("/shots/from-segments", response_model=list[SopShotRead])
async def create_shots_from_segments(
    payload: SopShotsFromSegmentsRequest,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> list[SopShotRead]:
    script = await get_sop_script(db, current_user.id, payload.script_id)
    if script is None:
        raise HTTPException(status_code=404, detail="剧本不存在")
    segs = await list_sop_segments(db, current_user.id, payload.script_id)
    segs = sorted(segs, key=lambda x: x.segment_no)
    if not segs:
        return []

    if payload.replace_existing:
        for seg in segs:
            olds = await list_sop_shots(db, current_user.id, seg.id)
            for old in olds:
                await soft_delete_sop_shot(db, old)

    created: list[SopShotRead] = []
    for seg in segs:
        blocks = _parse_shot_blocks_from_segment(seg.content)
        for blk in blocks:
            row = await create_sop_shot(db, {"segment_id": seg.id, **blk})
            created.append(SopShotRead.model_validate(row))
    return created


@router.get("/scripts", response_model=list[SopScriptRead])
async def list_scripts(db: DBSessionDep, current_user: CurrentUserDep) -> list[SopScriptRead]:
    rows = await list_sop_scripts(db, current_user.id)
    return [SopScriptRead.model_validate(x) for x in rows]


@router.post("/scripts", response_model=SopScriptRead)
async def create_script(payload: SopScriptCreate, db: DBSessionDep, current_user: CurrentUserDep) -> SopScriptRead:
    row = await create_sop_script(db, current_user.id, payload.model_dump())
    return SopScriptRead.model_validate(row)


@router.get("/scripts/{script_id}", response_model=SopScriptRead)
async def get_script(script_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> SopScriptRead:
    row = await get_sop_script(db, current_user.id, script_id)
    if row is None:
        raise HTTPException(status_code=404, detail="剧本不存在")
    return SopScriptRead.model_validate(row)


@router.put("/scripts/{script_id}", response_model=SopScriptRead)
async def update_script(
    script_id: int,
    payload: SopScriptUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SopScriptRead:
    row = await get_sop_script(db, current_user.id, script_id)
    if row is None:
        raise HTTPException(status_code=404, detail="剧本不存在")
    row = await update_sop_script(db, row, payload.model_dump(exclude_unset=True))
    return SopScriptRead.model_validate(row)


@router.delete("/scripts/{script_id}")
async def delete_script(script_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = await get_sop_script(db, current_user.id, script_id)
    if row is None:
        raise HTTPException(status_code=404, detail="剧本不存在")
    await soft_delete_sop_script(db, row)
    return {"message": "删除成功"}


@router.get("/segments", response_model=list[SopSegmentRead])
async def list_segments(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    script_id: int | None = Query(None),
) -> list[SopSegmentRead]:
    rows = await list_sop_segments(db, current_user.id, script_id)
    return [SopSegmentRead.model_validate(x) for x in rows]


@router.post("/segments", response_model=SopSegmentRead)
async def create_segment(payload: SopSegmentCreate, db: DBSessionDep, current_user: CurrentUserDep) -> SopSegmentRead:
    script = await get_sop_script(db, current_user.id, payload.script_id)
    if script is None:
        raise HTTPException(status_code=404, detail="所属剧本不存在")
    row = await create_sop_segment(db, payload.model_dump())
    return SopSegmentRead.model_validate(row)


@router.get("/segments/{segment_id}", response_model=SopSegmentRead)
async def get_segment(segment_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> SopSegmentRead:
    row = await get_sop_segment(db, current_user.id, segment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="片段不存在")
    return SopSegmentRead.model_validate(row)


@router.put("/segments/{segment_id}", response_model=SopSegmentRead)
async def update_segment(
    segment_id: int,
    payload: SopSegmentUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SopSegmentRead:
    row = await get_sop_segment(db, current_user.id, segment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="片段不存在")
    row = await update_sop_segment(db, row, payload.model_dump(exclude_unset=True))
    return SopSegmentRead.model_validate(row)


@router.delete("/segments/{segment_id}")
async def delete_segment(segment_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = await get_sop_segment(db, current_user.id, segment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="片段不存在")
    await soft_delete_sop_segment(db, row)
    return {"message": "删除成功"}


@router.get("/shots", response_model=list[SopShotRead])
async def list_shots(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    segment_id: int | None = Query(None),
) -> list[SopShotRead]:
    rows = await list_sop_shots(db, current_user.id, segment_id)
    return [SopShotRead.model_validate(x) for x in rows]


@router.post("/shots", response_model=SopShotRead)
async def create_shot(payload: SopShotCreate, db: DBSessionDep, current_user: CurrentUserDep) -> SopShotRead:
    segment = await get_sop_segment(db, current_user.id, payload.segment_id)
    if segment is None:
        raise HTTPException(status_code=404, detail="所属片段不存在")
    row = await create_sop_shot(db, payload.model_dump())
    return SopShotRead.model_validate(row)


@router.get("/shots/{shot_id}", response_model=SopShotRead)
async def get_shot(shot_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> SopShotRead:
    row = await get_sop_shot(db, current_user.id, shot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="分镜不存在")
    return SopShotRead.model_validate(row)


@router.put("/shots/{shot_id}", response_model=SopShotRead)
async def update_shot(
    shot_id: int,
    payload: SopShotUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SopShotRead:
    row = await get_sop_shot(db, current_user.id, shot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="分镜不存在")
    row = await update_sop_shot(db, row, payload.model_dump(exclude_unset=True))
    return SopShotRead.model_validate(row)


@router.delete("/shots/{shot_id}")
async def delete_shot(shot_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = await get_sop_shot(db, current_user.id, shot_id)
    if row is None:
        raise HTTPException(status_code=404, detail="分镜不存在")
    await soft_delete_sop_shot(db, row)
    return {"message": "删除成功"}


@router.get("/assets", response_model=list[SopAssetRead])
async def list_assets(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    shot_id: int | None = Query(None),
) -> list[SopAssetRead]:
    rows = await list_sop_assets(db, current_user.id, shot_id)
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return [_sop_asset_read_with_access(icfg, x) for x in rows]


@router.post("/assets", response_model=SopAssetRead)
async def create_asset(payload: SopAssetCreate, db: DBSessionDep, current_user: CurrentUserDep) -> SopAssetRead:
    shot = await get_sop_shot(db, current_user.id, payload.shot_id)
    if shot is None:
        raise HTTPException(status_code=404, detail="所属分镜不存在")
    if payload.source_asset_id:
        source = await get_sop_asset(db, current_user.id, payload.source_asset_id)
        if source is None:
            raise HTTPException(status_code=404, detail="source_asset_id 对应资产不存在")
    row = await create_sop_asset(db, payload.model_dump())
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return _sop_asset_read_with_access(icfg, row)


@router.get("/assets/{asset_id}", response_model=SopAssetRead)
async def get_asset(asset_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> SopAssetRead:
    row = await get_sop_asset(db, current_user.id, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return _sop_asset_read_with_access(icfg, row)


@router.put("/assets/{asset_id}", response_model=SopAssetRead)
async def update_asset(
    asset_id: int,
    payload: SopAssetUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SopAssetRead:
    row = await get_sop_asset(db, current_user.id, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "source_asset_id" in updates and updates["source_asset_id"]:
        source = await get_sop_asset(db, current_user.id, int(updates["source_asset_id"]))
        if source is None:
            raise HTTPException(status_code=404, detail="source_asset_id 对应资产不存在")
    row = await update_sop_asset(db, row, updates)
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return _sop_asset_read_with_access(icfg, row)


@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = await get_sop_asset(db, current_user.id, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    await soft_delete_sop_asset(db, row)
    return {"message": "删除成功"}


@router.get("/media", response_model=list[SopMediaRead])
async def list_media(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    shot_id: int | None = Query(None),
) -> list[SopMediaRead]:
    rows = await list_sop_media(db, current_user.id, shot_id)
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return [_sop_media_read_with_access(icfg, x) for x in rows]


@router.post("/media", response_model=SopMediaRead)
async def create_media(payload: SopMediaCreate, db: DBSessionDep, current_user: CurrentUserDep) -> SopMediaRead:
    shot = await get_sop_shot(db, current_user.id, payload.shot_id)
    if shot is None:
        raise HTTPException(status_code=404, detail="所属分镜不存在")
    row = await create_sop_media(db, payload.model_dump())
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return _sop_media_read_with_access(icfg, row)


@router.get("/media/{media_id}", response_model=SopMediaRead)
async def get_media(media_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> SopMediaRead:
    row = await get_sop_media(db, current_user.id, media_id)
    if row is None:
        raise HTTPException(status_code=404, detail="媒体不存在")
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return _sop_media_read_with_access(icfg, row)


@router.put("/media/{media_id}", response_model=SopMediaRead)
async def update_media(
    media_id: int,
    payload: SopMediaUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> SopMediaRead:
    row = await get_sop_media(db, current_user.id, media_id)
    if row is None:
        raise HTTPException(status_code=404, detail="媒体不存在")
    row = await update_sop_media(db, row, payload.model_dump(exclude_unset=True))
    icfg = await resolve_integration_config(db, org_id=current_user.org_id)
    return _sop_media_read_with_access(icfg, row)


@router.delete("/media/{media_id}")
async def delete_media(media_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = await get_sop_media(db, current_user.id, media_id)
    if row is None:
        raise HTTPException(status_code=404, detail="媒体不存在")
    await soft_delete_sop_media(db, row)
    return {"message": "删除成功"}
