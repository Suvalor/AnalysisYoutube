"""图像修复（Inpainting）Provider 抽象：便于接入多家云厂商或自建模型。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseInpaintProvider(ABC):
    """统一接口：输入原图与 Mask 的字节（建议 PNG），输出修复后图像字节。"""

    @abstractmethod
    def process(self, image_bytes: bytes, mask_bytes: bytes) -> bytes:
        """
        :param image_bytes: 原图二进制（BGR 或 RGB 均可，由实现约定；本项目使用 PNG 编码的 BGR）
        :param mask_bytes: 单通道或三通道 Mask 的二进制（PNG；白色区域为待修复区，与 OpenCV inpaint 约定一致）
        :return: 修复后图像二进制（PNG 或 JPEG，由实现决定；调用方负责解码）
        """
