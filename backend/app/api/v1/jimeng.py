from fastapi import APIRouter

from app.api.deps import CurrentUserDep
from app.schemas.jimeng import JimengGenerateRequest, JimengTaskStatusResponse, JimengTaskSubmitResponse
from app.services.jimeng_service import query_task_status, submit_task


router = APIRouter()


@router.post("/generate", response_model=JimengTaskSubmitResponse)
async def generate_asset_with_jimeng(
    payload: JimengGenerateRequest,
    _: CurrentUserDep,
) -> JimengTaskSubmitResponse:
    params: dict[str, object] = {}
    if payload.width is not None:
        params["width"] = payload.width
    if payload.height is not None:
        params["height"] = payload.height
    if payload.ratio:
        params["ratio"] = payload.ratio
    if payload.extra:
        params.update(payload.extra)

    data = await submit_task(
        model_name=payload.model_name,
        prompt=payload.prompt,
        negative_prompt=payload.negative_prompt,
        params=params,
    )
    return JimengTaskSubmitResponse.model_validate(data)


@router.get("/status/{task_id}", response_model=JimengTaskStatusResponse)
async def get_jimeng_task_status(
    task_id: str,
    _: CurrentUserDep,
) -> JimengTaskStatusResponse:
    data = await query_task_status(task_id)
    return JimengTaskStatusResponse.model_validate(data)
