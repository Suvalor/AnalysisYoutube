from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.inspiration import (
    create_inspiration,
    delete_inspiration,
    get_inspiration,
    list_inspirations,
    update_inspiration,
)
from app.crud.sop import get_sop_script
from app.schemas.inspiration import (
    InspirationCreate,
    InspirationLinkPlotBody,
    InspirationRead,
    InspirationUpdate,
)


router = APIRouter()


@router.get("", response_model=list[InspirationRead])
async def list_inspirations_api(db: DBSessionDep, current_user: CurrentUserDep) -> list[InspirationRead]:
    rows = await list_inspirations(db, current_user.id)
    return [InspirationRead.model_validate(x) for x in rows]


@router.post("", response_model=InspirationRead, status_code=status.HTTP_201_CREATED)
async def create_inspiration_api(
    payload: InspirationCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    data = payload.model_dump()
    if data.get("recorded_at") is None:
        data["recorded_at"] = datetime.now(timezone.utc)
    row = await create_inspiration(db, current_user.id, data)
    await db.commit()
    return InspirationRead.model_validate(row)


@router.get("/{inspiration_id}", response_model=InspirationRead)
async def get_inspiration_api(
    inspiration_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    return InspirationRead.model_validate(row)


@router.put("/{inspiration_id}", response_model=InspirationRead)
async def update_inspiration_api(
    inspiration_id: int,
    payload: InspirationUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return InspirationRead.model_validate(row)
    row = await update_inspiration(db, row, patch)
    await db.commit()
    await db.refresh(row)
    return InspirationRead.model_validate(row)


@router.delete("/{inspiration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inspiration_api(
    inspiration_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> None:
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    await delete_inspiration(db, row)
    await db.commit()


@router.post("/{inspiration_id}/link-plot", response_model=InspirationRead)
async def link_inspiration_plot_api(
    inspiration_id: int,
    body: InspirationLinkPlotBody,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> InspirationRead:
    """将灵感标记为已生成剧情，并关联 sop_scripts 主键（plot_id）。"""
    row = await get_inspiration(db, current_user.id, inspiration_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="灵感不存在")
    script = await get_sop_script(db, current_user.id, body.plot_id)
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧情记录不存在或无权访问")
    row = await update_inspiration(
        db,
        row,
        {"plot_id": body.plot_id, "status": "已生成剧情"},
    )
    await db.commit()
    await db.refresh(row)
    return InspirationRead.model_validate(row)
