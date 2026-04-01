import json
from typing import Any

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
        "请根据频道标题、频道简介、近期热门视频标题、视频标签与评论，提炼该博主的内容特征。\n"
        "请严格只输出一个 JSON 对象，不要输出任何额外文字或 Markdown。\n"
        "JSON 必须包含以下键：\n"
        '  "tags": 字符串数组，3～5 个中文核心标签；\n'
        '  "expertise": 字符串，一句话概括该博主「擅长做什么样的内容」、风格或领域（擅长内容）；\n'
        '  "summary": 字符串，频道定位或内容套路的补充说明，80 字以内；\n'
        '  "age_group": 字符串，可选，受众年龄段与性别倾向简述，无法判断时可写「未标注」。\n'
        "示例："
        '{"tags":["科技制作","硬核科普"],"expertise":"擅长用实体模型演示复杂物理概念","summary":"高信息密度解说+手工实验","age_group":"18-35岁偏男性"}'
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
    client = AsyncOpenAI(
        api_key=settings.volcengine_api_key,
        base_url=settings.volcengine_base_url,
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
    merged_input = f"{system_prompt}\n\n{user_prompt}".strip()

    def _extract_output_text(resp: Any) -> str:
        output_items = getattr(resp, "output", None)
        if output_items is None and hasattr(resp, "model_dump"):
            payload = resp.model_dump()
            output_items = payload.get("output")
        if not isinstance(output_items, list):
            return ""

        chunks: list[str] = []
        for item in output_items:
            item_type = getattr(item, "type", None)
            role = getattr(item, "role", None)
            content_list = getattr(item, "content", None)

            if item_type is None and isinstance(item, dict):
                item_type = item.get("type")
                role = item.get("role")
                content_list = item.get("content")

            if item_type != "message" or role != "assistant" or not isinstance(content_list, list):
                continue
            for content in content_list:
                c_type = getattr(content, "type", None)
                text = getattr(content, "text", None)
                if c_type is None and isinstance(content, dict):
                    c_type = content.get("type")
                    text = content.get("text")
                if c_type == "output_text" and text:
                    chunks.append(str(text))
        return "\n".join(chunks).strip()

    try:
        response = await client.responses.create(
            model=settings.volcengine_endpoint_id,
            input=merged_input,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 分析调用失败: {exc}",
        ) from exc

    raw_content = _extract_output_text(response)
    try:
        parsed = _extract_json_object(raw_content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 返回格式异常: {exc}",
        ) from exc

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
