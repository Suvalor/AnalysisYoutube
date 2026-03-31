from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.library import create_with_user, delete_with_user, ensure_owned_or_404, get_by_user, list_by_user, update_with_user
from app.models.library import PromptLibrary
from app.schemas.library import PromptCreate, PromptRead, PromptUpdate


router = APIRouter()


@router.get("", response_model=list[PromptRead])
async def list_prompts(db: DBSessionDep, current_user: CurrentUserDep) -> list[PromptRead]:
    rows = await list_by_user(db, PromptLibrary, current_user.id)
    return [PromptRead.model_validate(x) for x in rows]


@router.get("/{prompt_id}", response_model=PromptRead)
async def get_prompt(prompt_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> PromptRead:
    row = ensure_owned_or_404(await get_by_user(db, PromptLibrary, current_user.id, prompt_id))
    return PromptRead.model_validate(row)


@router.post("", response_model=PromptRead)
async def create_prompt(payload: PromptCreate, db: DBSessionDep, current_user: CurrentUserDep) -> PromptRead:
    row = await create_with_user(db, PromptLibrary, current_user.id, payload.model_dump())
    return PromptRead.model_validate(row)


@router.put("/{prompt_id}", response_model=PromptRead)
async def update_prompt(
    prompt_id: int,
    payload: PromptUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> PromptRead:
    row = ensure_owned_or_404(await get_by_user(db, PromptLibrary, current_user.id, prompt_id))
    row = await update_with_user(db, row, payload.model_dump(exclude_unset=True))
    return PromptRead.model_validate(row)


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = ensure_owned_or_404(await get_by_user(db, PromptLibrary, current_user.id, prompt_id))
    await delete_with_user(db, row)
    return {"message": "删除成功"}

