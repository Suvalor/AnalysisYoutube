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


def _required_volcengine_config() -> None:
    if not settings.volcengine_api_key or not settings.volcengine_base_url or not settings.volcengine_endpoint_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="火山引擎配置不完整",
        )


def build_channel_ai_messages(
    *,
    channel_title: str,
    channel_description: str,
    top_video_titles: list[str],
    merged_tags: list[str],
    hot_comments: list[str],
) -> list[dict[str, str]]:
    top_titles_text = "\n".join([f"- {x}" for x in top_video_titles]) if top_video_titles else "- 暂无视频标题数据"
    tags_text = ", ".join(merged_tags) if merged_tags else "暂无标签数据"
    comments_text = "\n".join([f"- {x}" for x in hot_comments]) if hot_comments else "- 暂无热门评论数据"

    system_prompt = (
        "你是一个资深的 YouTube 频道分析师。\n"
        "请根据我提供的频道简介、热门视频标题、视频标签和评论，推理出该频道的受众画像与内容定位。\n"
        "请严格以 JSON 格式返回，不要输出任何额外文字。\n"
        'JSON 键名固定为 tags, age_group, summary。\n'
        "其中：\n"
        "1) tags: 返回 3-5 个中文关键词数组；\n"
        "2) age_group: 返回受众年龄段及性别倾向，使用简短中文；\n"
        "3) summary: 返回频道内容定位与爆款套路总结，100字以内。"
    )
    user_prompt = (
        f"【频道标题】\n{channel_title}\n\n"
        f"【频道简介】\n{channel_description or '无'}\n\n"
        f"【播放量 Top10 视频标题】\n{top_titles_text}\n\n"
        f"【视频标签合并结果】\n{tags_text}\n\n"
        f"【热门评论（可选）】\n{comments_text}\n"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def analyze_channel_ai_insight(messages: list[dict[str, str]]) -> dict[str, str | list[str]]:
    _required_volcengine_config()
    # 显式提供 httpx 客户端，避免 openai 与 httpx 版本在 proxies 参数上的兼容问题。
    http_client = httpx.AsyncClient(timeout=60.0, trust_env=False)
    client = AsyncOpenAI(
        api_key=settings.volcengine_api_key,
        base_url=settings.volcengine_base_url,
        http_client=http_client,
    )
    try:
        completion = await client.chat.completions.create(
            model=settings.volcengine_endpoint_id,
            stream=False,
            temperature=0.2,
            messages=messages,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 分析调用失败: {exc}",
        ) from exc
    finally:
        await http_client.aclose()

    raw_content = ""
    if completion.choices and completion.choices[0].message and completion.choices[0].message.content:
        raw_content = completion.choices[0].message.content
    try:
        parsed = _extract_json_object(raw_content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 返回格式异常: {exc}",
        ) from exc

    tags = _sanitize_tags(parsed.get("tags"))
    age_group = str(parsed.get("age_group") or "").strip()
    summary = str(parsed.get("summary") or "").strip()
    if not age_group or not summary:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 返回缺少必要字段",
        )
    return {
        "tags": tags,
        "age_group": age_group,
        "summary": summary,
    }
