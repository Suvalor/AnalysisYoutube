import { Button, Card, Input, Select, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  createScriptApi,
  listModelsApi,
  listPromptsApi,
  listStylesApi,
  type ModelItem,
  type PromptItem,
  type StyleItem,
} from "@/services/libraryApi";

const { Title, Text } = Typography;
const { TextArea } = Input;

type StreamMsg = {
  type: "delta" | "done" | "error";
  content?: string;
  message?: string;
};

type ModelOption = { value: string; label: string };

function toModelOptions(rows: ModelItem[]): ModelOption[] {
  const out: ModelOption[] = [];
  for (const row of rows) {
    const raw = row.supported_models_json?.trim();
    if (!raw) continue;
    try {
      const arr = JSON.parse(raw) as Array<string | { value?: string; label?: string }>;
      if (!Array.isArray(arr)) continue;
      for (const item of arr) {
        if (typeof item === "string" && item.trim()) {
          out.push({ value: item.trim(), label: `${row.name} / ${item.trim()}` });
        } else if (item && typeof item === "object" && item.value?.trim()) {
          out.push({ value: item.value.trim(), label: `${row.name} / ${item.label?.trim() || item.value.trim()}` });
        }
      }
    } catch {
      continue;
    }
  }
  return out;
}

export default function AICreator() {
  const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
  const [promptRows, setPromptRows] = useState<PromptItem[]>([]);
  const [styleRows, setStyleRows] = useState<StyleItem[]>([]);

  const [selectedModel, setSelectedModel] = useState<string>("");
  const [selectedPrompt, setSelectedPrompt] = useState<number | null>(null);
  const [selectedStyle, setSelectedStyle] = useState<number | null>(null);
  const [coreIdea, setCoreIdea] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedText, setGeneratedText] = useState("");
  const [optionsLoading, setOptionsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [models, prompts, styles] = await Promise.all([listModelsApi(), listPromptsApi(), listStylesApi()]);
        if (!mounted) return;
        const modelOps = toModelOptions(models);
        setModelOptions(modelOps);
        setPromptRows(prompts);
        setStyleRows(styles);
        const firstModel = modelOps[0]?.value ?? "";
        setSelectedModel((prev) => {
          if (prev && modelOps.some((m) => m.value === prev)) return prev;
          return firstModel;
        });
        setSelectedPrompt((prev) => (prev && prompts.some((p) => p.id === prev) ? prev : (prompts[0]?.id ?? null)));
        setSelectedStyle((prev) => (prev && styles.some((s) => s.id === prev) ? prev : (styles[0]?.id ?? null)));
      } catch (e: any) {
        if (!mounted) return;
        message.error(e?.response?.data?.detail ?? e?.message ?? "加载配置失败");
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
          selectedPrompt !== null &&
          selectedStyle !== null &&
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
    const promptRow = promptRows.find((x) => x.id === selectedPrompt);
    const styleRow = styleRows.find((x) => x.id === selectedStyle);
    if (!promptRow || !styleRow) {
      message.warning("请先在配置中心维护可用的智能体和风格");
      return;
    }
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
          prompt_template: promptRow.content,
          style: styleRow.content,
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

  const cardClass = "border border-slate-200 shadow-none bg-white rounded-lg [&_.ant-card-body]:bg-white";

  return (
    <div className="min-h-full bg-white p-4 md:p-8 text-slate-900">
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
                value={selectedPrompt ?? undefined}
                onChange={(v: number) => setSelectedPrompt(v)}
                options={promptRows.map((x) => ({ value: x.id, label: x.title }))}
                loading={optionsLoading}
                placeholder="请选择智能体"
              />
            </div>
            <div>
              <Text className="text-slate-600">选择风格</Text>
              <Select
                className="w-full mt-1"
                value={selectedStyle ?? undefined}
                onChange={(v: number) => setSelectedStyle(v)}
                options={styleRows.map((x) => ({ value: x.id, label: x.title }))}
                loading={optionsLoading}
                placeholder="请选择风格"
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
          <div className="min-h-[520px] rounded-lg border border-slate-200 bg-white p-4 whitespace-pre-wrap leading-7 text-slate-800">
            {generatedText || "点击「开始生成」后，这里会以打字机效果实时展示内容。"}
          </div>
        </Card>
      </div>
    </div>
  );
}
