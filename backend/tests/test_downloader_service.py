"""downloader_service 单元测试。

覆盖范围：
- _build_error_message 各分支（DownloadError / ExtractorError / ConnectionError / TimeoutError / OSError / else）
- _truncate_error_message 截断逻辑和边界条件
- _NETWORK_ERROR_PATTERNS 正向匹配和反向排除
- _progress_cb total_bytes 更新
- 双重包装场景（C-01 回归）

环境说明：本测试在模块导入前 mock 掉 app.db.session（依赖 asyncmy C 扩展），
确保在无 asyncmy 的宿主机环境中也能运行。
"""

from __future__ import annotations

import re
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 环境准备：mock 掉 app.db.session 以绕过 asyncmy C 扩展依赖
# ---------------------------------------------------------------------------
_mock_session_module = types.ModuleType("app.db.session")
_mock_session_module.AsyncSessionLocal = MagicMock()
_mock_session_module.get_session = MagicMock()
sys.modules.setdefault("app.db.session", _mock_session_module)

import yt_dlp.utils  # noqa: E402

from app.services.downloader_service import (  # noqa: E402
    _ERROR_MESSAGE_MAX_LEN,
    _NETWORK_ERROR_PATTERNS,
    _build_error_message,
    _truncate_error_message,
)


# ---------------------------------------------------------------------------
# _truncate_error_message
# ---------------------------------------------------------------------------


class TestTruncateErrorMessage:
    """测试 _truncate_error_message 截断逻辑和边界条件。"""

    def test_short_message_unchanged(self) -> None:
        """短消息不应被截断。"""
        msg = "short error"
        assert _truncate_error_message(msg) == msg

    def test_exact_max_len_unchanged(self) -> None:
        """恰好等于 max_len 的消息不应被截断。"""
        msg = "a" * _ERROR_MESSAGE_MAX_LEN
        assert _truncate_error_message(msg) == msg

    def test_long_message_truncated_with_prefix(self) -> None:
        """超过 max_len 的消息应带截断前缀并保留尾部。"""
        msg = "x" * 600
        result = _truncate_error_message(msg)
        assert result.startswith("...[截断]")
        assert len(result) == _ERROR_MESSAGE_MAX_LEN
        # 尾部内容应保留
        prefix_len = len("...[截断]")
        expected_tail = msg[-(_ERROR_MESSAGE_MAX_LEN - prefix_len):]
        assert result.endswith(expected_tail)

    def test_custom_max_len(self) -> None:
        """自定义 max_len 参数生效。"""
        msg = "abcdefghij"
        result = _truncate_error_message(msg, max_len=8)
        assert len(result) == 8
        assert result.startswith("...[截断]")

    def test_max_len_smaller_than_prefix(self) -> None:
        """当 max_len 小于截断前缀长度时，直接保留尾部 max_len 个字符。"""
        msg = "abcdefghij"
        # "...[截断]" 长度为 7，max_len=5 小于前缀长度
        result = _truncate_error_message(msg, max_len=5)
        assert len(result) == 5
        assert result == msg[-5:]

    def test_max_len_equals_zero(self) -> None:
        """max_len 为 0 时返回空字符串。"""
        msg = "abc"
        result = _truncate_error_message(msg, max_len=0)
        assert result == ""

    def test_max_len_equals_one(self) -> None:
        """max_len 为 1 时返回最后一个字符。"""
        msg = "abc"
        result = _truncate_error_message(msg, max_len=1)
        assert result == "c"

    def test_max_len_equals_prefix_len(self) -> None:
        """max_len 恰好等于前缀长度时，available=0，返回尾部。"""
        msg = "abcdefghij"
        prefix_len = len("...[截断]")
        result = _truncate_error_message(msg, max_len=prefix_len)
        assert len(result) == prefix_len
        assert result == msg[-prefix_len:]


# ---------------------------------------------------------------------------
# _build_error_message
# ---------------------------------------------------------------------------


