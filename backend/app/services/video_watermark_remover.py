"""
视频静态文本水印自动去除模块（抽帧 OCR + FFmpeg delogo）。

安装依赖（Python）：
pip install ffmpeg-python paddlepaddle paddleocr opencv-python numpy

系统依赖（必须安装）：
- ffmpeg 命令行工具（用于真正执行视频滤镜处理）
  macOS: brew install ffmpeg
  Ubuntu: apt-get install -y ffmpeg
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import ffmpeg
import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int


class VideoWatermarkRemover:
    """
    视频静态文本水印去除器。

    设计原则：
    - PaddleOCR 全局加载一次，避免每次调用重复加载模型。
    - 仅处理“跨多帧位置稳定”的文本区域，尽量避免误伤动态字幕。
    """

    def __init__(self) -> None:
        from paddleocr import PaddleOCR

        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")

    @staticmethod
    def _extract_text_rects(ocr_result: Any) -> list[Rect]:
        """
        从 PaddleOCR 返回结果中提取外接矩形列表。
        """
        rects: list[Rect] = []
        if not ocr_result:
            return rects

        lines = ocr_result[0] if isinstance(ocr_result, list) else ocr_result
        if not isinstance(lines, list):
            return rects

        for item in lines:
            if not isinstance(item, (list, tuple)) or len(item) < 1:
                continue
            points = item[0]
            if not isinstance(points, (list, tuple)) or len(points) < 4:
                continue
            try:
                pts = np.array(points, dtype=np.int32).reshape((-1, 2))
            except Exception:  # noqa: BLE001
                continue
            x, y, w, h = cv2.boundingRect(pts)
            rects.append(Rect(x=x, y=y, w=w, h=h))
        return rects

    @staticmethod
    def _sample_frame_indices(total_frames: int, sample_count: int = 5) -> list[int]:
        """
        按进度均匀抽取关键帧索引。默认抽 5 帧（10%、30%、50%、70%、90%）。
        """
        if total_frames <= 0:
            return []
        positions = [0.1, 0.3, 0.5, 0.7, 0.9]
        if sample_count <= 3:
            positions = [0.1, 0.5, 0.9]
        indices = []
        for p in positions[:sample_count]:
            idx = max(0, min(total_frames - 1, int(total_frames * p)))
            indices.append(idx)
        return sorted(set(indices))

    @staticmethod
    def _center(rect: Rect) -> tuple[float, float]:
        return rect.x + rect.w / 2.0, rect.y + rect.h / 2.0

    @staticmethod
    def _match_with_tolerance(a: Rect, b: Rect, tol: int = 30) -> bool:
        """
        判断两个文本框是否可视为同一静态位置。
        """
        ax, ay = VideoWatermarkRemover._center(a)
        bx, by = VideoWatermarkRemover._center(b)
        return abs(ax - bx) <= tol and abs(ay - by) <= tol

    def _find_static_watermark_rect(
        self,
        all_frame_rects: list[list[Rect]],
        frame_width: int,
        frame_height: int,
        min_hits: int,
    ) -> Rect | None:
        """
        在多帧检测结果中寻找“稳定出现”的文本区域，并融合为最终矩形。
        """
        # 将每一帧的文本框尝试聚类到“同一位置簇”
        clusters: list[dict[str, Any]] = []
        for frame_idx, rects in enumerate(all_frame_rects):
            for rect in rects:
                matched = False
                for c in clusters:
                    if self._match_with_tolerance(rect, c["anchor"], tol=30):
                        c["rects"].append(rect)
                        c["frames"].add(frame_idx)
                        matched = True
                        break
                if not matched:
                    clusters.append(
                        {
                            "anchor": rect,
                            "rects": [rect],
                            "frames": {frame_idx},
                        }
                    )

        if not clusters:
            return None

        # 选出覆盖帧数最多的簇，且至少命中 min_hits 帧
        clusters.sort(key=lambda c: len(c["frames"]), reverse=True)
        best = clusters[0]
        if len(best["frames"]) < min_hits:
            return None

        rects = best["rects"]
        min_x = min(r.x for r in rects)
        min_y = min(r.y for r in rects)
        max_x = max(r.x + r.w for r in rects)
        max_y = max(r.y + r.h for r in rects)

        # 适度扩张，覆盖边缘光晕
        pad = 15
        x = max(0, min_x - pad)
        y = max(0, min_y - pad)
        w = min(frame_width - x, (max_x - min_x) + pad * 2)
        h = min(frame_height - y, (max_y - min_y) + pad * 2)
        if w <= 0 or h <= 0:
            return None
        return Rect(x=x, y=y, w=w, h=h)

    def auto_remove_video_watermark(self, input_video_path: str, output_video_path: str) -> bool:
        """
        自动去除视频中的静态文本水印。

        返回：
        - True: 成功（包括未检测到静态水印时复制原视频）
        - False: 处理失败
        """
        cap: cv2.VideoCapture | None = None
        try:
            in_path = Path(input_video_path)
            out_path = Path(output_video_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            cap = cv2.VideoCapture(str(in_path))
            if not cap.isOpened():
                logger.error("视频读取失败，无法打开文件: %s", input_video_path)
                return False

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if total_frames <= 0 or frame_width <= 0 or frame_height <= 0:
                logger.error(
                    "视频元信息异常，total_frames=%s,fps=%s,width=%s,height=%s,path=%s",
                    total_frames,
                    fps,
                    frame_width,
                    frame_height,
                    input_video_path,
                )
                return False

            sampled_indices = self._sample_frame_indices(total_frames, sample_count=5)
            if not sampled_indices:
                logger.warning("未能抽取有效关键帧，直接复制原视频: %s", input_video_path)
                shutil.copy2(input_video_path, output_video_path)
                return True

            all_frame_rects: list[list[Rect]] = []
            for idx in sampled_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if not ok or frame is None:
                    all_frame_rects.append([])
                    continue
                # PaddleOCR 支持直接传 numpy 图像
                ocr_result = self.ocr.ocr(frame, cls=True)
                rects = self._extract_text_rects(ocr_result)
                all_frame_rects.append(rects)

            # 至少在 3 帧中稳定出现，才认定为静态水印
            min_hits = min(3, len(sampled_indices))
            static_rect = self._find_static_watermark_rect(
                all_frame_rects=all_frame_rects,
                frame_width=frame_width,
                frame_height=frame_height,
                min_hits=min_hits,
            )

            if static_rect is None:
                logger.info("未检测到稳定静态文本水印，复制原视频: %s", input_video_path)
                shutil.copy2(input_video_path, output_video_path)
                return True

            # FFmpeg delogo：处理视频流，音频流直接 copy
            (
                ffmpeg.input(str(in_path))
                .filter(
                    "delogo",
                    x=static_rect.x,
                    y=static_rect.y,
                    w=static_rect.w,
                    h=static_rect.h,
                    show=0,
                )
                .output(str(out_path), **{"c:a": "copy"})
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return True

        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            logger.error("FFmpeg 去水印执行失败: %s", stderr)
            return False
        except MemoryError:
            logger.exception("视频去水印失败：内存不足，input=%s", input_video_path)
            return False
        except Exception:  # noqa: BLE001
            logger.exception("视频去水印失败，input=%s output=%s", input_video_path, output_video_path)
            return False
        finally:
            if cap is not None:
                cap.release()


def auto_remove_video_watermark(input_video_path: str, output_video_path: str) -> bool:
    """
    对外暴露便捷函数。
    """
    try:
        remover = VideoWatermarkRemover()
    except Exception:  # noqa: BLE001
        logger.exception("初始化 PaddleOCR 失败，请确认已安装 paddlepaddle。")
        return False
    return remover.auto_remove_video_watermark(input_video_path, output_video_path)

