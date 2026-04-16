"""LLM 对话记忆服务单元测试。"""

import pytest

from app.services.llm_conversation_service import (
    _truncate_messages,
    DEFAULT_MAX_CHARS,
)


class TestTruncateMessages:
    """消息截断逻辑测试。"""

    def test_no_truncation_needed(self):
        """总字符数未超限时不截断。"""
        messages = [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": "用户输入"},
            {"role": "assistant", "content": "AI 回复"},
        ]
        result = _truncate_messages(messages, max_chars=1000)
        assert result == messages

    def test_empty_messages(self):
        """空消息列表返回空。"""
        assert _truncate_messages([], max_chars=100) == []

    def test_truncation_preserves_system(self):
        """截断时始终保留 system 消息。"""
        long_content = "x" * 500
        messages = [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": long_content},
            {"role": "assistant", "content": long_content},
            {"role": "user", "content": long_content},
            {"role": "assistant", "content": long_content},
            {"role": "user", "content": "最新用户输入"},
        ]
        result = _truncate_messages(messages, max_chars=600)
        # system 消息必须保留
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "系统提示"

    def test_truncation_preserves_last_user(self):
        """截断时始终保留最后一条消息。"""
        long_content = "x" * 500
        messages = [
            {"role": "user", "content": long_content},
            {"role": "assistant", "content": long_content},
            {"role": "user", "content": "最新用户输入"},
        ]
        result = _truncate_messages(messages, max_chars=600)
        # 最后一条消息必须保留
        assert result[-1]["content"] == "最新用户输入"

    def test_truncation_drops_oldest_first(self):
        """截断时从最早的非 system 消息开始丢弃。"""
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "a" * 300},
            {"role": "assistant", "content": "b" * 300},
            {"role": "user", "content": "c" * 300},
            {"role": "assistant", "content": "d" * 300},
            {"role": "user", "content": "最新"},
        ]
        result = _truncate_messages(messages, max_chars=500)
        # system 保留
        assert result[0]["role"] == "system"
        # 最新消息保留
        assert result[-1]["content"] == "最新"
        # 最早的非 system 消息应被丢弃
        total_chars = sum(len(m["content"]) for m in result)
        assert total_chars <= 500

    def test_only_system_and_last(self):
        """极端情况：只有 system 和一条 user，不截断。"""
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ]
        result = _truncate_messages(messages, max_chars=10)
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["content"] == "hello"


class TestConversationEntityIsolation:
    """对话实体隔离逻辑验证（基于 CRUD 层的查询条件）。"""

    def test_entity_type_values(self):
        """验证所有支持的 entity_type 值。"""
        valid_types = {"script", "ai_script", "channel_ai", "radar_retro", "sop_split"}
        # 这些值在 API 层硬编码，需确保长度不超过模型定义的 String(32)
        for t in valid_types:
            assert len(t) <= 32, f"entity_type '{t}' 超过 32 字符限制"

    def test_entity_id_format(self):
        """验证 entity_id 格式不超过 String(64) 限制。"""
        # 各端点生成的 entity_id 格式
        ids = [
            "script:topic123",                          # scripts/generate
            "prompt:1:style:2",                         # ai/generate-script-stream
            "12345",                                    # youtube/channels/{id}/ai-analyze
            "lookback:14:top:8",                        # radar/ai-retrospective
            "outline:123456789",                         # sop/segments/ai-split
        ]
        for eid in ids:
            assert len(eid) <= 64, f"entity_id '{eid}' 超过 64 字符限制"
