from fastapi import APIRouter

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.library import create_with_user, delete_with_user, ensure_owned_or_404, get_by_user, list_by_user, update_with_user
from app.models.library import AssetLibrary
from app.schemas.library import AssetCreate, AssetRead, AssetUpdate


router = APIRouter()


@router.get("", response_model=list[AssetRead])
async def list_assets(db: DBSessionDep, current_user: CurrentUserDep) -> list[AssetRead]:
    rows = await list_by_user(db, AssetLibrary, current_user.id)
    return [AssetRead.model_validate(x) for x in rows]


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> AssetRead:
    row = ensure_owned_or_404(await get_by_user(db, AssetLibrary, current_user.id, asset_id))
    return AssetRead.model_validate(row)


@router.post("", response_model=AssetRead)
async def create_asset(payload: AssetCreate, db: DBSessionDep, current_user: CurrentUserDep) -> AssetRead:
    row = await create_with_user(db, AssetLibrary, current_user.id, payload.model_dump())
    return AssetRead.model_validate(row)


@router.put("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> AssetRead:
    row = ensure_owned_or_404(await get_by_user(db, AssetLibrary, current_user.id, asset_id))
    row = await update_with_user(db, row, payload.model_dump(exclude_unset=True))
    return AssetRead.model_validate(row)


@router.delete("/{asset_id}")
async def delete_asset(asset_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = ensure_owned_or_404(await get_by_user(db, AssetLibrary, current_user.id, asset_id))
    await delete_with_user(db, row)
    return {"message": "删除成功"}

