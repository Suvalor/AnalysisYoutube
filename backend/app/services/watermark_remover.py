"""
商业级自动文本去水印服务模块（PaddleOCR + OpenCV）。

安装依赖（CPU 版本示例）：
pip install paddlepaddle paddleocr numpy（opencv-python 通常由 paddleocr 依赖安装）

如果你的服务器有 NVIDIA GPU，请按 PaddlePaddle 官网安装对应 CUDA 版本，
再安装 paddleocr 与对应 CUDA 版 paddlepaddle。
"""

from __future__ import annotations

import logging
import shutil
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.watermark_inpaint_config import InpaintRuntimeConfig

# cv2/numpy 延迟导入：避免与 numpy 版本不兼容时在「import app」阶段拖垮整个 FastAPI 进程

logger = logging.getLogger(__name__)


class WatermarkRemover:
    """
    自动文本去水印处理器。

    说明：
    - OCR 模型在初始化时全局加载一次，避免每次调用重复加载模型导致高延迟。
    - 默认针对中文文本场景：use_angle_cls=True, lang="ch"。
    """

    def __init__(self) -> None:
        # 延迟导入，避免依赖未安装时在模块导入阶段导致服务启动失败。
        from app.services.paddle_ocr_runtime_shim import (
            ensure_analysis_config_compat,
            preload_paddle_cpp_libs,
        )

        ensure_analysis_config_compat()
        preload_paddle_cpp_libs()
        from paddleocr import PaddleOCR

        # 全局单例初始化 OCR；参数保持最小集（不在业务代码中调用已弃用的 Paddle AnalysisConfig API）
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")

    @staticmethod
    def _ensure_parent_dir(output_path: str) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _extract_text_boxes(ocr_result: Any) -> list[Any]:
        """
        兼容 PaddleOCR 常见返回结构，提取四点坐标框。
        返回值为 polygon 列表，每个元素 shape=(N, 1, 2)，dtype=int32。
        """
        import cv2
        import numpy as np

        boxes: list[Any] = []
        if not ocr_result:
            return boxes

        # 常见结构：
        # ocr_result = [
        #   [
        #     [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ('text', score)
        #   ]
        # ]
        lines = ocr_result[0] if isinstance(ocr_result, list) else ocr_result
        if not isinstance(lines, list):
            return boxes

        for item in lines:
            if not isinstance(item, (list, tuple)) or len(item) < 1:
                continue
            points = item[0]
            if not isinstance(points, (list, tuple)) or len(points) < 4:
                continue
            try:
                poly = np.array(points, dtype=np.int32).reshape((-1, 1, 2))
            except Exception:  # noqa: BLE001
                continue
            boxes.append(poly)
        return boxes

    def auto_remove_text_watermark(
        self,
        input_path: str,
        output_path: str,
        *,
        inpaint_config: InpaintRuntimeConfig | None = None,
    ) -> tuple[bool, str]:
        """
        自动去除图片中的文本水印。

        返回：(是否成功, 失败时的简短原因，成功时第二项为空字符串)
        """
        import cv2
        import numpy as np

        try:
            self._ensure_parent_dir(output_path)

            # 第一步：读取输入图像
            image = cv2.imread(input_path)
            if image is None:
                msg = "无法读取图片（路径无效、文件损坏或 OpenCV 不支持的格式）"
                logger.error("读取图片失败: %s", input_path)
                return False, msg

            # 第二步：OCR 检测文本框
            ocr_result = self.ocr.ocr(input_path, cls=True)
            boxes = self._extract_text_boxes(ocr_result)

            # 如果未检测到任何文字，直接复制原图到输出目录，避免无意义处理
            if not boxes:
                shutil.copy2(input_path, output_path)
                return True, ""

            # 第三步：构建与原图同尺寸的单通道黑色 Mask
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            for poly in boxes:
                cv2.fillPoly(mask, [poly], 255)

            # 第四步：膨胀 Mask，覆盖文字边缘与光晕，减少修复后重影
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)

            # 第五步：若模型库配置了 image_inpaint，则调用 OpenAI 兼容 images.edit；否则或失败则用 OpenCV TELEA
            inpainted = None
            if inpaint_config is not None:
                from app.services.watermark_inpaint_client import inpaint_bgr_with_runtime_config_or_none

                inpainted = inpaint_bgr_with_runtime_config_or_none(image, mask, inpaint_config)
            if inpainted is None:
                inpainted = cv2.inpaint(image, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

            # 第六步：保存输出
            ok = cv2.imwrite(output_path, inpainted)
            if not ok:
                msg = "无法写入处理后的图片（请检查磁盘权限或路径）"
                logger.error("写出处理结果失败: %s", output_path)
                return False, msg
            return True, ""

        except MemoryError:
            logger.exception("去水印处理失败：内存不足（MemoryError），input=%s", input_path)
            return False, "内存不足，请尝试缩小图片分辨率后重试"
        except Exception as exc:  # noqa: BLE001
            logger.exception("去水印处理失败，input=%s, output=%s", input_path, output_path)
            return False, f"处理异常：{type(exc).__name__}"


_text_remover_lock = threading.Lock()
_text_remover_singleton: WatermarkRemover | None = None
_text_remover_init_error: BaseException | None = None


def _init_engine_error_message(exc: Exception) -> str:
    """将初始化异常转为用户可读说明（便于安装缺失依赖）。"""
    if isinstance(exc, ModuleNotFoundError) and getattr(exc, "name", None):
        return (
            f"缺少 Python 模块「{exc.name}」。请在后端 venv 执行：pip install -r requirements.txt "
            "（推荐 numpy==1.26.4、paddlepaddle==2.6.2、paddleocr==2.7.3）"
        )
    return f"去水印引擎初始化失败（PaddleOCR）：{type(exc).__name__}: {exc}"


def get_text_watermark_remover() -> WatermarkRemover:
    """
    延迟单例：仅在首次需要去水印（图片）时初始化 PaddleOCR。
    若初始化失败，在同一进程内缓存异常，避免重复重试拖慢请求。
    """
    global _text_remover_singleton, _text_remover_init_error
    with _text_remover_lock:
        if _text_remover_singleton is not None:
            return _text_remover_singleton
        if _text_remover_init_error is not None:
            raise _text_remover_init_error
        try:
            _text_remover_singleton = WatermarkRemover()
            return _text_remover_singleton
        except BaseException as exc:
            _text_remover_init_error = exc
            logger.exception("图片去水印 OCR 引擎初始化失败，本进程内后续请求将快速失败")
            raise


def auto_remove_text_watermark(
    input_path: str,
    output_path: str,
    *,
    inpaint_config: InpaintRuntimeConfig | None = None,
) -> tuple[bool, str]:
    """对外便捷函数，返回 (成功, 失败原因)。"""
    try:
        remover = get_text_watermark_remover()
    except Exception as exc:  # noqa: BLE001
        logger.exception("获取图片去水印引擎单例失败。")
        return False, _init_engine_error_message(exc)
    return remover.auto_remove_text_watermark(input_path, output_path, inpaint_config=inpaint_config)

