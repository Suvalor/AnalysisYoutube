"""
视频静态文本水印自动去除模块（抽帧 OCR + FFmpeg delogo）。

安装依赖（Python）：
pip install ffmpeg-python paddlepaddle paddleocr numpy（opencv-python 通常由 paddleocr 依赖安装）

系统依赖（必须安装）：
- ffmpeg 命令行工具（用于真正执行视频滤镜处理）
  macOS: brew install ffmpeg
  Ubuntu: apt-get install -y ffmpeg
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.watermark_inpaint_config import InpaintRuntimeConfig

import ffmpeg

# cv2/numpy 延迟导入，避免 Docker 内 numpy/opencv ABI 不匹配时阻塞 uvicorn 启动

logger = logging.getLogger(__name__)


def _lazy_cv_numpy() -> tuple[Any, Any]:
    import cv2
    import numpy as np

    return cv2, np


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
        from app.services.paddle_ocr_runtime_shim import (
            ensure_analysis_config_compat,
            preload_paddle_cpp_libs,
        )

        ensure_analysis_config_compat()
        preload_paddle_cpp_libs()
        from paddleocr import PaddleOCR

        self.ocr = PaddleOCR(use_angle_cls=True, lang="ch")

    @staticmethod
    def _extract_text_rects(ocr_result: Any) -> list[Rect]:
        """
        从 PaddleOCR 返回结果中提取外接矩形列表。
        """
        cv2, np = _lazy_cv_numpy()
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

    def auto_remove_video_watermark(
        self,
        input_video_path: str,
        output_video_path: str,
        *,
        inpaint_config: InpaintRuntimeConfig | None = None,
    ) -> tuple[bool, str]:
        """
        自动去除视频中的静态文本水印。

        返回：(是否成功, 失败原因；成功时第二项为空字符串)
        """
        cv2, _ = _lazy_cv_numpy()
        cap: Any = None
        try:
            in_path = Path(input_video_path)
            out_path = Path(output_video_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            cap = cv2.VideoCapture(str(in_path))
            if not cap.isOpened():
                logger.error("视频读取失败，无法打开文件: %s", input_video_path)
                return False, "无法打开视频文件（格式不支持或文件损坏）"

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
                return False, "视频元数据异常（无法读取分辨率或帧数）"

            sampled_indices = self._sample_frame_indices(total_frames, sample_count=5)
            if not sampled_indices:
                logger.warning("未能抽取有效关键帧，直接复制原视频: %s", input_video_path)
                shutil.copy2(input_video_path, output_video_path)
                return True, ""

            all_frame_rects: list[list[Rect]] = []
            for idx in sampled_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if not ok or frame is None:
                    all_frame_rects.append([])
                    continue
                ocr_result = self.ocr.ocr(frame, cls=True)
                rects = self._extract_text_rects(ocr_result)
                all_frame_rects.append(rects)

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
                return True, ""

            sx, sy, sw, sh = static_rect.x, static_rect.y, static_rect.w, static_rect.h

            def _delogo_ffmpeg() -> None:
                (
                    ffmpeg.input(str(in_path))
                    .filter("delogo", x=sx, y=sy, w=sw, h=sh, show=0)
                    .output(str(out_path), **{"c:a": "copy"})
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

            from app.services.watermark_inpaint_client import (
                AI_FAILED_FALLBACK_TO_OPENCV,
                blend_patch_with_gaussian_feather,
                inpaint_bgr_with_runtime_config_or_none,
            )

            use_ai = (
                inpaint_config is not None
                and inpaint_config.has_any_ai()
                and total_frames > 0
                and total_frames <= inpaint_config.video_max_frames
            )
            if not use_ai:
                if inpaint_config is not None and total_frames > inpaint_config.video_max_frames:
                    logger.info(
                        "视频帧数 %s 超过组织配置的 watermark_video_ai_max_frames=%s，使用 FFmpeg delogo",
                        total_frames,
                        inpaint_config.video_max_frames,
                    )
                _delogo_ffmpeg()
                return True, ""

            cap.release()
            cap = None  # 避免 finally 二次 release
            import numpy as np

            cap2 = cv2.VideoCapture(str(in_path))
            tmp_p: Path | None = None
            try:
                if not cap2.isOpened():
                    logger.warning("无法重新打开视频进行 AI 逐帧修复，回退 delogo")
                    _delogo_ffmpeg()
                    return True, ""

                tmp_fd, tmp_name = tempfile.mkstemp(suffix=".mp4")
                os.close(tmp_fd)
                tmp_p = Path(tmp_name)
                feather = max(6, min(sw, sh) // 20)

                # 静态水印：仅在关键帧做一次云端/本地 Inpaint，全片复用修补块以控制成本
                key_idx = sampled_indices[len(sampled_indices) // 2]
                repaired_master: np.ndarray | None = None
                cap2.set(cv2.CAP_PROP_POS_FRAMES, key_idx)
                ok_kf, kfr = cap2.read()
                if (
                    ok_kf
                    and kfr is not None
                    and sh > 0
                    and sw > 0
                    and sy + sh <= kfr.shape[0]
                    and sx + sw <= kfr.shape[1]
                    and sy >= 0
                    and sx >= 0
                ):
                    kpatch = kfr[sy : sy + sh, sx : sx + sw].copy()
                    pm_key = np.full((sh, sw), 255, dtype=np.uint8)
                    repaired_master = inpaint_bgr_with_runtime_config_or_none(
                        kpatch, pm_key, inpaint_config
                    )
                    if repaired_master is None:
                        logger.warning(
                            "%s: 视频关键帧云端 Inpaint 未成功，该水印区域改用 OpenCV TELEA 并复用到全部帧",
                            AI_FAILED_FALLBACK_TO_OPENCV,
                        )
                        repaired_master = cv2.inpaint(kpatch, pm_key, 3, cv2.INPAINT_TELEA)
                else:
                    logger.warning("无法读取关键帧或水印区域越界，后续逐帧使用 OpenCV TELEA 修补")

                cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)

                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(str(tmp_p), fourcc, fps, (frame_width, frame_height))
                if not writer.isOpened():
                    logger.warning("OpenCV VideoWriter 不可用，回退 FFmpeg delogo")
                    _delogo_ffmpeg()
                    return True, ""

                try:
                    while True:
                        ok_f, fr = cap2.read()
                        if not ok_f:
                            break
                        if (
                            sh <= 0
                            or sw <= 0
                            or sy + sh > fr.shape[0]
                            or sx + sw > fr.shape[1]
                            or sy < 0
                            or sx < 0
                        ):
                            writer.write(fr)
                            continue
                        if repaired_master is not None:
                            p = repaired_master
                            if p.shape[0] != sh or p.shape[1] != sw:
                                p = cv2.resize(p, (sw, sh))
                            blend_patch_with_gaussian_feather(fr, sx, sy, p, feather)
                        else:
                            patch = fr[sy : sy + sh, sx : sx + sw].copy()
                            pm = np.full((sh, sw), 255, dtype=np.uint8)
                            repaired = cv2.inpaint(patch, pm, 3, cv2.INPAINT_TELEA)
                            blend_patch_with_gaussian_feather(fr, sx, sy, repaired, feather)
                        writer.write(fr)
                finally:
                    writer.release()

                try:
                    v_in = ffmpeg.input(str(tmp_p))
                    orig_in = ffmpeg.input(str(in_path))
                    ffmpeg.output(
                        v_in.video,
                        orig_in.audio,
                        str(out_path),
                        vcodec="libx264",
                        acodec="copy",
                    ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
                except Exception:
                    logger.warning("FFmpeg 合并音轨失败或源无音频，输出无音频视频", exc_info=True)
                    shutil.copy2(tmp_p, out_path)
            finally:
                cap2.release()
                if tmp_p is not None:
                    tmp_p.unlink(missing_ok=True)

            return True, ""

        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            logger.error("FFmpeg 去水印执行失败: %s", stderr)
            tail = (stderr or "").strip()[-240:]
            if tail:
                return False, f"视频处理失败（FFmpeg），请确认已安装 ffmpeg。摘要：{tail}"
            return False, "视频处理失败（FFmpeg），请确认系统已安装 ffmpeg 命令行工具"

        except MemoryError:
            logger.exception("视频去水印失败：内存不足，input=%s", input_video_path)
            return False, "内存不足，请尝试缩短视频或降低分辨率后重试"

        except Exception as exc:  # noqa: BLE001
            logger.exception("视频去水印失败，input=%s output=%s", input_video_path, output_video_path)
            return False, f"处理异常：{type(exc).__name__}"

        finally:
            if cap is not None:
                cap.release()


_video_remover_lock = threading.Lock()
_video_remover_singleton: VideoWatermarkRemover | None = None
_video_remover_init_error: BaseException | None = None


def get_video_watermark_remover() -> VideoWatermarkRemover:
    """延迟单例：仅在首次需要视频去水印时初始化 PaddleOCR。"""
    global _video_remover_singleton, _video_remover_init_error
    with _video_remover_lock:
        if _video_remover_singleton is not None:
            return _video_remover_singleton
        if _video_remover_init_error is not None:
            raise _video_remover_init_error
        try:
            _video_remover_singleton = VideoWatermarkRemover()
            return _video_remover_singleton
        except BaseException as exc:
            _video_remover_init_error = exc
            logger.exception("视频去水印 OCR 引擎初始化失败，本进程内后续请求将快速失败")
            raise


def _init_engine_error_message(exc: Exception) -> str:
    if isinstance(exc, ModuleNotFoundError) and getattr(exc, "name", None):
        return (
            f"缺少 Python 模块「{exc.name}」。请在后端 venv 执行：pip install -r requirements.txt "
            "（推荐 numpy==1.26.4、paddlepaddle==2.6.2、paddleocr==2.7.3）"
        )
    return f"去水印引擎初始化失败（PaddleOCR）：{type(exc).__name__}: {exc}"


def auto_remove_video_watermark(
    input_video_path: str,
    output_video_path: str,
    *,
    inpaint_config: InpaintRuntimeConfig | None = None,
) -> tuple[bool, str]:
    """对外便捷函数，返回 (成功, 失败原因)。"""
    try:
        remover = get_video_watermark_remover()
    except Exception as exc:  # noqa: BLE001
        logger.exception("获取视频去水印引擎单例失败。")
        return False, _init_engine_error_message(exc)
    return remover.auto_remove_video_watermark(
        input_video_path,
        output_video_path,
        inpaint_config=inpaint_config,
    )

