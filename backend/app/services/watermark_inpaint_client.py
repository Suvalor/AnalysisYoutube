"""
去水印云端图像修复：优先火山智能视觉 CV（Img2ImgInpainting），其次 OpenAI 兼容 images.edit。

不依赖 openai SDK；火山侧使用 volcengine-python-sdk 完成签名。
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any

import httpx
import numpy as np
from PIL import Image

from app.services.ai.volc_inpaint_provider import VolcInpaintProvider
from app.services.watermark_inpaint_config import (
    InpaintRuntimeConfig,
    OpenAIInpaintSlice,
    VolcCvInpaintSlice,
)

logger = logging.getLogger(__name__)

# 日志标记：曾尝试云端 Inpaint 后回退 OpenCV 时，业务方可据此检索
AI_FAILED_FALLBACK_TO_OPENCV = "AI_FAILED_FALLBACK_TO_OPENCV"

# 火山视觉常见请求体大小/边长限制（保守值）
_VOLC_MAX_SIDE_PX = 4096


def blend_patch_with_gaussian_feather(
    frame_bgr: np.ndarray,
    x: int,
    y: int,
    patch_bgr: np.ndarray,
    feather: int,
) -> None:
    """将 patch 以高斯羽化边缘贴回 frame（就地修改）。"""
    import cv2

    h, w = patch_bgr.shape[:2]
    if y + h > frame_bgr.shape[0] or x + w > frame_bgr.shape[1] or y < 0 or x < 0:
        return
    roi = frame_bgr[y : y + h, x : x + w]
    ph, pw = roi.shape[:2]
    p = patch_bgr
    if p.shape[0] != ph or p.shape[1] != pw:
        p = cv2.resize(p, (pw, ph))
    k = max(3, feather * 2 + 1)
    if k % 2 == 0:
        k += 1
    weight = cv2.GaussianBlur(np.ones((ph, pw), np.float32), (k, k), 0)[..., None]
    roi[:] = np.clip(
        weight * p.astype(np.float32) + (1.0 - weight) * roi.astype(np.float32),
        0,
        255,
    ).astype(np.uint8)


def _mask_bbox(mask_u8: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask_u8 > 127)
    if ys.size == 0:
        return None
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    return x0, y0, x1, y1


def _choose_edit_side(max_hw: int) -> int:
    if max_hw <= 256:
        return 256
    if max_hw <= 512:
        return 512
    return 1024


def _letterbox_to_square(
    bgr: np.ndarray,
    mask: np.ndarray,
    side: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    import cv2

    h, w = bgr.shape[:2]
    scale = side / max(h, w)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    rb = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    rm = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_NEAREST)
    canvas_b = np.full((side, side, 3), 114, dtype=np.uint8)
    canvas_m = np.zeros((side, side), dtype=np.uint8)
    x0 = (side - nw) // 2
    y0 = (side - nh) // 2
    canvas_b[y0 : y0 + nh, x0 : x0 + nw] = rb
    canvas_m[y0 : y0 + nh, x0 : x0 + nw] = rm
    meta = {
        "side": side,
        "x0": x0,
        "y0": y0,
        "nw": nw,
        "nh": nh,
        "orig_h": h,
        "orig_w": w,
    }
    return canvas_b, canvas_m, meta


def _images_edit_url(api_base_url: str) -> str:
    b = (api_base_url or "").strip().rstrip("/")
    if b.lower().endswith("/v1"):
        return f"{b}/images/edits"
    return f"{b}/v1/images/edits"


def _volc_inpaint_full_bgr_or_none(
    image_bgr: np.ndarray,
    mask_u8: np.ndarray,
    volc_slice: VolcCvInpaintSlice,
) -> np.ndarray | None:
    """整图 + 整幅 Mask 调用火山 CV；必要时缩小请求，结果放大回原分辨率。"""
    import cv2

    orig_h, orig_w = image_bgr.shape[:2]
    work_b = image_bgr
    work_m = mask_u8
    side = max(orig_h, orig_w)
    if side > _VOLC_MAX_SIDE_PX:
        scale = _VOLC_MAX_SIDE_PX / float(side)
        nw = max(1, int(round(orig_w * scale)))
        nh = max(1, int(round(orig_h * scale)))
        work_b = cv2.resize(image_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
        work_m = cv2.resize(mask_u8, (nw, nh), interpolation=cv2.INTER_NEAREST)
        logger.info(
            "火山 CV Inpaint：原图长边 %s 超过 %s，请求前缩放为 %sx%s",
            side,
            _VOLC_MAX_SIDE_PX,
            nw,
            nh,
        )

    ok_i, buf_i = cv2.imencode(".png", work_b)
    ok_m, buf_m = cv2.imencode(".png", work_m)
    if not ok_i or not ok_m:
        logger.warning("火山 CV Inpaint：PNG 编码失败")
        return None

    provider = VolcInpaintProvider(volc_slice)
    try:
        out_bytes = provider.process(buf_i.tobytes(), buf_m.tobytes())
    except Exception:
        logger.warning("火山 CV Inpaint 调用异常（将尝试其他通道或本地修复）", exc_info=True)
        return None

    raw = np.frombuffer(out_bytes, dtype=np.uint8)
    out = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if out is None:
        logger.warning("火山 CV Inpaint：无法解码返回图像")
        return None

    if out.shape[:2] != work_b.shape[:2]:
        out = cv2.resize(out, (work_b.shape[1], work_b.shape[0]), interpolation=cv2.INTER_LINEAR)

    if out.shape[0] != orig_h or out.shape[1] != orig_w:
        out = cv2.resize(out, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)
    return out


def _openai_inpaint_bgr_or_none(
    image_bgr: np.ndarray,
    mask_u8: np.ndarray,
    slice_cfg: OpenAIInpaintSlice,
) -> np.ndarray | None:
    import cv2

    bbox = _mask_bbox(mask_u8)
    if bbox is None:
        return image_bgr.copy()

    x0, y0, x1, y1 = bbox
    pad = max(8, (x1 - x0 + y1 - y0) // 40)
    H, W = image_bgr.shape[:2]
    bx0 = max(0, x0 - pad)
    by0 = max(0, y0 - pad)
    bx1 = min(W, x1 + pad + 1)
    by1 = min(H, y1 + pad + 1)
    crop = image_bgr[by0:by1, bx0:bx1].copy()
    crop_mask = mask_u8[by0:by1, bx0:bx1].copy()
    ch, cw = crop.shape[:2]
    side = _choose_edit_side(max(ch, cw))
    square_b, square_m, meta = _letterbox_to_square(crop, crop_mask, side)

    rgb_square = cv2.cvtColor(square_b, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_square)
    buf_img = io.BytesIO()
    pil_image.save(buf_img, format="PNG")

    h_s, w_s = square_m.shape
    edit = square_m > 127
    rgba_m = np.zeros((h_s, w_s, 4), dtype=np.uint8)
    rgba_m[:, :, 3] = np.where(edit, 0, 255).astype(np.uint8)
    pil_mask = Image.fromarray(rgba_m, mode="RGBA")
    buf_mask = io.BytesIO()
    pil_mask.save(buf_mask, format="PNG")

    url = _images_edit_url(slice_cfg.api_base_url)
    files = {
        "image": ("image.png", buf_img.getvalue(), "image/png"),
        "mask": ("mask.png", buf_mask.getvalue(), "image/png"),
    }
    data = {
        "model": slice_cfg.model_id,
        "prompt": slice_cfg.prompt,
        "n": "1",
        "size": f"{side}x{side}",
        "response_format": "b64_json",
    }

    try:
        with httpx.Client(timeout=180.0, trust_env=False) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {slice_cfg.api_key}"},
                files=files,
                data=data,
            )
    except Exception:
        logger.warning("images.edit 网络请求失败，将回退本地修复", exc_info=True)
        return None

    if resp.status_code == 429:
        logger.warning("images.edit 限流 HTTP 429：%s", (resp.text or "")[:500])
        return None
    if resp.status_code >= 400:
        logger.warning("images.edit HTTP %s：%s", resp.status_code, (resp.text or "")[:500])
        return None

    try:
        payload = resp.json()
    except json.JSONDecodeError:
        return None

    b64 = None
    arr = payload.get("data")
    if isinstance(arr, list) and arr:
        first = arr[0]
        if isinstance(first, dict):
            b64 = first.get("b64_json") or first.get("b64")
    if not b64:
        return None

    try:
        raw = base64.b64decode(b64)
        pil_r = Image.open(io.BytesIO(raw)).convert("RGB")
        out_arr = np.array(pil_r)
        out_canvas = cv2.cvtColor(out_arr, cv2.COLOR_RGB2BGR)
    except Exception:
        logger.warning("解码 images.edit 返回失败", exc_info=True)
        return None

    y0l, x0l, nw, nh = meta["y0"], meta["x0"], meta["nw"], meta["nh"]
    inner = out_canvas[y0l : y0l + nh, x0l : x0l + nw]
    if inner.size == 0:
        return None
    restored = cv2.resize(inner, (cw, ch), interpolation=cv2.INTER_AREA)

    out_full = image_bgr.copy()
    roi = out_full[by0:by1, bx0:bx1]
    cm = crop_mask > 127
    if cm.any():
        blended = roi.copy()
        blended[cm] = restored[cm]
        k = 3
        border = cv2.dilate(cm.astype(np.uint8) * 255, np.ones((k, k), np.uint8), iterations=1) - (
            cm.astype(np.uint8) * 255
        )
        if border.any():
            soft = cv2.GaussianBlur(blended, (5, 5), 0)
            bmask = border.astype(bool)
            blended[bmask] = soft[bmask]
        roi[:] = blended
    else:
        roi[:] = restored
    return out_full


def inpaint_bgr_with_runtime_config_or_none(
    image_bgr: np.ndarray,
    mask_u8: np.ndarray,
    config: InpaintRuntimeConfig,
) -> np.ndarray | None:
    """
    按配置依次尝试：火山 CV Inpaint → OpenAI 兼容 images.edit；均失败返回 None。
    """
    if image_bgr.shape[:2] != mask_u8.shape[:2]:
        logger.warning("Inpaint：图像与 mask 尺寸不一致")
        return None

    bbox = _mask_bbox(mask_u8)
    if bbox is None:
        return image_bgr.copy()

    if config.volc_cv is not None:
        volc_out = _volc_inpaint_full_bgr_or_none(image_bgr, mask_u8, config.volc_cv)
        if volc_out is not None:
            return volc_out

    if config.openai is not None:
        return _openai_inpaint_bgr_or_none(image_bgr, mask_u8, config.openai)

    return None
