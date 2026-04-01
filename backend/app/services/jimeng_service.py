from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


def _auth_header_value() -> str:
    token = settings.jimeng_auth_token or settings.jimeng_api_key
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缺少既梦鉴权配置，请设置 JIMENG_AUTH_TOKEN 或 JIMENG_API_KEY",
        )
    return f"Bearer {token}"


def _extract_task_id(payload: dict[str, Any]) -> str | None:
    candidates = [
        payload.get("task_id"),
        payload.get("id"),
        payload.get("data", {}).get("task_id") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("id") if isinstance(payload.get("data"), dict) else None,
    ]
    for value in candidates:
        if value:
            return str(value)
    return None


async def submit_task(
    *,
    model_name: str,
    prompt: str,
    negative_prompt: str | None,
    params: dict[str, Any],
) -> dict[str, Any]:
    if not settings.jimeng_api_base_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缺少 JIMENG_API_BASE_URL 配置",
        )

    body: dict[str, Any] = {
        "model_name": model_name,
        "prompt": prompt,
        **params,
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.jimeng_api_base_url.rstrip('/')}{settings.jimeng_submit_path}",
                json=body,
                headers={
                    "Authorization": _auth_header_value(),
                    "Content-Type": "application/json",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"请求既梦提交任务失败: {exc}",
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"既梦提交任务失败: {resp.status_code} {resp.text}",
        )

    data = resp.json()
    task_id = _extract_task_id(data)
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"既梦返回缺少 task_id，响应: {data}",
        )
    return {"task_id": task_id, "raw": data}


async def query_task_status(task_id: str) -> dict[str, Any]:
    if not settings.jimeng_api_base_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缺少 JIMENG_API_BASE_URL 配置",
        )

    query_path = settings.jimeng_status_path_template.format(task_id=task_id)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{settings.jimeng_api_base_url.rstrip('/')}{query_path}",
                headers={"Authorization": _auth_header_value()},
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"请求既梦查询任务失败: {exc}",
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"既梦查询任务失败: {resp.status_code} {resp.text}",
        )

    data = resp.json()
    status_value = (
        data.get("status")
        or data.get("task_status")
        or (data.get("data", {}).get("status") if isinstance(data.get("data"), dict) else None)
        or "unknown"
    )
    result_value = data.get("result")
    if result_value is None and isinstance(data.get("data"), dict):
        result_value = data["data"].get("result")

    return {
        "task_id": task_id,
        "status": str(status_value),
        "result": result_value,
        "raw": data,
    }
