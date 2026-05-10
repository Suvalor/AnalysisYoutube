"""
即梦 AI 图片生成服务。

配置不再从静态环境变量读取，改为通过 model_libraries 表（library_kind=jimeng）
由调用方传入 api_key / api_base_url 等参数。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException, status


JIMENG_SUBMIT_PATH = "/v1/tasks"
JIMENG_STATUS_PATH_TEMPLATE = "/v1/tasks/{task_id}"


@dataclass(frozen=True)
class JimengConfig:
    """即梦 AI 运行时配置，由调用方从 model_libraries 解析后传入。"""

    api_key: str
    api_base_url: str


def _auth_header_value(cfg: JimengConfig) -> str:
    token = (cfg.api_key or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缺少即梦鉴权配置，请在智能体管理中配置即梦 API Key",
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
    cfg: JimengConfig,
    model_name: str,
    prompt: str,
    negative_prompt: str | None,
    params: dict[str, Any],
) -> dict[str, Any]:
    if not cfg.api_base_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缺少即梦 API Base URL，请在智能体管理中配置",
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
                f"{cfg.api_base_url.rstrip('/')}{JIMENG_SUBMIT_PATH}",
                json=body,
                headers={
                    "Authorization": _auth_header_value(cfg),
                    "Content-Type": "application/json",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"请求即梦提交任务失败: {exc}",
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"即梦提交任务失败: {resp.status_code} {resp.text}",
        )

    data = resp.json()
    task_id = _extract_task_id(data)
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"即梦返回缺少 task_id，响应: {data}",
        )
    return {"task_id": task_id, "raw": data}


async def query_task_status(
    *,
    cfg: JimengConfig,
    task_id: str,
) -> dict[str, Any]:
    if not cfg.api_base_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缺少即梦 API Base URL，请在智能体管理中配置",
        )

    query_path = JIMENG_STATUS_PATH_TEMPLATE.format(task_id=task_id)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{cfg.api_base_url.rstrip('/')}{query_path}",
                headers={"Authorization": _auth_header_value(cfg)},
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"请求即梦查询任务失败: {exc}",
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"即梦查询任务失败: {resp.status_code} {resp.text}",
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
