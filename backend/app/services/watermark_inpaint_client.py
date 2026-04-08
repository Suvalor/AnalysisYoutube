"""去水印云端图像修复：优先火山 CV，其次 OpenAI 兼容 images.edit。"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any

import httpx
import numpy as np
from PIL import Image, ImageFilter

from app.services.ai.volc_inpaint_provider import VolcInpaintProvider
from app.services.watermark_inpaint_config import (
    InpaintRuntimeConfig,
    OpenAIInpaintSlice,
    VolcCvInpaintSlice,
)

logger = logging.getLogger(__name__)

# 日志标记：曾尝试云端 Inpaint 但失败
AI_INPAINT_FAILED = "AI_INPAINT_FAILED"

# 火山视觉常见请求体大小/边长限制（保守值）
_VOLC_MAX_SIDE_PX = 4096


def _resize_rgb(rgb: np.ndarray, width: int, height: int) -> np.ndarray:
    pil = Image.fromarray(rgb, mode="RGB")
    resized = pil.resize((width, height), Image.Resampling.BILINEAR)
    return np.array(resized)


def _resize_mask(mask: np.ndarray, width: int, height: int) -> np.ndarray:
    pil = Image.fromarray(mask, mode="L")
    resized = pil.resize((width, height), Image.Resampling.NEAREST)
    return np.array(resized)


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
    rgb: np.ndarray,
    mask: np.ndarray,
    side: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    h, w = rgb.shape[:2]
    scale = side / max(h, w)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    rb = _resize_rgb(rgb, nw, nh)
    rm = _resize_mask(mask, nw, nh)
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
    orig_h, orig_w = image_bgr.shape[:2]
    work_b = image_bgr[:, :, ::-1].copy()
    work_m = mask_u8
    side = max(orig_h, orig_w)
    if side > _VOLC_MAX_SIDE_PX:
        scale = _VOLC_MAX_SIDE_PX / float(side)
        nw = max(1, int(round(orig_w * scale)))
        nh = max(1, int(round(orig_h * scale)))
        work_b = _resize_rgb(work_b, nw, nh)
        work_m = _resize_mask(mask_u8, nw, nh)
        logger.info(
            "火山 CV Inpaint：原图长边 %s 超过 %s，请求前缩放为 %sx%s",
            side,
            _VOLC_MAX_SIDE_PX,
            nw,
            nh,
        )

    buf_i = io.BytesIO()
    buf_m = io.BytesIO()
    Image.fromarray(work_b, mode="RGB").save(buf_i, format="PNG")
    Image.fromarray(work_m, mode="L").save(buf_m, format="PNG")

    provider = VolcInpaintProvider(volc_slice)
    try:
        out_bytes = provider.process(buf_i.getvalue(), buf_m.getvalue())
    except Exception:
        logger.warning("火山 CV Inpaint 调用异常（将尝试其他通道）", exc_info=True)
        return None

    try:
        out_rgb = np.array(Image.open(io.BytesIO(out_bytes)).convert("RGB"))
    except Exception:
        logger.warning("火山 CV Inpaint：无法解码返回图像")
        return None

    if out_rgb.shape[:2] != work_b.shape[:2]:
        out_rgb = _resize_rgb(out_rgb, work_b.shape[1], work_b.shape[0])

    if out_rgb.shape[0] != orig_h or out_rgb.shape[1] != orig_w:
        out_rgb = _resize_rgb(out_rgb, orig_w, orig_h)
    return out_rgb[:, :, ::-1].copy()


def _openai_inpaint_bgr_or_none(
    image_bgr: np.ndarray,
    mask_u8: np.ndarray,
    slice_cfg: OpenAIInpaintSlice,
) -> np.ndarray | None:
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
    crop_bgr = image_bgr[by0:by1, bx0:bx1].copy()
    crop = crop_bgr[:, :, ::-1].copy()
    crop_mask = mask_u8[by0:by1, bx0:bx1].copy()
    ch, cw = crop.shape[:2]
    side = _choose_edit_side(max(ch, cw))
    square_b, square_m, meta = _letterbox_to_square(crop, crop_mask, side)

    pil_image = Image.fromarray(square_b, mode="RGB")
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
        out_canvas = np.array(pil_r)
    except Exception:
        logger.warning("解码 images.edit 返回失败", exc_info=True)
        return None

    y0l, x0l, nw, nh = meta["y0"], meta["x0"], meta["nw"], meta["nh"]
    inner = out_canvas[y0l : y0l + nh, x0l : x0l + nw]
    if inner.size == 0:
        return None
    restored = _resize_rgb(inner, cw, ch)

    out_full = image_bgr.copy()
    roi = out_full[by0:by1, bx0:bx1]
    cm = crop_mask > 127
    if cm.any():
        blended = roi.copy()
        blended[cm] = restored[cm]
        k = 3
        bmask_u8 = cm.astype(np.uint8) * 255
        border = np.array(
            Image.fromarray(bmask_u8, mode="L").filter(ImageFilter.MaxFilter(size=3)),
            dtype=np.uint8,
        ) - bmask_u8
        if border.any():
            soft = np.array(
                Image.fromarray(blended, mode="RGB").filter(ImageFilter.GaussianBlur(radius=1.2))
            )
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
