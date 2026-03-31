from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.library import create_with_user, delete_with_user, ensure_owned_or_404, get_by_user, list_by_user, update_with_user
from app.models.library import ScriptLibrary
from app.schemas.library import ScriptCreate, ScriptRead, ScriptUpdate


router = APIRouter()


@router.get("", response_model=list[ScriptRead])
async def list_scripts(db: DBSessionDep, current_user: CurrentUserDep) -> list[ScriptRead]:
    rows = await list_by_user(db, ScriptLibrary, current_user.id)
    return [ScriptRead.model_validate(x) for x in rows]


@router.get("/{script_id}", response_model=ScriptRead)
async def get_script(script_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> ScriptRead:
    row = ensure_owned_or_404(await get_by_user(db, ScriptLibrary, current_user.id, script_id))
    return ScriptRead.model_validate(row)


@router.post("", response_model=ScriptRead)
async def create_script(payload: ScriptCreate, db: DBSessionDep, current_user: CurrentUserDep) -> ScriptRead:
    row = await create_with_user(db, ScriptLibrary, current_user.id, payload.model_dump())
    return ScriptRead.model_validate(row)


@router.put("/{script_id}", response_model=ScriptRead)
async def update_script(
    script_id: int,
    payload: ScriptUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ScriptRead:
    row = ensure_owned_or_404(await get_by_user(db, ScriptLibrary, current_user.id, script_id))
    row = await update_with_user(db, row, payload.model_dump(exclude_unset=True))
    return ScriptRead.model_validate(row)


@router.delete("/{script_id}")
async def delete_script(script_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = ensure_owned_or_404(await get_by_user(db, ScriptLibrary, current_user.id, script_id))
    await delete_with_user(db, row)
    return {"message": "删除成功"}

