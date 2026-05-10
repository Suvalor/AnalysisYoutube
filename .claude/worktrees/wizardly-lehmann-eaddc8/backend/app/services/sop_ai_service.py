from __future__ import annotations

from collections.abc import AsyncGenerator
import re

import httpx

from app.models.user import User
from app.services.config_manager import ResolvedIntegrationConfig
from app.services.llm_openai_factory import LLMClientFactory, LLMClientConfig, normalize_base_url
from app.services.script_user_ai import parse_models_from_user_json, user_custom_openai_credentials


async def split_outline_markdown_with_ai(
    *,
    user: User,
    outline_markdown: str,
    model: str | None = None,
    agent_prompt: str | None = None,
    integration: ResolvedIntegrationConfig | None = None,
) -> str:
    parts: list[str] = []
    async for chunk in split_outline_markdown_with_ai_stream(
        user=user,
        outline_markdown=outline_markdown,
        model=model,
        agent_prompt=agent_prompt,
        integration=integration,
    ):
        parts.append(chunk)
    return "".join(parts).strip()


async def split_outline_markdown_with_ai_stream(
    *,
    user: User,
    outline_markdown: str,
    model: str | None = None,
    agent_prompt: str | None = None,
    integration: ResolvedIntegrationConfig | None = None,
) -> AsyncGenerator[str, None]:
    fast_result = _fast_split_markdown(outline_markdown)
    if fast_result:
        yield fast_result
        return

    creds = user_custom_openai_credentials(user)
    if creds:
        api_key, base_url_raw = creds
        default_model = parse_models_from_user_json(user.ai_models_json)[0]["value"]
        explicit = (model or default_model or "").strip()
    else:
        if integration is None:
            raise ValueError("未配置自建 LLM 时，必须在请求内解析并传入用户集成配置 integration")
        api_key = ""
        base_url_raw = ""
        explicit = (model or "").strip()
    base_url = normalize_base_url(base_url_raw)
    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=api_key, base_url=base_url, model_name=explicit, protocol="openai")
    resolved_model = factory.resolve_model_name(cfg)
    if not api_key or not base_url or not resolved_model:
        raise ValueError("LLM 配置不完整，无法执行 AI 拆解")

    system_prompt = (
        "你是资深分镜导演与短视频编剧。\n"
        "请把用户提供的剧本大纲拆成结构化剧情片段，输出必须是 Markdown，且只输出 Markdown。\n"
        "格式要求：\n"
        "## 片段 1：标题\n"
        "片段正文（可多段）\n\n"
        "## 片段 2：标题\n"
        "片段正文（可多段）\n\n"
        "约束：\n"
        "1) 片段数量 4-10 段；\n"
        "2) 每段保持可拍摄性与连续性；\n"
        "3) 不要输出 JSON，不要输出代码块标记。"
    )
    if agent_prompt and agent_prompt.strip():
        system_prompt = f"{system_prompt}\n\n【智能体补充规则】\n{agent_prompt.strip()}"
    user_prompt = f"请拆解以下剧本大纲：\n\n{outline_markdown}"
    async for delta in factory.stream_chat_completions_deltas(
        cfg=cfg,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    ):
        yield delta


def _fast_split_markdown(outline_markdown: str) -> str:
    """
    对常见“标准分镜表”输入做本地快速拆解，避免大文本调用 LLM 超时。
    命中后直接返回结构化 Markdown；未命中返回空字符串。
    """
    text = (outline_markdown or "").strip()
    if not text:
        return ""
    if "标准分镜表" not in text and "| 镜号 |" not in text:
        return ""

    # 提取 Markdown 表格的行（过滤表头分隔线）
    lines = [x.rstrip() for x in text.splitlines()]
    table_rows = [x for x in lines if x.strip().startswith("|") and "---" not in x]
    if len(table_rows) < 3:
        return ""

    # 粗略定位列索引，兼容“镜号/画面内容/台词/参考时长”等字段
    header_cells = _split_md_row(table_rows[0])
    if not header_cells:
        return ""

    idx_shot = _find_col(header_cells, ["镜号"])
    idx_visual = _find_col(header_cells, ["画面内容", "画面"])
    idx_dialogue = _find_col(header_cells, ["台词"])
    idx_duration = _find_col(header_cells, ["参考时长", "时长"])
    if idx_shot < 0:
        return ""

    out_blocks: list[str] = []
    seq = 1
    for row in table_rows[1:]:
        cells = _split_md_row(row)
        if len(cells) <= idx_shot:
            continue
        shot_no = cells[idx_shot].strip()
        if not shot_no:
            continue
        # 过滤可能残留的表头行
        if "镜号" in shot_no:
            continue

        visual = cells[idx_visual].strip() if idx_visual >= 0 and len(cells) > idx_visual else ""
        dialogue = cells[idx_dialogue].strip() if idx_dialogue >= 0 and len(cells) > idx_dialogue else ""
        duration = cells[idx_duration].strip() if idx_duration >= 0 and len(cells) > idx_duration else ""

        title = f"片段 {seq}：镜头 {shot_no}"
        content_parts = []
        if visual:
            content_parts.append(f"**画面内容**：{visual}")
        if dialogue:
            content_parts.append(f"**台词**：{dialogue}")
        if duration:
            content_parts.append(f"**参考时长**：{duration}")
        if not content_parts:
            continue
        out_blocks.append(f"## {title}\n" + "\n\n".join(content_parts))
        seq += 1

    return "\n\n".join(out_blocks).strip()


def _split_md_row(row: str) -> list[str]:
    raw = row.strip().strip("|")
    cells = [c.strip() for c in raw.split("|")]
    return cells


def _find_col(headers: list[str], candidates: list[str]) -> int:
    for i, h in enumerate(headers):
        clean = re.sub(r"\s+", "", h)
        for c in candidates:
            if c in clean:
                return i
    return -1
