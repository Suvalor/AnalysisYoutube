import {
  Alert,
  Avatar,
  Button,
  Card,
  Drawer,
  Form,
  Input,
  InputNumber,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";
import {
  analyzeYouTubeBatchApi,
  blueOceanRadarScanApi,
  radarAiRetrospectiveApi,
  type BlueOceanChannelItem,
  type RadarAiRetrospectiveResponse,
} from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";
import { formatNumber } from "@/utils/format";

const { Title, Text, Link } = Typography;

type ScanFormValues = {
  keyword: string;
  published_after: 30 | 90 | 180;
  max_subscribers: number;
  outlier_multiplier: number;
  video_duration?: "short" | "medium" | "long";
};

function outlierTagColor(score: number): string {
  if (score >= 30) return "magenta";
  if (score >= 15) return "orange";
  if (score >= 10) return "gold";
  return "blue";
}

export default function BlueOceanRadar() {
  const [form] = Form.useForm<ScanFormValues>();
  const [scanning, setScanning] = useState(false);
  const [items, setItems] = useState<BlueOceanChannelItem[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [importedIds, setImportedIds] = useState<Set<string>>(() => new Set());
  const [addingId, setAddingId] = useState<string | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<RadarAiRetrospectiveResponse | null>(null);
  const [aiError, setAiError] = useState<string>("");
  const [modelOptions, setModelOptions] = useState<ModelItem[]>([]);
  const [agentOptions, setAgentOptions] = useState<PromptItem[]>([]);
  const [selectedModelLibId, setSelectedModelLibId] = useState<number | undefined>(undefined);
  const [selectedLlmModelName, setSelectedLlmModelName] = useState<string>("");
  const [selectedAgentId, setSelectedAgentId] = useState<number | undefined>(undefined);

  const columns: ColumnsType<BlueOceanChannelItem> = useMemo(
    () => [
      {
        title: "频道",
        key: "channel",
        width: 280,
        render: (_, row) => (
          <Space>
            <Avatar src={row.thumbnail_url ?? undefined} size={40}>
              {row.title?.slice(0, 1) ?? "?"}
            </Avatar>
            <div className="min-w-0">
              <div className="font-medium text-slate-900 truncate max-w-[200px]">{row.title}</div>
              <Text type="secondary" className="text-xs">
                {row.yt_channel_id}
              </Text>
            </div>
          </Space>
        ),
      },
      {
        title: "订阅数",
        dataIndex: "subscriber_count",
        sorter: (a, b) => a.subscriber_count - b.subscriber_count,
        render: (v: number) => formatNumber(v),
      },
      {
        title: "频道总播放",
        dataIndex: "total_views",
        sorter: (a, b) => a.total_views - b.total_views,
        render: (v: number) => formatNumber(v),
      },
      {
        title: "爆款视频",
        key: "viral",
        render: (_, row) => (
          <Link href={row.viral_video_url} target="_blank" rel="noopener noreferrer">
            打开 YouTube
          </Link>
        ),
      },
      {
        title: "播放量",
        dataIndex: "viral_view_count",
        sorter: (a, b) => a.viral_view_count - b.viral_view_count,
        render: (v: number) => formatNumber(v),
      },
      {
        title: "爆款系数",
        dataIndex: "outlier_score",
        sorter: (a, b) => a.outlier_score - b.outlier_score,
        defaultSortOrder: "descend",
        render: (v: number) => (
          <Tag color={outlierTagColor(v)} className="font-semibold">
            {v}
          </Tag>
        ),
      },
      {
        title: "操作",
        key: "action",
        width: 120,
        render: (_, row) => {
          const done = importedIds.has(row.yt_channel_id);
          return (
            <Button
              type="primary"
              size="small"
              disabled={done || addingId === row.yt_channel_id}
              loading={addingId === row.yt_channel_id}
              onClick={() => void handleImport(row)}
            >
              {done ? "已入库" : "入库关注"}
            </Button>
          );
        },
      },
    ],
    [importedIds, addingId]
  );

  const handleImport = async (row: BlueOceanChannelItem) => {
    setAddingId(row.yt_channel_id);
    try {
      await analyzeYouTubeBatchApi({ urls: row.channel_url, group_name: "蓝海雷达" });
      setImportedIds((prev) => new Set([...prev, row.yt_channel_id]));
      message.success("已提交入库任务");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? "入库失败");
    } finally {
      setAddingId(null);
    }
  };

  useEffect(() => {
    const loadAiConfigs = async () => {
      try {
        const [models, prompts] = await Promise.all([listModelsApi(), listPromptsApi()]);
        const chatModels = models.filter((m) => (m.library_kind ?? "chat") === "chat");
        setModelOptions(chatModels);
        setAgentOptions(prompts);
        if (chatModels.length > 0) {
          const first = chatModels[0];
          setSelectedModelLibId(first.id);
          const firstModelName =
            ((first.supported_models_json || "").match(/"value"\s*:\s*"([^"]+)"/)?.[1] ??
              (first.supported_models_json || "").match(/"([^"]+)"/)?.[1] ??
              "").trim();
          setSelectedLlmModelName(firstModelName);
        }
        if (prompts.length > 0) {
          setSelectedAgentId(prompts[0].id);
        }
      } catch {
        message.warning("加载 AI 模型/智能体配置失败，请前往设置中心检查");
      }
    };
    void loadAiConfigs();
  }, []);

  const openAiDrawer = async () => {
    if (!selectedModelLibId || !selectedLlmModelName || !selectedAgentId) {
      message.warning("请先在设置中心维护模型与智能体，并在本页完成选择");
      return;
    }
    setAiOpen(true);
    setAiLoading(true);
    setAiResult(null);
    setAiError("");
    try {
      const data = await radarAiRetrospectiveApi({
        lookback_days: 14,
        top_n: 8,
        model_library_id: selectedModelLibId,
        llm_model_name: selectedLlmModelName,
        agent_id: selectedAgentId,
      });
      setAiResult(data);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setAiError(err?.response?.data?.detail ?? "AI 复盘失败");
    } finally {
      setAiLoading(false);
    }
  };

  const appendKeyword = (kw: string) => {
    const current = String(form.getFieldValue("keyword") || "").trim();
    if (!current) {
      form.setFieldValue("keyword", kw);
      return;
    }
    if (current.includes(kw)) return;
    form.setFieldValue("keyword", `${current} ${kw}`);
  };

  const applyAiParams = () => {
    if (!aiResult) return;
    form.setFieldsValue({
      max_subscribers: aiResult.recommended_parameters.max_subscribers,
      outlier_multiplier: aiResult.recommended_parameters.outlier_multiplier,
    });
    setAiOpen(false);
    message.success("已应用 AI 推荐参数，可直接开始扫描");
  };

  const onScan = async () => {
    try {
      const values = await form.validateFields();
      setScanning(true);
      const payload: Parameters<typeof blueOceanRadarScanApi>[0] = {
        keyword: values.keyword.trim(),
        published_after: values.published_after,
        max_subscribers: values.max_subscribers,
        outlier_multiplier: values.outlier_multiplier,
      };
      if (values.video_duration) {
        payload.video_duration = values.video_duration;
      }
      const data = await blueOceanRadarScanApi(payload);
      setItems(data.items);
      setWarnings(data.warnings ?? []);
      if (data.items.length === 0) {
        message.info("没有符合筛选条件的频道，可放宽粉丝上限或降低爆款系数");
      } else {
        message.success(`扫描完成，共 ${data.items.length} 条`);
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; errorFields?: unknown };
      if (err?.errorFields) return;
      message.error(err?.response?.data?.detail ?? "扫描失败");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] p-6 md:p-10 text-slate-900">
      <div className="max-w-7xl mx-auto space-y-6">
        <Card className="!bg-white !border-slate-200 !shadow-sm">
          <Title level={3} style={{ color: "#0f172a", marginBottom: 8 }}>
            蓝海雷达
          </Title>
          <Text style={{ color: "#64748b" }}>
            自动发现粉丝量相对较低、但近期出现超高播放爆款视频的潜力对标频道。扫描结果仅保存在本页，不会写入数据库。
          </Text>
        </Card>

        <Card className="!bg-white !border-slate-200 !shadow-sm" title="搜索控制台">
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              published_after: 30,
              max_subscribers: 30000,
              outlier_multiplier: 10,
            }}
            className="max-w-3xl"
          >
            <Form.Item
              name="keyword"
              label="关键词"
              rules={[{ required: true, message: "请输入关键词" }]}
            >
              <Input placeholder="例如：AI 教程、健身跟练" allowClear />
            </Form.Item>
            <Form.Item name="published_after" label="发布时间范围">
              <Select
                options={[
                  { value: 30, label: "近 1 个月" },
                  { value: 90, label: "近 3 个月" },
                  { value: 180, label: "近半年" },
                ]}
              />
            </Form.Item>
            <Space wrap className="w-full" size="large">
              <Form.Item name="max_subscribers" label="粉丝上限（低于此值）" className="mb-0 min-w-[200px]">
                <InputNumber min={0} className="w-full" />
              </Form.Item>
              <Form.Item name="outlier_multiplier" label="爆款系数下限" className="mb-0 min-w-[200px]">
                <InputNumber min={0.1} step={0.5} className="w-full" />
              </Form.Item>
            </Space>
            <Form.Item name="video_duration" label="视频时长（可选）" className="mt-4">
              <Select
                allowClear
                placeholder="不限"
                options={[
                  { value: "short", label: "短视频（short）" },
                  { value: "medium", label: "中等（medium）" },
                  { value: "long", label: "长视频（long）" },
                ]}
              />
            </Form.Item>
            <Space className="mt-4" wrap>
              <Form.Item label="AI 模型配置" className="mb-0 min-w-[220px]">
                <Select
                  value={selectedModelLibId}
                  onChange={(v) => {
                    setSelectedModelLibId(v);
                    const target = modelOptions.find((x) => x.id === v);
                    const firstModelName =
                      ((target?.supported_models_json || "").match(/"value"\s*:\s*"([^"]+)"/)?.[1] ??
                        (target?.supported_models_json || "").match(/"([^"]+)"/)?.[1] ??
                        "").trim();
                    setSelectedLlmModelName(firstModelName);
                  }}
                  options={modelOptions.map((m) => ({ value: m.id, label: m.name }))}
                  placeholder="选择模型配置"
                />
              </Form.Item>
              <Form.Item label="模型名" className="mb-0 min-w-[260px]">
                <Input
                  value={selectedLlmModelName}
                  onChange={(e) => setSelectedLlmModelName(e.target.value)}
                  placeholder="例如 ep-xxxx / gpt-4o-mini"
                />
              </Form.Item>
              <Form.Item label="AI 智能体" className="mb-0 min-w-[220px]">
                <Select
                  value={selectedAgentId}
                  onChange={setSelectedAgentId}
                  options={agentOptions.map((p) => ({ value: p.id, label: p.title }))}
                  placeholder="选择提示词智能体"
                />
              </Form.Item>
            </Space>
            <Form.Item className="mb-0 mt-4">
              <Space wrap>
                <Button type="primary" size="large" loading={scanning} onClick={() => void onScan()}>
                  开始深度扫描
                </Button>
                <Button
                  size="large"
                  className="!text-purple-600 !border-purple-200 hover:!border-purple-400 hover:!text-purple-700"
                  onClick={() => void openAiDrawer()}
                >
                  ✨ AI 参数自进化
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>

        {warnings.length > 0 && (
          <Alert type="warning" showIcon message="部分数据未完整" description={
            <ul className="list-disc pl-4 mb-0">
              {warnings.map((w, i) => (
                <li key={`${i}-${w.slice(0, 40)}`}>{w}</li>
              ))}
            </ul>
          } />
        )}

        <Card className="!bg-white !border-slate-200 !shadow-sm" title="雷达扫描结果">
          <Table<BlueOceanChannelItem>
            rowKey={(r) => r.yt_channel_id}
            columns={columns}
            dataSource={items}
            pagination={{ pageSize: 10, showSizeChanger: true }}
            locale={{ emptyText: scanning ? "扫描中…" : "暂无数据，请先执行扫描" }}
          />
        </Card>
      </div>
      <Drawer
        title="AI 参数自进化复盘"
        placement="right"
        width={520}
        open={aiOpen}
        onClose={() => setAiOpen(false)}
      >
        {aiLoading ? (
          <div className="space-y-4">
            <Skeleton active paragraph={{ rows: 4 }} />
            <Skeleton active paragraph={{ rows: 6 }} />
          </div>
        ) : aiError ? (
          <Alert type="error" showIcon message="复盘失败" description={aiError} />
        ) : aiResult ? (
          <div className="space-y-4">
            <Card size="small" title="复盘摘要" className="!border-slate-200">
              <Text>{aiResult.analysis_summary}</Text>
            </Card>
            <Card size="small" title="推荐关键词" className="!border-slate-200">
              <Space wrap>
                {aiResult.recommended_parameters.suggested_keywords.length > 0 ? (
                  aiResult.recommended_parameters.suggested_keywords.map((kw) => (
                    <Tag
                      key={kw}
                      color="purple"
                      className="cursor-pointer"
                      onClick={() => appendKeyword(kw)}
                    >
                      {kw}
                    </Tag>
                  ))
                ) : (
                  <Text type="secondary">暂无关键词建议</Text>
                )}
              </Space>
            </Card>
            <Card size="small" title="推荐参数" className="!border-slate-200">
              <div className="space-y-2">
                <div>
                  <Text type="secondary">粉丝上限：</Text>
                  <Text strong>{formatNumber(aiResult.recommended_parameters.max_subscribers)}</Text>
                </div>
                <div>
                  <Text type="secondary">爆款系数：</Text>
                  <Text strong>{aiResult.recommended_parameters.outlier_multiplier}</Text>
                </div>
                <div>
                  <Text type="secondary">建议动作：</Text>
                  <Text>{aiResult.next_step_action}</Text>
                </div>
                <div>
                  <Text type="secondary">
                    样本覆盖：近 {aiResult.sample_meta.lookback_days} 天，高样本 {aiResult.sample_meta.top_count} 条，低样本{" "}
                    {aiResult.sample_meta.low_count} 条
                  </Text>
                </div>
              </div>
            </Card>
            <Button type="primary" size="large" block onClick={applyAiParams}>
              ⚡️ 采纳 AI 推荐参数
            </Button>
          </div>
        ) : (
          <Text type="secondary">暂无复盘数据</Text>
        )}
      </Drawer>
    </div>
  );
}
