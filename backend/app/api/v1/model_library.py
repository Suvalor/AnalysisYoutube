import json

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, DBSessionDep
from app.crud.library import create_with_user, delete_with_user, ensure_owned_or_404, get_by_user, list_by_user, update_with_user
from app.models.library import ModelLibrary
from app.schemas.library import ModelCreate, ModelRead, ModelUpdate
from app.services.field_encryption import encrypt_plaintext


router = APIRouter()


def _validate_json_string(field_name: str, raw: str | None) -> None:
    if raw is None:
        return
    s = raw.strip()
    if not s:
        return
    try:
        json.loads(s)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} 必须是合法 JSON：{e}",
        ) from e


def _normalize_supported_models_json(raw: object) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        val = raw.strip()
        _validate_json_string("supported_models_json", val)
        return val or None
    if isinstance(raw, list):
        return json.dumps(raw, ensure_ascii=False)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="supported_models_json 必须是 JSON 字符串或列表",
    )


def _to_read(row: ModelLibrary) -> ModelRead:
    return ModelRead(
        id=row.id,
        user_id=row.user_id,
        library_kind=getattr(row, "library_kind", None) or "chat",
        name=row.name,
        api_base_url=row.api_base_url,
        supported_models_json=row.supported_models_json,
        has_api_key=bool(row.api_key_encrypted and row.api_key_encrypted.strip()),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[ModelRead])
async def list_models(db: DBSessionDep, current_user: CurrentUserDep) -> list[ModelRead]:
    rows = await list_by_user(db, ModelLibrary, current_user.id)
    return [_to_read(x) for x in rows]


@router.get("/{model_id}", response_model=ModelRead)
async def get_model(model_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> ModelRead:
    row = ensure_owned_or_404(await get_by_user(db, ModelLibrary, current_user.id, model_id))
    return _to_read(row)


@router.post("", response_model=ModelRead)
async def create_model(payload: ModelCreate, db: DBSessionDep, current_user: CurrentUserDep) -> ModelRead:
    kind = (payload.library_kind or "chat").strip()
    if kind not in {"chat", "image_inpaint"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="library_kind 仅支持 chat 或 image_inpaint")
    row = await create_with_user(
        db,
        ModelLibrary,
        current_user.id,
        {
            "name": payload.name.strip(),
            "library_kind": kind,
            "api_base_url": payload.api_base_url.strip(),
            "api_key_encrypted": encrypt_plaintext(payload.api_key.strip()) if payload.api_key and payload.api_key.strip() else None,
            "supported_models_json": _normalize_supported_models_json(payload.supported_models_json),
        },
    )
    return _to_read(row)


@router.put("/{model_id}", response_model=ModelRead)
async def update_model(
    model_id: int,
    payload: ModelUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> ModelRead:
    row = ensure_owned_or_404(await get_by_user(db, ModelLibrary, current_user.id, model_id))
    incoming = payload.model_dump(exclude_unset=True)
    patch: dict[str, str | None] = {}

    if "name" in incoming and incoming["name"] is not None:
        patch["name"] = str(incoming["name"]).strip()
    if "api_base_url" in incoming and incoming["api_base_url"] is not None:
        patch["api_base_url"] = str(incoming["api_base_url"]).strip()
    if "supported_models_json" in incoming:
        patch["supported_models_json"] = _normalize_supported_models_json(incoming["supported_models_json"])
    if "library_kind" in incoming and incoming["library_kind"] is not None:
        k = str(incoming["library_kind"]).strip()
        if k not in {"chat", "image_inpaint"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="library_kind 仅支持 chat 或 image_inpaint",
            )
        patch["library_kind"] = k
    if "api_key" in incoming:
        raw_key = incoming["api_key"]
        if raw_key is not None and str(raw_key).strip():
            patch["api_key_encrypted"] = encrypt_plaintext(str(raw_key).strip())

    row = await update_with_user(db, row, patch)
    return _to_read(row)


@router.delete("/{model_id}")
async def delete_model(model_id: int, db: DBSessionDep, current_user: CurrentUserDep) -> dict[str, str]:
    row = ensure_owned_or_404(await get_by_user(db, ModelLibrary, current_user.id, model_id))
    await delete_with_user(db, row)
    return {"message": "删除成功"}
