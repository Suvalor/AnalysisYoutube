import { Button, Card, Input, Select, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { createScriptApi } from "@/services/libraryApi";
import { getScriptModelsApi, type ScriptModelOption } from "@/services/scriptsApi";
import { getUserSettingsApi } from "@/services/userApi";

const { Title, Text } = Typography;
const { TextArea } = Input;

const DEFAULT_PROMPT_OPTIONS = [
  { value: "short-video", label: "短视频脚本（带分镜）" },
  { value: "talking-head", label: "口播稿（单人出镜，信息密集）" },
  { value: "live-sale", label: "直播话术（转化导向）" },
  { value: "drama-multi-role", label: "剧情脚本（多角色对话）" },
];

const DEFAULT_STYLE_OPTIONS = [
  { value: "humor", label: "幽默搞笑" },
  { value: "professional", label: "专业权威" },
  { value: "storytelling", label: "故事叙事" },
  { value: "emotional", label: "情绪共鸣" },
];

type StreamMsg = {
  type: "delta" | "done" | "error";
  content?: string;
  message?: string;
};

function parseUiOptionsFromSettings(raw: string | null | undefined) {
  if (!raw?.trim()) {
    return {
      prompts: DEFAULT_PROMPT_OPTIONS,
      styles: DEFAULT_STYLE_OPTIONS,
    };
  }
  try {
    const o = JSON.parse(raw) as {
      prompts?: { value?: string; label?: string }[];
      styles?: { value?: string; label?: string }[];
    };
    const prompts = (o.prompts ?? [])
      .filter((x) => x?.value && x?.label)
      .map((x) => ({ value: String(x.value), label: String(x.label) }));
    const styles = (o.styles ?? [])
      .filter((x) => x?.value && x?.label)
      .map((x) => ({ value: String(x.value), label: String(x.label) }));
    return {
      prompts: prompts.length ? prompts : DEFAULT_PROMPT_OPTIONS,
      styles: styles.length ? styles : DEFAULT_STYLE_OPTIONS,
    };
  } catch {
    return {
      prompts: DEFAULT_PROMPT_OPTIONS,
      styles: DEFAULT_STYLE_OPTIONS,
    };
  }
}

export default function AICreator() {
  const [modelOptions, setModelOptions] = useState<ScriptModelOption[]>([]);
  const [promptOptions, setPromptOptions] = useState(DEFAULT_PROMPT_OPTIONS);
  const [styleOptions, setStyleOptions] = useState(DEFAULT_STYLE_OPTIONS);

  const [selectedModel, setSelectedModel] = useState<string>("");
  const [selectedPrompt, setSelectedPrompt] = useState<string>(DEFAULT_PROMPT_OPTIONS[0]!.value);
  const [selectedStyle, setSelectedStyle] = useState<string>(DEFAULT_STYLE_OPTIONS[0]!.value);
  const [coreIdea, setCoreIdea] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedText, setGeneratedText] = useState("");
  const [optionsLoading, setOptionsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [models, settings] = await Promise.all([getScriptModelsApi(), getUserSettingsApi()]);
        if (!mounted) return;
        const ui = parseUiOptionsFromSettings(settings.ai_prompt_config_json);
        setPromptOptions(ui.prompts);
        setStyleOptions(ui.styles);
        setModelOptions(models);
        const firstModel = models[0]?.value ?? "";
        setSelectedModel((prev) => {
          if (prev && models.some((m) => m.value === prev)) return prev;
          return firstModel;
        });
        setSelectedPrompt((prev) =>
          ui.prompts.some((p) => p.value === prev) ? prev : ui.prompts[0]!.value
        );
        setSelectedStyle((prev) =>
          ui.styles.some((s) => s.value === prev) ? prev : ui.styles[0]!.value
        );
      } catch (e: any) {
        if (!mounted) return;
        message.error(e?.response?.data?.detail ?? e?.message ?? "加载模型或设置失败");
        setModelOptions([]);
      } finally {
        if (mounted) setOptionsLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const canGenerate = useMemo(
    () =>
      Boolean(
        selectedModel &&
          selectedPrompt &&
          selectedStyle &&
          coreIdea.trim().length > 0 &&
          !generating &&
          !optionsLoading
      ),
    [selectedModel, selectedPrompt, selectedStyle, coreIdea, generating, optionsLoading]
  );

  const startGenerate = async () => {
    if (!coreIdea.trim()) {
      message.warning("请先填写创作主题/素材核心点");
      return;
    }
    if (!canGenerate) return;
    setGenerating(true);
    setGeneratedText("");
    try {
      const token = localStorage.getItem("access_token");
      const resp = await fetch("/api/v1/scripts/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token ?? ""}`,
        },
        body: JSON.stringify({
          model: selectedModel,
          prompt_template: selectedPrompt,
          style: selectedStyle,
          core_idea: coreIdea.trim(),
        }),
      });
      if (resp.status === 401) {
        localStorage.removeItem("access_token");
        if (!window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
        return;
      }
      if (!resp.ok || !resp.body) {
        throw new Error(`生成请求失败：${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const lines = frame.split("\n");
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6);
            if (!payload) continue;
            const parsed = JSON.parse(payload) as StreamMsg;
            if (parsed.type === "delta" && parsed.content) {
              setGeneratedText((prev) => prev + parsed.content);
            } else if (parsed.type === "error") {
              throw new Error(parsed.message || "生成出错");
            }
          }
        }
      }
    } catch (e: any) {
      message.error(e?.message ?? "生成失败");
    } finally {
      setGenerating(false);
    }
  };

  const saveScript = async () => {
    if (!generatedText.trim()) {
      message.warning("没有可保存内容");
      return;
    }
    try {
      await createScriptApi({
        title: coreIdea.slice(0, 60),
        content: generatedText,
      });
      message.success("已保存到剧本库");
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "保存失败");
    }
  };

  const cardClass =
    "border border-slate-200 shadow-sm bg-white rounded-lg [&_.ant-card-body]:bg-white";

  return (
    <div className="min-h-full bg-[#F8F9FA] p-4 md:p-8 text-slate-900">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className={`lg:col-span-1 ${cardClass}`}>
          <Title level={4} className="!mb-4 !text-slate-900">
            AI 创作控制台
          </Title>
          <div className="space-y-4">
            <div>
              <Text className="text-slate-600">选择模型</Text>
              <Select
                className="w-full mt-1"
                value={selectedModel || undefined}
                onChange={(v) => setSelectedModel(v)}
                options={modelOptions}
                loading={optionsLoading}
                placeholder="加载模型列表…"
              />
            </div>
            <div>
              <Text className="text-slate-600">选择提示词</Text>
              <Select
                className="w-full mt-1"
                value={selectedPrompt}
                onChange={(v) => setSelectedPrompt(v)}
                options={promptOptions}
                loading={optionsLoading}
              />
            </div>
            <div>
              <Text className="text-slate-600">选择风格</Text>
              <Select
                className="w-full mt-1"
                value={selectedStyle}
                onChange={(v) => setSelectedStyle(v)}
                options={styleOptions}
                loading={optionsLoading}
              />
            </div>
            <div>
              <Text className="text-slate-600">创作主题 / 素材核心点</Text>
              <TextArea
                rows={8}
                value={coreIdea}
                onChange={(e) => setCoreIdea(e.target.value)}
                placeholder="例如：围绕 2026 AI Agent 生产力工具，写一条 90 秒短视频脚本"
                className="mt-1"
              />
            </div>
            <Button type="primary" size="large" loading={generating} disabled={!canGenerate} onClick={startGenerate} block>
              开始生成
            </Button>
          </div>
        </Card>

        <Card className={`lg:col-span-2 ${cardClass}`}>
          <div className="flex items-center justify-between mb-4">
            <Title level={4} className="!m-0 !text-slate-900">
              剧本预览（实时流式）
            </Title>
            <Button onClick={saveScript} disabled={generating || !generatedText.trim()}>
              保存到剧本库
            </Button>
          </div>
          <div className="min-h-[520px] rounded-lg border border-slate-200 bg-slate-50 p-4 whitespace-pre-wrap leading-7 text-slate-800">
            {generatedText || "点击「开始生成」后，这里会以打字机效果实时展示内容。"}
          </div>
        </Card>
      </div>
    </div>
  );
}