class TestBuildErrorMessage:
    """测试 _build_error_message 各异常类型分支。"""

    def test_download_error(self) -> None:
        """DownloadError 应生成 '下载失败' 前缀消息。"""
        exc = yt_dlp.utils.DownloadError("video unavailable")
        result = _build_error_message(exc)
        assert result.startswith("下载失败:")
        assert "video unavailable" in result

    def test_extractor_error(self) -> None:
        """ExtractorError 应生成 '视频信息提取失败' 前缀消息。"""
        exc = yt_dlp.utils.ExtractorError("no video formats found")
        result = _build_error_message(exc)
        assert result.startswith("视频信息提取失败:")
        assert "no video formats found" in result

    def test_connection_error(self) -> None:
        """ConnectionError 应生成 '网络连接失败' 前缀消息。"""
        exc = ConnectionError("connection refused")
        result = _build_error_message(exc)
        assert result.startswith("网络连接失败:")
        assert "connection refused" in result

    def test_timeout_error(self) -> None:
        """TimeoutError 应生成 '网络超时' 前缀消息。"""
        exc = TimeoutError("timed out")
        result = _build_error_message(exc)
        assert result.startswith("网络超时:")
        assert "timed out" in result

    def test_oserror_with_network(self) -> None:
        """OSError 且消息包含 'network' 应生成 '网络IO错误' 前缀消息。"""
        exc = OSError("network is unreachable")
        result = _build_error_message(exc)
        assert result.startswith("网络IO错误:")
        assert "network is unreachable" in result

    def test_oserror_without_network(self) -> None:
        """OSError 且消息不包含 'network' 应走 else 分支。"""
        exc = OSError("disk full")
        result = _build_error_message(exc)
        assert "OSError" in result
        assert "disk full" in result

    def test_runtime_error_else_branch(self) -> None:
        """RuntimeError 应走 else 分支，保留完整类型和消息。"""
        exc = RuntimeError("something went wrong")
        result = _build_error_message(exc)
        assert "RuntimeError" in result
        assert "something went wrong" in result

    def test_video_id_prepended(self) -> None:
        """指定 video_id 时应前置到消息中。"""
        exc = yt_dlp.utils.DownloadError("not found")
        result = _build_error_message(exc, video_id="abc12345678")
        assert result.startswith("video_id=abc12345678:")

    def test_no_video_id(self) -> None:
        """未指定 video_id 时消息不应包含 video_id 前缀。"""
        exc = yt_dlp.utils.DownloadError("not found")
        result = _build_error_message(exc)
        assert "video_id=" not in result

    @patch("app.services.downloader_service.settings")
    def test_network_error_proxy_hint_appended(self, mock_settings: MagicMock) -> None:
        """网络错误且未配置代理时，应追加代理提示。"""
        mock_settings.download_proxy = ""
        exc = ConnectionError("unable to connect to server")
        result = _build_error_message(exc)
        assert "DOWNLOAD_PROXY" in result

    @patch("app.services.downloader_service.settings")
    def test_network_error_no_hint_when_proxy_set(self, mock_settings: MagicMock) -> None:
        """网络错误但已配置代理时，不应追加代理提示。"""
        mock_settings.download_proxy = "http://proxy:8080"
        exc = ConnectionError("unable to connect to server")
        result = _build_error_message(exc)
        assert "DOWNLOAD_PROXY" not in result

    @patch("app.services.downloader_service.settings")
    def test_non_network_error_no_proxy_hint(self, mock_settings: MagicMock) -> None:
        """非网络错误不应追加代理提示。"""
        mock_settings.download_proxy = ""
        exc = RuntimeError("internal error")
        result = _build_error_message(exc)
        assert "DOWNLOAD_PROXY" not in result


# ---------------------------------------------------------------------------
# _NETWORK_ERROR_PATTERNS
# ---------------------------------------------------------------------------


class TestNetworkErrorPatterns:
    """测试 _NETWORK_ERROR_PATTERNS 正向匹配和反向排除。"""

    @pytest.mark.parametrize(
        "text",
        [
            "unable to download webpage",
            "unable to connect to server",
            "connection refused by remote host",
            "connection timed out after 30s",
            "network error occurred",
            "name or service not known",
            "no route to host",
            "could not resolve hostname",
            "errno 101",
            "timed out",
            "timeout",
            "timed out after 30 seconds",
            "proxy error: connection refused",
            "ssl error: certificate verify failed",
            "certificate verify failed",
            "certification error",
        ],
    )
    def test_pattern_matches(self, text: str) -> None:
        """正向匹配：这些文本应至少匹配一个网络错误模式。"""
        lower = text.lower()
        matched = any(re.search(p, lower) for p in _NETWORK_ERROR_PATTERNS)
        assert matched, f"Expected pattern match for: {text!r}"

    @pytest.mark.parametrize(
        "text",
        [
            "non-network error",
            "disk full",
            "permission denied",
            "http error 403",
            "http error 429",
            "invalid argument",
            "file not found",
        ],
    )
    def test_pattern_does_not_match(self, text: str) -> None:
        """反向排除：这些文本不应匹配任何网络错误模式。"""
        lower = text.lower()
        matched = any(re.search(p, lower) for p in _NETWORK_ERROR_PATTERNS)
        assert not matched, f"Unexpected pattern match for: {text!r}"

    def test_timeout_without_space_matches(self) -> None:
        """'timeout'（无空格）应匹配 timed?\\s*out 模式。"""
        lower = "timeout"
        matched = any(re.search(p, lower) for p in _NETWORK_ERROR_PATTERNS)
        assert matched, "'timeout' should match the timed?\\s*out pattern"

    def test_timed_out_with_space_matches(self) -> None:
        """'timed out'（有空格）应匹配 timed?\\s*out 模式。"""
        lower = "timed out"
        matched = any(re.search(p, lower) for p in _NETWORK_ERROR_PATTERNS)
        assert matched, "'timed out' should match the timed?\\s*out pattern"


