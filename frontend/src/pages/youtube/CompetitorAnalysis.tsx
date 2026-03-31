import { Button, Card, Checkbox, Empty, InputNumber, message, Spin, Typography } from "antd";
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

const { Title, Text } = Typography;

type PoolItem = {
  pool_id: number;
  group_name: string;
  channel: {
    id: number;
    title: string;
  };
};

const lineColors = ["#60a5fa", "#34d399", "#f59e0b", "#f472b6"];

export default function CompetitorAnalysis() {
  const [pool, setPool] = useState<PoolItem[]>([]);
  const [selectedChannelIds, setSelectedChannelIds] = useState<number[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState<Array<Record<string, string | number>>>([]);

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

  return (
    <div className="min-h-screen bg-[#F8F9FA] p-6 md:p-10 text-slate-900">
      <div className="max-w-7xl mx-auto space-y-6">
        <Card className="!bg-white !border-slate-200 !shadow-sm">
          <Title level={3} style={{ color: "#0f172a", marginBottom: 8 }}>
            对标分析图表
          </Title>
          <Text style={{ color: "#64748b" }}>
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
                  <span className="text-slate-800">
                    {item.channel.title}
                    <span className="text-slate-500 ml-1">({item.group_name})</span>
                  </span>
                </Checkbox>
              ))}
            </Checkbox.Group>
            <div className="flex items-center gap-3">
              <span className="text-slate-700">回溯天数</span>
              <InputNumber min={7} max={180} value={days} onChange={(v) => setDays(Number(v ?? 30))} />
              <Button type="primary" onClick={onAnalyze} loading={loading}>
                生成对比图
              </Button>
            </div>
          </div>
        </Card>

        <Spin spinning={loading}>
          {chartData.length === 0 ? (
            <Card className="!bg-white !border-slate-200 !shadow-sm">
              <Empty description="暂无图表数据，请先选择频道并生成" />
            </Card>
          ) : (
            <>
              <Card
                title={<span className="text-slate-900">播放量增长趋势（total_views）</span>}
                className="!bg-white !border-slate-200 !shadow-sm"
              >
                <div className="h-[360px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="date" stroke="#64748b" />
                      <YAxis stroke="#64748b" />
                      <Tooltip />
                      <Legend />
                      {selectedChannels.map((item, idx) => (
                        <Line
                          key={`${item.channel.id}-views`}
                          type="monotone"
                          dataKey={`${item.channel.title}_views`}
                          stroke={lineColors[idx % lineColors.length]}
                          strokeWidth={2}
                          dot={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card
                title={<span className="text-slate-900">订阅量增长趋势（subscriber_count）</span>}
                className="!bg-white !border-slate-200 !shadow-sm"
              >
                <div className="h-[360px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="date" stroke="#64748b" />
                      <YAxis stroke="#64748b" />
                      <Tooltip />
                      <Legend />
                      {selectedChannels.map((item, idx) => (
                        <Line
                          key={`${item.channel.id}-subs`}
                          type="monotone"
                          dataKey={`${item.channel.title}_subscriber_count`}
                          stroke={lineColors[idx % lineColors.length]}
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
      </div>
    </div>
  );
}

