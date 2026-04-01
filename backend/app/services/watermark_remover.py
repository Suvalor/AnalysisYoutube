"""
商业级自动文本去水印服务模块（PaddleOCR + OpenCV）。

安装依赖（CPU 版本示例）：
pip install paddlepaddle paddleocr opencv-python numpy

如果你的服务器有 NVIDIA GPU，请按 PaddlePaddle 官网安装对应 CUDA 版本，
再安装 paddleocr / opencv-python / numpy。
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import cv2
import numpy as np


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
        from paddleocr import PaddleOCR

        # 全局单例初始化 OCR，提升服务端吞吐与响应稳定性。
        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")

    @staticmethod
    def _ensure_parent_dir(output_path: str) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _extract_text_boxes(ocr_result: Any) -> list[np.ndarray]:
        """
        兼容 PaddleOCR 常见返回结构，提取四点坐标框。
        返回值为 polygon 列表，每个元素 shape=(N, 1, 2)，dtype=int32。
        """
        boxes: list[np.ndarray] = []
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

    def auto_remove_text_watermark(self, input_path: str, output_path: str) -> bool:
        """
        自动去除图片中的文本水印。

        处理流程：
        1) 读取图片
        2) OCR 检测文本区域
        3) 生成文本区域二值 Mask
        4) 对 Mask 膨胀，覆盖文字边缘光晕
        5) Inpainting 修复
        6) 保存输出

        返回：
        - True: 成功（包括未检测到文本时直接复制原图）
        - False: 失败
        """
        try:
            self._ensure_parent_dir(output_path)

            # 第一步：读取输入图像
            image = cv2.imread(input_path)
            if image is None:
                logger.error("读取图片失败，路径无效或文件损坏: %s", input_path)
                return False

            # 第二步：OCR 检测文本框
            # PaddleOCR 对单张图片输入路径，返回文本框 + 文本 + 置信度
            ocr_result = self.ocr.ocr(input_path, cls=True)
            boxes = self._extract_text_boxes(ocr_result)

            # 如果未检测到任何文字，直接复制原图到输出目录，避免无意义处理
            if not boxes:
                shutil.copy2(input_path, output_path)
                return True

            # 第三步：构建与原图同尺寸的单通道黑色 Mask
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            for poly in boxes:
                cv2.fillPoly(mask, [poly], 255)

            # 第四步：膨胀 Mask，覆盖文字边缘与光晕，减少修复后重影
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)

            # 第五步：图像修复（TELEA 算法）
            inpainted = cv2.inpaint(image, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

            # 第六步：保存输出
            ok = cv2.imwrite(output_path, inpainted)
            if not ok:
                logger.error("写出处理结果失败: %s", output_path)
                return False
            return True

        except MemoryError:
            logger.exception("去水印处理失败：内存不足（MemoryError），input=%s", input_path)
            return False
        except Exception:  # noqa: BLE001
            logger.exception("去水印处理失败，input=%s, output=%s", input_path, output_path)
            return False


def auto_remove_text_watermark(input_path: str, output_path: str) -> bool:
    """
    对外暴露的便捷函数。
    """
    try:
        remover = WatermarkRemover()
    except Exception:  # noqa: BLE001
        logger.exception("初始化 PaddleOCR 失败，请确认已安装 paddlepaddle。")
        return False
    return remover.auto_remove_text_watermark(input_path, output_path)

