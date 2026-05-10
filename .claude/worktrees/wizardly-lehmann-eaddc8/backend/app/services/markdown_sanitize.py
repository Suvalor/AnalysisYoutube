"""
知识库手动录入 Markdown 消毒：在落库前降低 XSS 与危险协议风险（与前端 MarkdownPreview 展示形成纵深防御）。
"""

from __future__ import annotations

import re

import markdown
import nh3

# 与常见 Markdown 正文体量一致，避免超大负载
_MAX_CHARS = 500_000

# 块级危险标签（整段删除）
_BAD_BLOCK_RE = re.compile(
    r"(?is)<\s*(script|iframe|object|embed|meta|link|base|form)\b[^>]*>.*?</\s*\1\s*>",
)
_BAD_VOID_RE = re.compile(
    r"(?is)<\s*(script|iframe|object|embed|meta|link|base|form)\b[^>]*/\s*>",
)
# Markdown 链接中的危险协议
_BAD_LINK_RE = re.compile(r"(?i)\]\(\s*(javascript|vbscript|data)\s*:")


def sanitize_manual_knowledge_markdown(raw: str) -> str:
    """
    对用户 Markdown 做必要消毒后原样存库（仍为 Markdown，与 AI 脚本工坊 content 字段形态一致）。

    步骤：去控制字符 → 长度限制 → 正则剔除常见 HTML 注入片段 → 危险链接协议降级 →
    将 Markdown 转为 HTML 后经 nh3 白名单清洗，确保渲染管线与 nh3 策略一致。
    """
    text = (raw or "").replace("\x00", "").replace("\ufeff", "").strip()
    if not text:
        raise ValueError("核心内容不能为空")
    if len(text) > _MAX_CHARS:
        raise ValueError("核心内容超出长度上限")

    text = _BAD_BLOCK_RE.sub("", text)
    text = _BAD_VOID_RE.sub("", text)
    text = _BAD_LINK_RE.sub("](#", text)

    # 与前端 GFM 接近的扩展（避免 extra 中可能透传原始 HTML）；转 HTML 后走 nh3 校验清洗策略
    html = markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
        output_format="html",
    )
    _ = nh3.clean(html)
    return text
