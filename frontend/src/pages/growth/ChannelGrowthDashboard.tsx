import { useState, useCallback } from "react";
import {
  Card,
  Row,
  Col,
  Statistic,
  Select,
  Button,
  Table,
  Tag,
  Space,
  Empty,
  Spin,
  message,
  Typography,
  Tooltip,
} from "antd";
import {
  UserAddOutlined,
  PlayCircleOutlined,
  VideoCameraOutlined,
  RiseOutlined,
  FallOutlined,
  MinusOutlined,
  ReloadOutlined,
  TrophyOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { channelGrowthApi } from "@/services/authApi";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

const { Title } = Typography;

interface GrowthDataPoint {
  date: string;
  subscribers: number;
  views: number;
  videos: number;
}

interface ChannelMetrics {
  pool_id: number;
  channel_id: string;
  title: string;
  thumbnail_url: string | null;
  current_subscribers: number;
  current_views: number;
  current_videos: number;
  subscriber_growth_rate: number;
  view_growth_rate: number;
  avg_views_per_video: number;
  engagement_score: number;
  growth_trend: "rising" | "stable" | "declining";
  growth_data: GrowthDataPoint[];
}

interface GrowthSummary {
  total_subscribers: number;
  total_views: number;
  total_videos: number;
  avg_subscriber_growth_rate: number;
  avg_view_growth_rate: number;
  fastest_growing_channel: string;
  fastest_growing_rate: number;
}

interface GrowthResponse {
  channels: ChannelMetrics[];
  summary: GrowthSummary;
  quota_used: number;
}

/** 格式化数字 */
function formatNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

/** 趋势标签 */
function TrendTag({ trend }: { trend: string }) {
  switch (trend) {
    case "rising":
      return (
        <Tag icon={<RiseOutlined />} color="success">
          Rising
        </Tag>
      );
    case "declining":
      return (
        <Tag icon={<FallOutlined />} color="error">
          Declining
        </Tag>
      );
    default:
      return (
        <Tag icon={<MinusOutlined />} color="default">
          Stable
        </Tag>
      );
  }
}

/** 互动得分颜色 */
function scoreColor(score: number): string {
  if (score >= 70) return "var(--color-success)";
  if (score >= 50) return "var(--color-primary)";
  if (score >= 30) return "var(--color-warning)";
  return "var(--color-danger)";
}

export default function ChannelGrowthDashboard() {
  const { t } = useTranslation("nav");
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<GrowthResponse | null>(null);
  const [days, setDays] = useState(30);
  const [selectedChannelIdx, setSelectedChannelIdx] = useState<number | null>(
    null
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await channelGrowthApi({ channel_ids: [], days });
      setData(res);
      if (res.channels.length > 0) setSelectedChannelIdx(0);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "Failed to fetch growth data");
    } finally {
      setLoading(false);
    }
  }, [days]);

  // 当前选中频道的增长数据
  const selectedChannel =
    selectedChannelIdx !== null ? data?.channels[selectedChannelIdx] : null;

  // 表格列
  const columns = [
    {
      title: "Channel",
      dataIndex: "title",
      key: "title",
      render: (text: string, _: ChannelMetrics, idx: number) => (
        <a onClick={() => setSelectedChannelIdx(idx)}>{text}</a>
      ),
    },
    {
      title: "Subscribers",
      dataIndex: "current_subscribers",
      key: "subscribers",
      sorter: (a: ChannelMetrics, b: ChannelMetrics) =>
        a.current_subscribers - b.current_subscribers,
      render: (v: number) => formatNum(v),
    },
    {
      title: "Views",
      dataIndex: "current_views",
      key: "views",
      sorter: (a: ChannelMetrics, b: ChannelMetrics) =>
        a.current_views - b.current_views,
      render: (v: number) => formatNum(v),
    },
    {
      title: "Sub Growth",
      dataIndex: "subscriber_growth_rate",
      key: "sub_growth",
      sorter: (a: ChannelMetrics, b: ChannelMetrics) =>
        a.subscriber_growth_rate - b.subscriber_growth_rate,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? "var(--color-stat-positive)" : "var(--color-stat-negative)" }}>
          {v >= 0 ? "+" : ""}
          {v.toFixed(1)}%
        </span>
      ),
    },
    {
      title: "View Growth",
      dataIndex: "view_growth_rate",
      key: "view_growth",
      sorter: (a: ChannelMetrics, b: ChannelMetrics) =>
        a.view_growth_rate - b.view_growth_rate,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? "var(--color-stat-positive)" : "var(--color-stat-negative)" }}>
          {v >= 0 ? "+" : ""}
          {v.toFixed(1)}%
        </span>
      ),
    },
    {
      title: "Engagement",
      dataIndex: "engagement_score",
      key: "engagement",
      sorter: (a: ChannelMetrics, b: ChannelMetrics) =>
        a.engagement_score - b.engagement_score,
      render: (v: number) => (
        <span style={{ color: scoreColor(v), fontWeight: 600 }}>
          {v.toFixed(0)}
        </span>
      ),
    },
    {
      title: "Trend",
      dataIndex: "growth_trend",
      key: "trend",
      render: (v: string) => <TrendTag trend={v} />,
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_: unknown, record: ChannelMetrics) => (
        <Button
          type="link"
          size="small"
          icon={<SearchOutlined />}
          onClick={() => navigate(`/keyword-research?keyword=${encodeURIComponent(record.title)}`)}
        >
          关键词
        </Button>
      ),
    },
  ];

  return (
    <div className="p-6">
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            {t("channelGrowth", "Channel Growth Dashboard")}
          </Title>
        </Col>
        <Col>
          <Space>
            <Select
              value={days}
              onChange={setDays}
              style={{ width: 120 }}
              options={[
                { label: "7 Days", value: 7 },
                { label: "14 Days", value: 14 },
                { label: "30 Days", value: 30 },
                { label: "90 Days", value: 90 },
              ]}
            />
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              loading={loading}
              onClick={fetchData}
            >
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      {loading && <Spin tip="Loading growth data..." />}

      {!loading && !data && (
        <Empty
          description="Click Refresh to load channel growth data from your competitor pool"
          style={{ marginTop: 80 }}
        />
      )}

      {!loading && data && (
        <>
          {/* 汇总统计卡片 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Total Subscribers"
                  value={data.summary.total_subscribers}
                  formatter={(v) => formatNum(v as number)}
                  prefix={<UserAddOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Total Views"
                  value={data.summary.total_views}
                  formatter={(v) => formatNum(v as number)}
                  prefix={<PlayCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Avg Sub Growth"
                  value={data.summary.avg_subscriber_growth_rate}
                  suffix="%"
                  valueStyle={{
                    color:
                      data.summary.avg_subscriber_growth_rate >= 0
                        ? "var(--color-stat-positive)"
                        : "var(--color-stat-negative)",
                  }}
                  prefix={
                    data.summary.avg_subscriber_growth_rate >= 0 ? (
                      <RiseOutlined />
                    ) : (
                      <FallOutlined />
                    )
                  }
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="Fastest Growing"
                  value={data.summary.fastest_growing_rate}
                  suffix="%"
                  prefix={<TrophyOutlined />}
                  valueStyle={{ color: "var(--color-warning)" }}
                />
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--color-text-tertiary)",
                    marginTop: 4,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {data.summary.fastest_growing_channel}
                </div>
              </Card>
            </Col>
          </Row>

          {/* 增长趋势图 */}
          {selectedChannel && selectedChannel.growth_data.length > 0 && (
            <Card
              title={`Growth Trend: ${selectedChannel.title}`}
              style={{ marginBottom: 24 }}
            >
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={selectedChannel.growth_data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis
                    yAxisId="subs"
                    orientation="left"
                    tickFormatter={(v: number) => formatNum(v)}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis
                    yAxisId="views"
                    orientation="right"
                    tickFormatter={(v: number) => formatNum(v)}
                    tick={{ fontSize: 12 }}
                  />
                  <RechartsTooltip
                    formatter={(value: number, name: string) => [
                      formatNum(value),
                      name,
                    ]}
                  />
                  <Legend />
                  <Line
                    yAxisId="subs"
                    type="monotone"
                    dataKey="subscribers"
                    stroke="var(--color-chart-1)"
                    strokeWidth={2}
                    dot={false}
                    name="Subscribers"
                  />
                  <Line
                    yAxisId="views"
                    type="monotone"
                    dataKey="views"
                    stroke="var(--color-chart-2)"
                    strokeWidth={2}
                    dot={false}
                    name="Views"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* 频道表格 */}
          <Card title="Channel Overview">
            <Table
              columns={columns}
              dataSource={data.channels}
              rowKey="channel_id"
              pagination={false}
              size="middle"
              rowClassName={(_, idx) =>
                idx === selectedChannelIdx ? "ant-table-row-selected" : ""
              }
            />
          </Card>
        </>
      )}
    </div>
  );
}
