"""
PaddlePaddle 与 PaddleOCR 版本兼容与启动预检。

部分新版本 Paddle 中 AnalysisConfig 已移除 set_optimization_level，而旧版 paddleocr 仍会调用，
导致：AttributeError: 'AnalysisConfig' object has no attribute 'set_optimization_level'

在「import paddleocr / 构造 PaddleOCR」之前调用 ensure_analysis_config_compat()。
不改变去水印算法，仅补齐缺失 API 为无操作（不主动调用已弃用接口，仅补丁）。

preload_paddle_cpp_libs() 在主流程初始化 OCR 前调用，尽早暴露 C++ 扩展 / 动态库加载问题。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_shim_applied = False


def ensure_analysis_config_compat() -> None:
    """为 AnalysisConfig 补全 set_optimization_level（若不存在且被 paddleocr 调用）。"""
    global _shim_applied
    if _shim_applied:
        return
    try:
        import paddle.base.libpaddle as libpaddle  # type: ignore[import-untyped]

        ac = getattr(libpaddle, "AnalysisConfig", None)
        if ac is None:
            return
        if hasattr(ac, "set_optimization_level"):
            return

        def _set_optimization_level(self, *_args, **_kwargs) -> None:  # noqa: ANN001
            return None

        ac.set_optimization_level = _set_optimization_level  # type: ignore[method-assign]
        logger.info("已应用 Paddle AnalysisConfig.set_optimization_level 兼容补丁（空实现）")
    except Exception:
        logger.debug("Paddle AnalysisConfig 兼容补丁未应用（可忽略）", exc_info=True)
    finally:
        _shim_applied = True


def preload_paddle_cpp_libs() -> None:
    """
    预检 Paddle C++ 扩展能否加载（import paddle / libpaddle），
    避免仅在 PaddleOCR 内部才出现难以定位的 native 错误。
    """
    import importlib

    importlib.import_module("paddle")
    try:
        importlib.import_module("paddle.base.libpaddle")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Paddle libpaddle 预检未完全通过：%s", exc)
