"""
基于 OpenAI Images Edit（DALL·E 2）的局部重绘，用于去水印插件。

说明：
- 项目内「火山」集成仅为 chat.completions 文本接口；既梦为异步文生图任务提交，均无标准 mask inpainting。
- 本模块为可选能力：配置 WATERMARK_OPENAI_API_KEY 后，在去水印流程中优先尝试；
  失败或未配置时由调用方回退 OpenCV / FFmpeg。

API 文档参考：https://platform.openai.com/docs/api-reference/images/createEdit
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_openai_inpaint_configured() -> bool:
    return bool((settings.watermark_openai_api_key or "").strip())


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
    """将 ROI 保持比例缩放后置于正方形画布中心，供 DALL·E Edit 尺寸约束。"""
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


def inpaint_bgr_with_openai_or_none(image_bgr: np.ndarray, mask_u8: np.ndarray) -> np.ndarray | None:
    """
    对 BGR 图与单通道 mask（255=待修复）调用 OpenAI images.edit；失败返回 None。

    仅处理 mask 非零区域的外接框（含少量边距），再 letterbox 到 256/512/1024。
    """
    import cv2
    from openai import OpenAI
    from PIL import Image

    if not is_openai_inpaint_configured():
        return None
    if image_bgr.shape[:2] != mask_u8.shape[:2]:
        logger.warning("OpenAI inpaint：图像与 mask 尺寸不一致，跳过")
        return None

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

    api_key = (settings.watermark_openai_api_key or "").strip()
    base_url = (settings.watermark_openai_base_url or "").strip() or None
    prompt = (settings.watermark_inpaint_prompt or "").strip() or "Remove watermark naturally."

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        result = client.images.edit(
            model="dall-e-2",
            image=io.BytesIO(buf_img.getvalue()),
            mask=io.BytesIO(buf_mask.getvalue()),
            prompt=prompt,
            n=1,
            size=f"{side}x{side}",
            response_format="b64_json",
        )
    except Exception:
        logger.warning("OpenAI images.edit 调用失败，将回退传统修复", exc_info=True)
        return None

    if not result.data:
        logger.warning("OpenAI images.edit 返回空 data")
        return None
    b64 = getattr(result.data[0], "b64_json", None)
    if not b64:
        logger.warning("OpenAI images.edit 未返回 b64_json")
        return None

    try:
        raw = base64.b64decode(b64)
        pil_r = Image.open(io.BytesIO(raw)).convert("RGB")
        arr = np.array(pil_r)
        out_canvas = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    except Exception:
        logger.warning("解码 OpenAI 返回图像失败", exc_info=True)
        return None

    y0, x0, nw, nh = meta["y0"], meta["x0"], meta["nw"], meta["nh"]
    inner = out_canvas[y0 : y0 + nh, x0 : x0 + nw]
    if inner.size == 0:
        return None
    restored = cv2.resize(inner, (cw, ch), interpolation=cv2.INTER_AREA)

    out_full = image_bgr.copy()
    roi = out_full[by0:by1, bx0:bx1]
    cm = crop_mask > 127
    if cm.any():
        blended = roi.copy()
        blended[cm] = restored[cm]
        # 边缘轻模糊减少硬边
        k = 3
        border = cv2.dilate(cm.astype(np.uint8) * 255, np.ones((k, k), np.uint8), iterations=1) - (cm.astype(np.uint8) * 255)
        if border.any():
            soft = cv2.GaussianBlur(blended, (5, 5), 0)
            bmask = border.astype(bool)
            blended[bmask] = soft[bmask]
        roi[:] = blended
    else:
        roi[:] = restored
    return out_full
