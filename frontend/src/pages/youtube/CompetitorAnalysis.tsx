import { Button, Card, Checkbox, Empty, InputNumber, message, Select, Space, Spin, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { compareCompetitorsApi, listYouTubeChannelsApi } from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";
import apiClient from "@/services/apiClient";
import { useChartColors } from "@/hooks/useChartColors";

const { Title, Text, Paragraph } = Typography;

type PoolItem = {
  pool_id: number;
  group_name: string;
  channel: {
    id: number;
    title: string;
  };
};

export default function CompetitorAnalysis() {
  const chartColors = useChartColors();
  const [pool, setPool] = useState<PoolItem[]>([]);
  const [selectedChannelIds, setSelectedChannelIds] = useState<number[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState<Array<Record<string, string | number>>>([]);
  // AI 洞察
  const [aiInsight, setAiInsight] = useState<Record<string, string> | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [modelOptions, setModelOptions] = useState<ModelItem[]>([]);
  const [agentOptions, setAgentOptions] = useState<PromptItem[]>([]);
  const [selectedModelLibId, setSelectedModelLibId] = useState<number | undefined>(undefined);
  const [selectedLlmModelName, setSelectedLlmModelName] = useState<string>("");
  const [selectedAgentId, setSelectedAgentId] = useState<number | undefined>(undefined);

  useEffect(() => {
    const loadConfigs = async () => {
      try {
        const [models, prompts] = await Promise.all([listModelsApi(), listPromptsApi()]);
        const chatModels = models.filter((m) => (m.library_kind ?? "chat") === "chat");
        setModelOptions(chatModels);
        setAgentOptions(prompts);
        if (chatModels.length > 0) {
          const first = chatModels[0];
          const firstName = ((first.supported_models_json || "").match(/"value"\s*:\s*"([^"]+)"/)?.[1] ?? "").trim();
          setSelectedModelLibId(first.id);
          setSelectedLlmModelName(firstName);
        }
        if (prompts.length > 0) setSelectedAgentId(prompts[0].id);
      } catch { /* 静默 */ }
    };
    void loadConfigs();
  }, []);

  // 所有库的模型名扁平化选项，选项值格式："{libId}::{modelName}"
  const allModelNameOpts = useMemo(
    () =>
      modelOptions.flatMap((lib) => {
        try {
          const parsed: Array<{ value?: string; label?: string } | string> = JSON.parse(
            lib.supported_models_json || "[]"
          );
          return parsed.flatMap((m) => {
            const name = typeof m === "string" ? m : (m.value ?? "");
            const display = typeof m === "string" ? m : (m.label ?? m.value ?? "");
            if (!name) return [];
            return [{
              value: `${lib.id}::${name}`,
              label: modelOptions.length > 1 ? `${display} (${lib.name})` : display,
            }];
          });
        } catch {
          return [];
        }
      }),
    [modelOptions]
  );

  useEffect(() => {
    (async () => {
      const rows = await listYouTubeChannelsApi();
      const mapped: PoolItem[] = rows.map((row) => ({
        pool_id: row.pool_id,
        group_name: row.group_name,
        channel: {
          id: row.channel.id,
          title: row.channel.title,
        },
      }));
      setPool(mapped);
    })().catch(() => message.error("加载监控池失败"));
  }, []);

  const selectedChannels = useMemo(
    () => pool.filter((p) => selectedChannelIds.includes(p.channel.id)),
    [pool, selectedChannelIds]
  );

  const onAnalyze = async () => {
    if (selectedChannelIds.length < 2 || selectedChannelIds.length > 3) {
      message.warning("请勾选 2-3 个频道进行对比");
      return;
    }
    setLoading(true);
    try {
      const data = await compareCompetitorsApi({ channel_ids: selectedChannelIds, days });
      setChartData(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "获取对比数据失败");
    } finally {
      setLoading(false);
    }
  };

  const onAiInsight = async () => {
    if (selectedChannelIds.length < 2) {
      message.warning("请先选择至少 2 个频道");
      return;
    }
    if (!selectedModelLibId || !selectedLlmModelName) {
      message.warning("请先选择模型名");
      return;
    }
    setAiLoading(true);
    setAiInsight(null);
    try {
      const res = await apiClient.post("/api/youtube/competitors/ai-insight", {
        channel_ids: selectedChannelIds,
        model_library_id: selectedModelLibId,
        llm_model_name: selectedLlmModelName,
        agent_id: selectedAgentId,
      });
      setAiInsight(res.data.insight);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "AI 竞对分析失败");
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-yc-bg-page p-6 md:p-10 text-yc-text-primary">
      <div className="max-w-7xl mx-auto space-y-6">
        <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm">
          <Title level={3} className="text-yc-text-primary" style={{ marginBottom: 8 }}>
            竞对洞察
          </Title>
          <Text className="text-yc-text-secondary">
            勾选 2-3 个监控频道，生成总播放量与订阅量增长趋势图。
          </Text>
          <div className="mt-4 flex flex-col gap-4">
            <Checkbox.Group
              value={selectedChannelIds}
              onChange={(values) => setSelectedChannelIds(values as number[])}
              className="flex flex-wrap gap-3"
            >
              {pool.map((item) => (
                <Checkbox key={item.pool_id} value={item.channel.id}>
                  <span className="text-yc-text-primary">
                    {item.channel.title}
                    <span className="text-yc-text-secondary ml-1">({item.group_name})</span>
                  </span>
                </Checkbox>
              ))}
            </Checkbox.Group>
            <div className="flex items-center gap-3">
              <span className="text-yc-text-secondary">回溯天数</span>
              <InputNumber min={7} max={180} value={days} onChange={(v) => setDays(Number(v ?? 30))} />
              <Button type="primary" onClick={onAnalyze} loading={loading}>
                生成对比图
              </Button>
            </div>
            {/* AI 模型选择 */}
            <div className="flex items-center gap-3 flex-wrap">
              <Select
                showSearch
                style={{ width: 240 }}
                placeholder="选择模型名"
                value={
                  selectedModelLibId !== undefined && selectedLlmModelName
                    ? `${selectedModelLibId}::${selectedLlmModelName}`
                    : undefined
                }
                onChange={(v: string) => {
                  const idx = v.indexOf("::");
                  setSelectedModelLibId(Number(v.slice(0, idx)));
                  setSelectedLlmModelName(v.slice(idx + 2));
                }}
                options={allModelNameOpts}
                filterOption={(input, opt) =>
                  String(opt?.label ?? "").toLowerCase().includes(input.toLowerCase())
                }
                allowClear
                onClear={() => { setSelectedModelLibId(undefined); setSelectedLlmModelName(""); }}
              />
              <Select
                style={{ width: 200 }}
                placeholder="AI 智能体"
                value={selectedAgentId}
                onChange={setSelectedAgentId}
                options={agentOptions.map((p) => ({ value: p.id, label: p.title }))}
                allowClear
              />
              <Button type="primary" ghost loading={aiLoading} onClick={onAiInsight}>
                AI 竞争分析
              </Button>
            </div>
          </div>
        </Card>

        <Spin spinning={loading}>
          {chartData.length === 0 ? (
            <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm">
              <Empty description="暂无图表数据，请先选择频道并生成" />
            </Card>
          ) : (
            <>
              <Card
                title={<span className="text-yc-text-primary">播放量增长趋势（total_views）</span>}
                className="!bg-yc-bg-card !border-yc-border !shadow-sm"
              >
                <div className="h-[360px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                      <XAxis dataKey="date" stroke={chartColors.axis} />
                      <YAxis stroke={chartColors.axis} />
                      <Tooltip contentStyle={{ backgroundColor: chartColors.tooltip.bg, border: `1px solid ${chartColors.tooltip.border}`, color: chartColors.tooltip.text }} />
                      <Legend />
                      {selectedChannels.map((item, idx) => (
                        <Line
                          key={`${item.channel.id}-views`}
                          type="monotone"
                          dataKey={`${item.channel.title}_views`}
                          stroke={chartColors.series[idx % chartColors.series.length]}
                          strokeWidth={2}
                          dot={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card
                title={<span className="text-yc-text-primary">订阅量增长趋势（subscriber_count）</span>}
                className="!bg-yc-bg-card !border-yc-border !shadow-sm"
              >
                <div className="h-[360px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                      <XAxis dataKey="date" stroke={chartColors.axis} />
                      <YAxis stroke={chartColors.axis} />
                      <Tooltip contentStyle={{ backgroundColor: chartColors.tooltip.bg, border: `1px solid ${chartColors.tooltip.border}`, color: chartColors.tooltip.text }} />
                      <Legend />
                      {selectedChannels.map((item, idx) => (
                        <Line
                          key={`${item.channel.id}-subs`}
                          type="monotone"
                          dataKey={`${item.channel.title}_subscriber_count`}
                          stroke={chartColors.series[idx % chartColors.series.length]}
                          strokeWidth={2}
                          dot={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </>
          )}
        </Spin>

        {/* AI 竞争分析结果 */}
        {aiInsight && (
          <Card title="AI 竞争格局分析" className="!bg-yc-bg-card !border-yc-border !shadow-sm">
            <div className="space-y-4">
              {aiInsight.positioning_diff && (
                <div><Text strong>定位差异</Text><Paragraph className="!mb-0">{aiInsight.positioning_diff}</Paragraph></div>
              )}
              {aiInsight.content_strategy_diff && (
                <div><Text strong>内容策略差异</Text><Paragraph className="!mb-0">{aiInsight.content_strategy_diff}</Paragraph></div>
              )}
              {aiInsight.audience_overlap && (
                <div><Text strong>受众重叠度</Text><Paragraph className="!mb-0">{aiInsight.audience_overlap}</Paragraph></div>
              )}
              {aiInsight.competitive_summary && (
                <div><Text strong>竞争格局总结</Text><Paragraph className="!mb-0">{aiInsight.competitive_summary}</Paragraph></div>
              )}
              {aiInsight.actionable_advice && (
                <div><Text strong>可操作建议</Text><Paragraph className="!mb-0">{aiInsight.actionable_advice}</Paragraph></div>
              )}
            </div>
          </Card>
        )}
        {aiLoading && (
          <div className="flex justify-center py-8"><Spin size="large" tip="AI 正在分析竞争格局…" /></div>
        )}
      </div>
    </div>
  );
}

