import json
from typing import Any

import httpx
from fastapi import HTTPException, status
from openai import AsyncOpenAI

from app.core.config import settings


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("模型返回为空")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("模型返回不是有效 JSON") from None
        return json.loads(text[start : end + 1])


def _sanitize_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    for item in value:
        s = str(item).strip()
        if s:
            tags.append(s)
    return tags[:5]


def _channel_ai_json_rules() -> str:
    return (
        "你是一个资深的 YouTube 频道分析师。\n"
        "请根据用户提供的频道标题、频道简介、近期热门视频标题、视频标签与评论，提炼该博主的内容特征。\n"
        "请严格只输出一个 JSON 对象，不要输出任何额外文字或 Markdown 代码块。\n"
        "JSON 必须包含以下键：\n"
        '  "tags": 字符串数组，3～5 个中文核心标签；\n'
        '  "expertise": 字符串，一句话概括该博主「擅长做什么样的内容」、风格或领域（擅长内容）；\n'
        '  "summary": 字符串，频道定位或内容套路的补充说明，80 字以内；\n'
        '  "age_group": 字符串，受众年龄段与性别倾向简述，无法判断时可写「未标注」。\n'
        "示例："
        '{"tags":["科技制作","硬核科普"],"expertise":"擅长用实体模型演示复杂物理概念","summary":"高信息密度解说+手工实验","age_group":"18-35岁偏男性"}'
    )


def build_channel_ai_messages(
    *,
    channel_title: str,
    channel_description: str,
    top_video_titles: list[str],
    merged_tags: list[str],
    hot_comments: list[str],
    agent_system_prepend: str | None = None,
) -> list[dict[str, str]]:
    """
    组装发给 LLM 的消息列表。
    若传入 agent_system_prepend（配置中心智能体的系统提示词），会置于分析师规则之前，作为角色与任务补充。
    """
    top_titles_text = "\n".join([f"- {x}" for x in top_video_titles]) if top_video_titles else "- 暂无视频标题数据"
    tags_text = ", ".join(merged_tags) if merged_tags else "暂无标签数据"
    comments_text = "\n".join([f"- {x}" for x in hot_comments]) if hot_comments else "- 暂无热门评论数据"

    rules = _channel_ai_json_rules()
    if agent_system_prepend and agent_system_prepend.strip():
        system_prompt = (
            f"【智能体 / 分析任务说明（来自用户配置）】\n{agent_system_prepend.strip()}\n\n"
            f"----\n\n【输出格式与角色约束】\n{rules}"
        )
    else:
        system_prompt = rules

    user_prompt = (
        f"【频道标题】\n{channel_title}\n\n"
        f"【频道简介】\n{channel_description or '无'}\n\n"
        f"【播放量 Top10 视频标题】\n{top_titles_text}\n\n"
        f"【视频标签合并结果】\n{tags_text}\n\n"
        f"【热门评论（若有）】\n{comments_text}\n"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _parse_insight_result(parsed: dict[str, Any]) -> dict[str, str | list[str]]:
    tags = _sanitize_tags(parsed.get("tags"))
    expertise = str(parsed.get("expertise") or "").strip()
    summary = str(parsed.get("summary") or "").strip()
    age_group = str(parsed.get("age_group") or "").strip() or "未标注"

    if not expertise and summary:
        expertise = summary
    if not summary and expertise:
        summary = expertise[:120]

    if not tags and not expertise:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 返回缺少 tags 或 expertise 等必要字段",
        )
    return {
        "tags": tags,
        "expertise": expertise or summary or "暂无",
        "age_group": age_group,
        "summary": summary or expertise or "暂无",
    }


async def analyze_channel_ai_insight(
    messages: list[dict[str, str]],
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> dict[str, str | list[str]]:
    """
    使用 OpenAI 兼容的 chat.completions 调用 LLM（适用于配置中心自建网关、火山 OpenAI 兼容端等）。
    未传 api_key/base_url/model 时回退到环境变量中的火山引擎配置。
    """
    key = (api_key or settings.volcengine_api_key or "").strip()
    base = (base_url or settings.volcengine_base_url or "").strip().rstrip("/")
    m = (model or settings.volcengine_endpoint_id or "").strip()
    if not key or not base or not m:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM 配置不完整：请检查 API Key、Base URL 与模型名（或环境变量 VOLCENGINE_*）",
        )

    system_prompt = ""
    user_prompt = ""
    for msg in messages:
        role = str(msg.get("role") or "").strip()
        content = str(msg.get("content") or "").strip()
        if role == "system":
            system_prompt = content
        elif role == "user":
            user_prompt = content

    http_client = httpx.AsyncClient(timeout=120.0, trust_env=False)
    client = AsyncOpenAI(api_key=key, base_url=base, http_client=http_client)
    try:
        resp = await client.chat.completions.create(
            model=m,
            temperature=0.35,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = resp.choices[0] if resp.choices else None
        raw_content = (choice.message.content if choice and choice.message else "") or ""
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 分析调用失败: {exc}",
        ) from exc
    finally:
        await http_client.aclose()

    try:
        parsed = _extract_json_object(raw_content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 返回格式异常: {exc}；原始片段：{raw_content[:500]}",
        ) from exc

    return _parse_insight_result(parsed)
