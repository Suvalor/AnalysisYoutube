import {
  Button,
  Card,
  Form,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from "antd";
import { useState } from "react";
import {
  navigationGuideApi,
  type CategoryRecommendation,
  type ChannelStrategyBreakdown,
} from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";
import { useEffect } from "react";

const { Title, Text } = Typography;

const LANGUAGE_OPTIONS = [
  { value: "中文", label: "中文" },
  { value: "英语", label: "英语" },
  { value: "日语", label: "日语" },
  { value: "韩语", label: "韩语" },
  { value: "阿拉伯语", label: "阿拉伯语" },
  { value: "西班牙语", label: "西班牙语" },
  { value: "法语", label: "法语" },
  { value: "德语", label: "德语" },
  { value: "葡萄牙语", label: "葡萄牙语" },
  { value: "印地语", label: "印地语" },
];

const FORMAT_OPTIONS = [
  { value: "video", label: "长视频" },
  { value: "short", label: "短视频" },
  { value: "live", label: "直播" },
];

const BUDGET_OPTIONS = [
  { value: "low", label: "低预算（个人/小团队）" },
  { value: "medium", label: "中预算（工作室）" },
  { value: "high", label: "高预算（公司级）" },
];

function fitScoreColor(score: number): string {
  if (score >= 70) return "green";
  if (score >= 40) return "orange";
  return "red";
}

function ChannelBreakdownCard({ channel }: { channel: ChannelStrategyBreakdown }) {
  return (
    <div className="border border-slate-200 rounded-lg p-3 space-y-1">
      <div className="font-medium text-slate-900">{channel.title}</div>
      <div className="text-xs text-slate-500">订阅 {channel.subscriber_count.toLocaleString()}</div>
      <div className="grid grid-cols-2 gap-1 text-xs text-slate-600">
        <span>发布频率：{channel.publish_frequency}</span>
        <span>平均时长：{channel.avg_duration}</span>
        <span>标题模式：{channel.title_pattern}</span>
        <span>标签模式：{channel.tag_pattern}</span>
      </div>
    </div>
  );
}

function RecommendationCard({ rec, index }: { rec: CategoryRecommendation; index: number }) {
  return (
    <Card
      className="!border-slate-200 !shadow-sm"
      title={
        <Space>
          <Tag color="blue">#{index + 1}</Tag>
          <span className="font-semibold">{rec.category}</span>
          <Tag>{rec.region}</Tag>
          <Tag color={fitScoreColor(rec.fit_score)}>匹配度 {rec.fit_score}</Tag>
        </Space>
      }
    >
      <Text type="secondary" className="block mb-3">{rec.reason}</Text>
      {rec.top_channels.length > 0 && (
        <div>
          <Text strong className="block mb-2">Top 频道策略拆解</Text>
          <div className="space-y-2">
            {rec.top_channels.map((ch) => (
              <ChannelBreakdownCard key={ch.channel_id} channel={ch} />
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export default function NavigationGuide() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<CategoryRecommendation[]>([]);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [modelOptions, setModelOptions] = useState<ModelItem[]>([]);
  const [agentOptions, setAgentOptions] = useState<PromptItem[]>([]);

  useEffect(() => {
    const loadConfigs = async () => {
      try {
        const [models, prompts] = await Promise.all([listModelsApi(), listPromptsApi()]);
        const chatModels = models.filter((m) => (m.library_kind ?? "chat") === "chat");
        setModelOptions(chatModels);
        setAgentOptions(prompts);
      } catch {
        // 静默失败，AI 功能可选
      }
    };
    void loadConfigs();
  }, []);

  const onSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      // 从选定的模型库中提取模型名
      let llm_model_name: string | undefined;
      if (values.model_library_id) {
        const target = modelOptions.find((m) => m.id === values.model_library_id);
        llm_model_name =
          ((target?.supported_models_json || "").match(/"value"\s*:\s*"([^"]+)"/)?.[1] ??
            (target?.supported_models_json || "").match(/"([^"]+)"/)?.[1] ??
            "").trim() || undefined;
      }
      const data = await navigationGuideApi({
        languages: values.languages,
        content_format: values.content_format,
        budget_level: values.budget_level,
        model_library_id: values.model_library_id,
        llm_model_name,
        agent_id: values.agent_id,
      });
      setRecommendations(data.recommendations);
      setAiSummary(data.ai_summary ?? null);
      if (data.recommendations.length === 0) {
        message.info("暂无匹配推荐，可调整语言或预算后重试");
      } else {
        message.success(`找到 ${data.recommendations.length} 个推荐组合`);
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; errorFields?: unknown };
      if (err?.errorFields) return;
      message.error(err?.response?.data?.detail ?? "导航推荐失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] p-6 md:p-10 text-slate-900">
      <div className="max-w-5xl mx-auto space-y-6">
        <Card className="!bg-white !border-slate-200 !shadow-sm">
          <Title level={3} style={{ color: "#0f172a", marginBottom: 8 }}>
            出海导航
          </Title>
          <Text style={{ color: "#64748b" }}>
            输入你的语言能力、内容形式和预算水平，为你推荐最适合的品类和地区组合，并拆解 Top 频道的内容策略。
          </Text>
        </Card>

        <Card className="!bg-white !border-slate-200 !shadow-sm" title="你的资源">
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              languages: ["中文"],
              content_format: ["video"],
              budget_level: "low",
            }}
            className="max-w-2xl"
          >
            <Form.Item
              name="languages"
              label="语言能力"
              rules={[{ required: true, message: "请选择至少一种语言" }]}
            >
              <Select mode="multiple" options={LANGUAGE_OPTIONS} placeholder="选择你会的语言" />
            </Form.Item>
            <Form.Item name="content_format" label="内容形式">
              <Select mode="multiple" options={FORMAT_OPTIONS} placeholder="选择内容形式" />
            </Form.Item>
            <Form.Item name="budget_level" label="预算水平">
              <Select options={BUDGET_OPTIONS} />
            </Form.Item>
            <Space wrap className="w-full" size="large">
              <Form.Item name="model_library_id" label="AI 模型配置" className="mb-0 min-w-[200px]">
                <Select
                  options={modelOptions.map((m) => ({ value: m.id, label: m.name }))}
                  placeholder="可选"
                  allowClear
                />
              </Form.Item>
              <Form.Item name="agent_id" label="AI 智能体" className="mb-0 min-w-[200px]">
                <Select
                  options={agentOptions.map((p) => ({ value: p.id, label: p.title }))}
                  placeholder="可选"
                  allowClear
                />
              </Form.Item>
            </Space>
            <Form.Item className="mb-0 mt-4">
              <Button type="primary" size="large" loading={loading} onClick={() => void onSubmit()}>
                开始导航推荐
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {loading && (
          <div className="flex justify-center py-12">
            <Spin size="large" tip="正在分析全球市场机会…" />
          </div>
        )}

        {!loading && aiSummary && (
          <Card className="!bg-white !border-slate-200 !shadow-sm" title="AI 导航总结">
            <Text>{aiSummary}</Text>
          </Card>
        )}

        {!loading && recommendations.length > 0 && (
          <div className="space-y-4">
            <Title level={4} style={{ color: "#0f172a" }}>推荐结果</Title>
            {recommendations.map((rec, i) => (
              <RecommendationCard key={`${rec.category}-${rec.region}`} rec={rec} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
