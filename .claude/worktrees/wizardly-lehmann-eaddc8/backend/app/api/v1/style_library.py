from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.library import create_with_user, delete_with_user, ensure_owned_or_404, get_by_user, list_by_user, update_with_user
from app.models.library import StyleLibrary
from app.schemas.library import StyleCreate, StyleRead, StyleUpdate


router = APIRouter()


@router.get("", response_model=list[StyleRead])
async def list_styles(db: DBSessionDep, current_user: CurrentUserDep) -> list[StyleRead]:
    rows = await list_by_user(db, StyleLibrary, current_user.id)
    return [StyleRead.model_validate(x) for x in rows]


@router.get("/{style_id}", response_model=StyleRead)
async def get_style(style_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> StyleRead:
    row = ensure_owned_or_404(await get_by_user(db, StyleLibrary, current_user.id, style_id))
    return StyleRead.model_validate(row)


@router.post("", response_model=StyleRead)
async def create_style(payload: StyleCreate, db: DBSessionDep, current_user: CurrentUserDep) -> StyleRead:
    row = await create_with_user(db, StyleLibrary, current_user.id, payload.model_dump())
    return StyleRead.model_validate(row)


@router.put("/{style_id}", response_model=StyleRead)
async def update_style(
    style_id: int,
    payload: StyleUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> StyleRead:
    row = ensure_owned_or_404(await get_by_user(db, StyleLibrary, current_user.id, style_id))
    row = await update_with_user(db, row, payload.model_dump(exclude_unset=True))
    return StyleRead.model_validate(row)


@router.delete("/{style_id}")
async def delete_style(style_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = ensure_owned_or_404(await get_by_user(db, StyleLibrary, current_user.id, style_id))
    await delete_with_user(db, row)
    return {"message": "删除成功"}

