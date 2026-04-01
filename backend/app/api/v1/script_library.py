from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.library import create_with_user, ensure_owned_or_404, update_with_user
from app.models.library import ScriptLibrary
from app.schemas.library import ScriptCreate, ScriptRead, ScriptUpdate


router = APIRouter()


async def _list_scripts_by_deleted(
    db: DBSessionDep,
    user_id: int,
    *,
    is_deleted: bool,
) -> list[ScriptLibrary]:
    q = (
        select(ScriptLibrary)
        .where(
            ScriptLibrary.user_id == user_id,
            ScriptLibrary.is_deleted.is_(is_deleted),
        )
        .order_by(ScriptLibrary.id.desc())
    )
    res = await db.execute(q)
    return list(res.scalars().all())


async def _get_active_script(db: DBSessionDep, user_id: int, script_id: int) -> ScriptLibrary | None:
    q = select(ScriptLibrary).where(
        ScriptLibrary.id == script_id,
        ScriptLibrary.user_id == user_id,
        ScriptLibrary.is_deleted.is_(False),
    )
    res = await db.execute(q)
    return res.scalar_one_or_none()


@router.get("", response_model=list[ScriptRead])
async def list_scripts(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    include_deleted: bool = Query(False, description="是否返回回收站数据"),
) -> list[ScriptRead]:
    rows = await _list_scripts_by_deleted(db, current_user.id, is_deleted=include_deleted)
    return [ScriptRead.model_validate(x) for x in rows]


@router.get("/{script_id}", response_model=ScriptRead)
async def get_script(script_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> ScriptRead:
    row = ensure_owned_or_404(await _get_active_script(db, current_user.id, script_id))
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
    row = ensure_owned_or_404(await _get_active_script(db, current_user.id, script_id))
    row = await update_with_user(db, row, payload.model_dump(exclude_unset=True))
    return ScriptRead.model_validate(row)


@router.delete("/{script_id}")
async def delete_script(script_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = ensure_owned_or_404(await _get_active_script(db, current_user.id, script_id))
    row.is_deleted = True
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{script_id}/restore", response_model=ScriptRead)
async def restore_script(script_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> ScriptRead:
    q = select(ScriptLibrary).where(
        ScriptLibrary.id == script_id,
        ScriptLibrary.user_id == current_user.id,
        ScriptLibrary.is_deleted.is_(True),
    )
    res = await db.execute(q)
    row = ensure_owned_or_404(res.scalar_one_or_none(), "资源不存在")
    row.is_deleted = False
    row.deleted_at = None
    await db.commit()
    await db.refresh(row)
    return ScriptRead.model_validate(row)

