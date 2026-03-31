import { Button, Card, Input, Select, Typography, message } from "antd";
import { useEffect, useMemo, useState } from "react";
import { createScriptApi, listPromptsApi, listStylesApi, PromptItem, StyleItem } from "@/services/libraryApi";

const { Title, Text } = Typography;
const { TextArea } = Input;

type StreamMsg = {
  type: "delta" | "done" | "error";
  content?: string;
  message?: string;
};

export default function AICreator() {
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [styles, setStyles] = useState<StyleItem[]>([]);
  const [promptId, setPromptId] = useState<number | null>(null);
  const [styleId, setStyleId] = useState<number | null>(null);
  const [topic, setTopic] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedText, setGeneratedText] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [p, s] = await Promise.all([listPromptsApi(), listStylesApi()]);
        setPrompts(p);
        setStyles(s);
        if (p.length > 0) setPromptId(p[0].id);
        if (s.length > 0) setStyleId(s[0].id);
      } catch {
        message.error("加载提示词/风格失败");
      }
    })();
  }, []);

  const canGenerate = useMemo(
    () => Boolean(promptId && styleId && topic.trim().length > 0 && !generating),
    [promptId, styleId, topic, generating]
  );

  const startGenerate = async () => {
    if (!canGenerate) return;
    setGenerating(true);
    setGeneratedText("");
    try {
      const token = localStorage.getItem("access_token");
      const resp = await fetch("http://localhost:8000/api/ai/generate-script-stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token ?? ""}`,
        },
        body: JSON.stringify({
          prompt_id: promptId,
          style_id: styleId,
          topic: topic.trim(),
        }),
      });
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

        // SSE 最佳实践：按 \n\n 切割完整事件帧，避免 chunk 边界截断
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
        title: topic.slice(0, 60),
        content: generatedText,
        prompt_id: promptId,
        style_id: styleId,
      });
      message.success("已保存到剧本库");
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "保存失败");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 p-6 md:p-10 text-slate-100">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1 !bg-slate-900/80 !border-slate-800 shadow-2xl">
          <Title level={4} style={{ color: "#f8fafc" }}>
            AI 创作控制台
          </Title>
          <div className="space-y-4">
            <div>
              <Text style={{ color: "#cbd5e1" }}>选择提示词</Text>
              <Select
                className="w-full mt-1"
                value={promptId ?? undefined}
                onChange={(v) => setPromptId(v)}
                options={prompts.map((p) => ({ label: p.title, value: p.id }))}
              />
            </div>
            <div>
              <Text style={{ color: "#cbd5e1" }}>选择风格</Text>
              <Select
                className="w-full mt-1"
                value={styleId ?? undefined}
                onChange={(v) => setStyleId(v)}
                options={styles.map((s) => ({ label: s.title, value: s.id }))}
              />
            </div>
            <div>
              <Text style={{ color: "#cbd5e1" }}>创作主题 / 素材核心点</Text>
              <TextArea
                rows={8}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="例如：围绕 2026 AI Agent 生产力工具，写一条 90 秒短视频脚本"
                className="mt-1"
              />
            </div>
            <Button
              type="primary"
              size="large"
              loading={generating}
              disabled={!canGenerate}
              onClick={startGenerate}
              className="w-full !bg-fuchsia-500 !border-fuchsia-400 hover:!bg-fuchsia-400"
            >
              开始生成
            </Button>
          </div>
        </Card>

        <Card className="lg:col-span-2 !bg-slate-900/80 !border-slate-800 shadow-2xl">
          <div className="flex items-center justify-between mb-4">
            <Title level={4} style={{ color: "#f8fafc", margin: 0 }}>
              剧本预览（实时流式）
            </Title>
            <Button onClick={saveScript} disabled={generating || !generatedText.trim()}>
              保存到剧本库
            </Button>
          </div>
          <div className="min-h-[520px] rounded-xl border border-slate-800 bg-slate-950/70 p-4 whitespace-pre-wrap leading-7 text-slate-100">
            {generatedText || "点击“开始生成”后，这里会以打字机效果实时展示内容。"}
          </div>
        </Card>
      </div>
    </div>
  );
}

