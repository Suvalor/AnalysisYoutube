"""
火山引擎智能视觉 CV 20240606：Img2ImgInpainting（图像修补 / 智能抹除类能力）。

使用官方 volcengine-python-sdk 完成签名与请求，避免手写签名字段错误。
req_key、Region、Host 等由调用方配置注入（来自组织集成设置），禁止在代码中写死 AK/SK。
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

from app.services.ai.base_inpaint_provider import BaseInpaintProvider

if TYPE_CHECKING:
    from app.services.watermark_inpaint_config import VolcCvInpaintSlice

logger = logging.getLogger(__name__)


class VolcInpaintProvider(BaseInpaintProvider):
    """火山 CV Img2ImgInpainting：binary_data_base64 传入 [原图, Mask]。"""

    def __init__(self, cfg: VolcCvInpaintSlice) -> None:
        self._cfg = cfg
        self._api: Any = None

    def _ensure_api(self) -> None:
        if self._api is not None:
            return
        try:
            from volcenginesdkcore.api_client import ApiClient
            from volcenginesdkcore.configuration import Configuration
            from volcenginesdkcv20240606 import CV20240606Api
        except ImportError as exc:  # pragma: no cover - 运行环境未装 SDK
            raise RuntimeError(
                "未安装 volcengine-python-sdk，无法调用火山 CV 图像修补。请在后端环境执行："
                "pip install 'volcengine-python-sdk>=5.0.22'"
            ) from exc

        conf = Configuration()
        conf.ak = self._cfg.access_key_id.strip()
        conf.sk = self._cfg.secret_access_key.strip()
        conf.region = (self._cfg.region or "").strip() or "cn-north-1"
        host = (self._cfg.host or "").strip()
        if host:
            conf.host = host.removeprefix("https://").removeprefix("http://").split("/")[0]
        self._api = CV20240606Api(ApiClient(conf))

    @staticmethod
    def _response_ok(resp: Any) -> bool:
        code = getattr(resp, "code", None)
        if code is None:
            return False
        try:
            c = int(code)
        except (TypeError, ValueError):
            return False
        if c not in (0, 10000):
            return False
        data = getattr(resp, "data", None)
        if data is None:
            return False
        ab = getattr(data, "algorithm_base_resp", None)
        if ab is not None:
            sc = getattr(ab, "status_code", None)
            if sc is not None and int(sc) != 0:
                return False
        return True

    @staticmethod
    def _extract_image_b64_list(data: Any) -> list[str] | None:
        raw = getattr(data, "binary_data_base64", None)
        if isinstance(raw, list) and raw:
            return [str(x) for x in raw if x]
        return None

    def process(self, image_bytes: bytes, mask_bytes: bytes) -> bytes:
        import cv2
        import numpy as np
        from volcenginesdkcv20240606.models.img2_img_inpainting_request import Img2ImgInpaintingRequest
        from volcenginesdkcore.rest import ApiException

        self._ensure_api()

        img_arr = np.frombuffer(image_bytes, dtype=np.uint8)
        m_arr = np.frombuffer(mask_bytes, dtype=np.uint8)
        image_bgr = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        mask_u8 = cv2.imdecode(m_arr, cv2.IMREAD_GRAYSCALE)
        if image_bgr is None or mask_u8 is None:
            raise ValueError("无法解码输入的图像或 Mask（imdecode 失败）")
        if image_bgr.shape[:2] != mask_u8.shape[:2]:
            raise ValueError("图像与 Mask 尺寸不一致")

        ok_img, buf_img = cv2.imencode(".png", image_bgr)
        ok_mask, buf_mask = cv2.imencode(".png", mask_u8)
        if not ok_img or not ok_mask:
            raise ValueError("PNG 编码失败")

        img_b64 = base64.b64encode(buf_img.tobytes()).decode("ascii")
        mask_b64 = base64.b64encode(buf_mask.tobytes()).decode("ascii")

        # 与控制台 / OpenAPI 示例一致：binary_data_base64[0] 原图、[1] 待修复区域 Mask（白=修补区）
        body = Img2ImgInpaintingRequest(
            req_key=self._cfg.req_key.strip(),
            binary_data_base64=[img_b64, mask_b64],
            return_url=False,
        )

        try:
            resp = self._api.img2_img_inpainting(body)
        except ApiException as exc:
            status = getattr(exc, "status", None) or 0
            msg = (getattr(exc, "reason", None) or str(exc))[:800]
            logger.warning("火山 CV Inpaint HTTP/传输异常 status=%s %s", status, msg)
            raise RuntimeError(f"Volc Img2ImgInpaint 请求失败：status={status}") from exc

        if not self._response_ok(resp):
            c = getattr(resp, "code", None)
            m = (getattr(resp, "message", None) or "")[:500]
            rid = getattr(resp, "request_id", None)
            logger.warning("火山 CV Inpaint 业务失败 code=%s message=%s request_id=%s", c, m, rid)
            raise RuntimeError(f"Volc Img2ImgInpaint 返回失败：code={c} message={m}")

        data = resp.data
        b64_list = self._extract_image_b64_list(data)
        if not b64_list:
            raise RuntimeError("Volc Img2ImgInpaint 未返回 binary_data_base64")

        try:
            out = base64.b64decode(b64_list[0])
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("解码结果 Base64 失败") from exc
        if not out:
            raise RuntimeError("Volc Img2ImgInpaint 结果为空")
        return out
