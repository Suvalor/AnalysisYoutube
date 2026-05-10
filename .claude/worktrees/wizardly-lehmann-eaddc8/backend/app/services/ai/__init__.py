"""AI 能力抽象层：去水印图像修复等可插拔 Provider。"""

from app.services.ai.base_inpaint_provider import BaseInpaintProvider
from app.services.ai.inpaint_provider_factory import get_active_inpaint_providers
from app.services.ai.volc_inpaint_provider import VolcInpaintProvider

__all__ = ["BaseInpaintProvider", "VolcInpaintProvider", "get_active_inpaint_providers"]
