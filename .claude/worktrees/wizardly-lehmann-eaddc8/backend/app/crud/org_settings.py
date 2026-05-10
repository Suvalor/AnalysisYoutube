from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_settings import OrgSettings


async def get_org_integration_payload_dict(session: AsyncSession, org_id: int) -> dict[str, str]:
    """读取组织已保存的集成配置；无记录或解析失败时返回空字典。"""
    result = await session.execute(select(OrgSettings).where(OrgSettings.org_id == org_id))
    row = result.scalar_one_or_none()
    if row is None or not (row.payload_json or "").strip():
        return {}
    try:
        data = json.loads(row.payload_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        if v is None:
            continue
        s = str(v).strip()
        if s:
            out[str(k)] = s
    return out


async def upsert_org_integration_payload(session: AsyncSession, org_id: int, payload: dict[str, str]) -> OrgSettings:
    result = await session.execute(select(OrgSettings).where(OrgSettings.org_id == org_id))
    row = result.scalar_one_or_none()
    body = json.dumps(payload, ensure_ascii=False)
    if row is None:
        row = OrgSettings(org_id=org_id, payload_json=body)
        session.add(row)
    else:
        row.payload_json = body
    await session.commit()
    await session.refresh(row)
    return row


async def delete_org_integration_settings(session: AsyncSession, org_id: int) -> bool:
    result = await session.execute(select(OrgSettings).where(OrgSettings.org_id == org_id))
    row = result.scalar_one_or_none()
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    return True
