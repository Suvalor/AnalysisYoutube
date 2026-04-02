import json
from typing import Any

from fastapi import HTTPException, status

from app.services.config_manager import ResolvedIntegrationConfig, merge_integration_config
from app.services.llm_openai_factory import LLMClientFactory, LLMClientConfig, normalize_openai_base_url


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("模型返回为空")
    # 去掉 ``` / ```json 等 Markdown 代码块包裹，减少解析失败
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        while lines and lines[-1].strip() == "":
            lines.pop()
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
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
    integration: ResolvedIntegrationConfig | None = None,
) -> dict[str, str | list[str]]:
    """
    使用 OpenAI 兼容的 chat.completions 调用 LLM（适用于配置中心自建网关、火山 OpenAI 兼容端等）。
    未传 api_key/base_url/model 时，使用 integration 合并结果（默认同 merge_integration_config({})，即仅环境变量）。
    """
    icfg = integration if integration is not None else merge_integration_config({})
    key = (api_key or icfg.volcengine_api_key or "").strip()
    base = normalize_openai_base_url(base_url or icfg.volcengine_base_url)
    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=key, base_url=base, model_name=model or "")
    resolved_model = factory.resolve_model_name(cfg)
    if not key or not base or not resolved_model:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM 配置不完整：请检查 API Key、Base URL 与模型名（设置中心集成配置或环境变量 VOLCENGINE_*）",
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

    try:
        raw_content = await factory.chat_completions_content(
            cfg=cfg,
            temperature=0.35,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 分析调用失败: {exc}",
        ) from exc

    try:
        parsed = _extract_json_object(raw_content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 返回格式异常: {exc}；原始片段：{raw_content[:500]}",
        ) from exc

    return _parse_insight_result(parsed)


async def analyze_channel_info_sync(
    *,
    channel_title: str,
    channel_description: str,
    top_video_titles: list[str],
    merged_tags: list[str],
    hot_comments: list[str],
    integration: ResolvedIntegrationConfig,
    model: str | None = None,
) -> dict[str, Any]:
    """
    后台专用“频道信息打标签”分析器：强制非流式（non-stream）。

    物理隔离目标：
    - 不调用任何 stream_chat_completions_deltas / stream=True
    - 任何异常/超时/JSON 解析失败都不抛出，返回 tags=[] + expertise=""
    """
    # 降级默认值：不阻断入库流程
    fallback: dict[str, Any] = {"tags": [], "expertise": ""}

    api_key = (integration.volcengine_api_key or "").strip()
    base_url = normalize_openai_base_url(integration.volcengine_base_url)
    explicit = (model or "").strip()

    # 性价比模型选取：如果没有显式模型，则优先使用集成中的 endpoint_id；
    # 若是 Coding Plan 且 endpoint_id 为空，LLMClientFactory 将在该协议下提供默认 ark-code-latest。
    if not explicit:
        explicit = (integration.volcengine_endpoint_id or "").strip()

    if not api_key or not base_url:
        return fallback

    factory = LLMClientFactory()
    cfg = LLMClientConfig(api_key=api_key, base_url=base_url, model_name=explicit)

    try:
        resolved_model = factory.resolve_model_name(cfg)
        if not resolved_model:
            return fallback

        top_titles_text = "\n".join([f"- {x}" for x in top_video_titles]) if top_video_titles else "- 暂无视频标题数据"
        tags_text = ", ".join(merged_tags) if merged_tags else "暂无标签数据"
        comments_text = "\n".join([f"- {x}" for x in hot_comments]) if hot_comments else "- 暂无热门评论数据"

        system_prompt = (
            "你是一个资深的 YouTube 频道分析师。\n"
            "请根据用户提供的频道标题、频道简介、近期热门视频标题、视频标签与评论，提炼内容特征。\n"
            "要求：你必须返回合法的 JSON 格式，且只能包含以下字段：\n"
            '  "tags": 字符串数组；\n'
            '  "expertise": 字符串；\n'
            "禁止输出任何额外解释、Markdown、代码块标记（例如 ```）。\n"
        )

        user_prompt = (
            f"【频道标题】\n{channel_title}\n\n"
            f"【频道简介】\n{channel_description or '无'}\n\n"
            f"【播放量 Top10 视频标题】\n{top_titles_text}\n\n"
            f"【视频标签合并结果】\n{tags_text}\n\n"
            f"【热门评论（若有）】\n{comments_text}\n\n"
            "现在请输出 JSON（包含 tags 与 expertise）。"
        )

        raw_content = await factory.chat_completions_content(
            cfg=cfg,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        text = (raw_content or "").strip()
        if not text:
            return fallback

        # 清理可能的 ```json / ``` 包裹
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            while lines and lines[-1].strip() == "":
                lines.pop()
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # 再次兜底：尽可能截取 JSON 对象
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1].strip()

        import json as _json

        try:
            parsed = _json.loads(text)
        except _json.JSONDecodeError:
            return fallback

        tags_val = parsed.get("tags")
        expertise_val = parsed.get("expertise")

        tags_out: list[str] = []
        if isinstance(tags_val, list):
            for t in tags_val:
                s = str(t).strip()
                if s:
                    tags_out.append(s)
        tags_out = tags_out[:5]

        expertise_out = str(expertise_val or "").strip()

        return {"tags": tags_out, "expertise": expertise_out}
    except Exception:
        # 兜底：任何 AI/超时/网络异常都不抛出
        return fallback