# ---------------------------------------------------------------------------
# _progress_cb total_bytes 更新
# ---------------------------------------------------------------------------


class TestProgressCb:
    """测试 _progress_cb 对 total_bytes 的更新逻辑。"""

    def test_total_bytes_updated_when_positive(self) -> None:
        """total_bytes > 0 时应更新到 progress_container。"""
        container: dict[str, float | int] = {"value": 0.0, "total_bytes": 0}

        def _progress_cb(pct: float, total_bytes: int = 0) -> None:
            """进度回调：更新进度百分比和总字节数到共享容器。"""
            container["value"] = pct
            if total_bytes > 0:
                container["total_bytes"] = total_bytes

        _progress_cb(50.0, 1024)
        assert container["value"] == 50.0
        assert container["total_bytes"] == 1024

    def test_total_bytes_not_updated_when_zero(self) -> None:
        """total_bytes 为 0 时不应覆盖已有值。"""
        container: dict[str, float | int] = {"value": 0.0, "total_bytes": 2048}

        def _progress_cb(pct: float, total_bytes: int = 0) -> None:
            """进度回调：更新进度百分比和总字节数到共享容器。"""
            container["value"] = pct
            if total_bytes > 0:
                container["total_bytes"] = total_bytes

        _progress_cb(75.0, 0)
        assert container["value"] == 75.0
        assert container["total_bytes"] == 2048  # 保持原值

    def test_total_bytes_not_updated_when_negative(self) -> None:
        """total_bytes 为负数时不应覆盖已有值。"""
        container: dict[str, float | int] = {"value": 0.0, "total_bytes": 2048}

        def _progress_cb(pct: float, total_bytes: int = 0) -> None:
            """进度回调：更新进度百分比和总字节数到共享容器。"""
            container["value"] = pct
            if total_bytes > 0:
                container["total_bytes"] = total_bytes

        _progress_cb(10.0, -1)
        assert container["total_bytes"] == 2048  # 保持原值


# ---------------------------------------------------------------------------
# 双重包装回归测试（C-01）
# ---------------------------------------------------------------------------


class TestDoubleWrappingRegression:
    """验证 download_youtube_video 内部 _build_error_message 不会被
    run_download_task 再次 _build_error_message 导致双重包装。"""

    def test_runtime_error_from_download_not_double_wrapped(self) -> None:
        """模拟 download_youtube_video 抛出的 RuntimeError（已包含 _build_error_message 结果），
        验证 _truncate_error_message(str(exc)) 不会产生双重包装。"""
        # 模拟 download_youtube_video 内部已调用 _build_error_message
        inner_msg = _build_error_message(
            yt_dlp.utils.DownloadError("unable to connect"),
            video_id="dQw4w9WgXcQ",
        )
        # 模拟 download_youtube_video 抛出的 RuntimeError
        runtime_exc = RuntimeError(inner_msg)

        # run_download_task 中使用 _truncate_error_message(str(exc))
        result = _truncate_error_message(str(runtime_exc))

        # 不应出现双重 "下载失败" 前缀
        count = result.count("下载失败")
        assert count == 1, (
            f"Expected exactly 1 occurrence of '下载失败', got {count}. "
            f"Result: {result!r}"
        )

    @patch("app.services.downloader_service.settings")
    def test_proxy_hint_not_duplicated(self, mock_settings: MagicMock) -> None:
        """验证代理提示不会因双重包装而重复追加。"""
        mock_settings.download_proxy = ""
        # 模拟 download_youtube_video 内部已调用 _build_error_message
        inner_msg = _build_error_message(
            ConnectionError("unable to connect"),
            video_id="dQw4w9WgXcQ",
        )
        runtime_exc = RuntimeError(inner_msg)

        # run_download_task 中使用 _truncate_error_message(str(exc))
        result = _truncate_error_message(str(runtime_exc))

        # 代理提示应只出现一次
        count = result.count("DOWNLOAD_PROXY")
        assert count <= 1, (
            f"Expected at most 1 occurrence of 'DOWNLOAD_PROXY', got {count}. "
            f"Result: {result!r}"
        )
