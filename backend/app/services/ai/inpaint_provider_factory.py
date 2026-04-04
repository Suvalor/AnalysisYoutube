"""
按运行时配置构造 Inpaint Provider 实例（可扩展多厂商）。

说明：OpenAI 兼容 images.edit 仍由 watermark_inpaint_client 单独封装，
此处仅产出继承 BaseInpaintProvider 的火山等实现，供统一编排。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.ai.base_inpaint_provider import BaseInpaintProvider
from app.services.ai.volc_inpaint_provider import VolcInpaintProvider

if TYPE_CHECKING:
    from app.services.watermark_inpaint_config import InpaintRuntimeConfig


def get_active_inpaint_providers(task_type: str, cfg: InpaintRuntimeConfig) -> list[BaseInpaintProvider]:
    """
    返回当前应尝试的 Provider 列表（按优先级排序）。

    :param task_type: 预留扩展，例如 "inpaint"
    """
    if task_type != "inpaint":
        return []
    providers: list[BaseInpaintProvider] = []
    if cfg.volc_cv is not None:
        providers.append(VolcInpaintProvider(cfg.volc_cv))
    return providers
