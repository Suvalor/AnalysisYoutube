import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  BulbOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  keywordResearchApi,
  type KeywordResearchResponse,
  type RelatedKeywordItem,
  type TopVideoItem,
} from "@/services/authApi";

const { Title, Text } = Typography;

const REGION_OPTIONS = [
  { value: "US", label: "🇺🇸 美国" },
  { value: "GB", label: "🇬🇧 英国" },
  { value: "JP", label: "🇯🇵 日本" },
  { value: "KR", label: "🇰🇷 韩国" },
  { value: "DE", label: "🇩🇪 德国" },
  { value: "FR", label: "🇫🇷 法国" },
  { value: "BR", label: "🇧🇷 巴西" },
  { value: "IN", label: "🇮🇳 印度" },
  { value: "SG", label: "🇸🇬 新加坡" },
  { value: "AE", label: "🇦🇪 阿联酋" },
];

const LANGUAGE_OPTIONS = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "ko", label: "한국어" },
  { value: "de", label: "Deutsch" },
  { value: "fr", label: "Français" },
  { value: "pt", label: "Português" },
  { value: "hi", label: "हिन्दी" },
  { value: "ar", label: "العربية" },
];

function volumeColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#f59e0b";
  return "#ef4444";
}

function competitionColor(score: number): string {
  if (score >= 70) return "#ef4444";
  if (score >= 40) return "#f59e0b";
  return "#22c55e";
}

function difficultyColor(score: number): string {
  if (score >= 70) return "#ef4444";
  if (score >= 40) return "#f59e0b";
  return "#22c55e";
}

function opportunityColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#f59e0b";
  return "#ef4444";
}

function trendIcon(direction: string) {
  switch (direction) {
    case "rising":
      return <ArrowUpOutlined style={{ color: "#22c55e" }} />;
    case "declining":
      return <ArrowDownOutlined style={{ color: "#ef4444" }} />;
    default:
      return <MinusOutlined style={{ color: "#f59e0b" }} />;
  }
}

function trendLabel(direction: string): string {
  switch (direction) {
    case "rising": return "上升";
    case "declining": return "下降";
    default: return "稳定";
  }
}

function trendTagColor(direction: string): string {
  switch (direction) {
    case "rising": return "success";
    case "declining": return "error";
    default: return "warning";
  }
}

function scoreLabel(score: number): string {
  if (score >= 80) return "极优";
  if (score >= 60) return "良好";
  if (score >= 40) return "中等";
  if (score >= 20) return "较差";
  return "极差";
}

function difficultyLabel(score: number): string {
  if (score >= 80) return "极难";
  if (score >= 60) return "困难";
  if (score >= 40) return "中等";
  if (score >= 20) return "容易";
  return "极易";
}

export default function KeywordResearch() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<KeywordResearchResponse | null>(null);
  const navigate = useNavigate();

  const onSearch = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const data = await keywordResearchApi({
        keyword: values.keyword,
        region: values.region || "US",
        language: values.language || "zh",
      });
      setResult(data);
      if (data.related_keywords.length > 0) {
        message.success(`找到 ${data.related_keywords.length} 个相关关键词`);
      }
    } catch (e: unknown) {
      const err = e as { errorFields?: unknown; response?: { data?: { detail?: string } } };
      if (err?.errorFields) return;
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === "object" ? JSON.stringify(detail) : detail;
      message.error(msg ?? "关键词研究失败");
    } finally {
      setLoading(false);
    }
  };

  const importToRadar = (keyword: string) => {
    navigate(`/blue-ocean-radar?keyword=${encodeURIComponent(keyword)}`);
  };

  const videoColumns: ColumnsType<TopVideoItem> = [
    {
      title: "频道",
      dataIndex: "channel_title",
      key: "channel",
      width: 200,
      render: (v: string) => <span className="font-medium">{v || "-"}</span>,
    },
    {
      title: "播放量",
      dataIndex: "view_count",
      key: "views",
      sorter: (a, b) => a.view_count - b.view_count,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: "点赞",
      dataIndex: "like_count",
      key: "likes",
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: "评论",
      dataIndex: "comment_count",
      key: "comments",
      render: (v: number) => v.toLocaleString(),
    },
  ];

  const relatedColumns: ColumnsType<RelatedKeywordItem> = [
    {
      title: "关键词",
      dataIndex: "keyword",
      key: "keyword",
      render: (v: string) => (
        <a
          className="cursor-pointer text-blue-600 hover:text-blue-800"
          onClick={() => {
            form.setFieldsValue({ keyword: v });
            void onSearch();
          }}
        >
          {v}
        </a>
      ),
    },
    {
      title: "搜索量评分",
      dataIndex: "search_volume_score",
      key: "volume",
      width: 140,
      sorter: (a, b) => a.search_volume_score - b.search_volume_score,
      render: (v: number) => (
        <div className="flex items-center gap-2">
          <Progress
            percent={v}
            size="small"
            strokeColor={volumeColor(v)}
            showInfo={false}
            style={{ width: 60 }}
          />
          <span style={{ color: volumeColor(v), fontWeight: 500 }}>{v}</span>
        </div>
      ),
    },
    {
      title: "竞争度",
      dataIndex: "competition_score",
      key: "competition",
      width: 140,
      sorter: (a, b) => a.competition_score - b.competition_score,
      render: (v: number) => (
        <div className="flex items-center gap-2">
          <Progress
            percent={v}
            size="small"
            strokeColor={competitionColor(v)}
            showInfo={false}
            style={{ width: 60 }}
          />
          <span style={{ color: competitionColor(v), fontWeight: 500 }}>{v}</span>
        </div>
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_: unknown, record: RelatedKeywordItem) => (
        <Button
          type="link"
          size="small"
          icon={<ThunderboltOutlined />}
          onClick={() => importToRadar(record.keyword)}
        >
          雷达
        </Button>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-[#F8F9FA] p-6 md:p-10 text-slate-900">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* 页面标题 */}
        <div className="mb-2">
          <Title level={3} style={{ color: "#0f172a", marginBottom: 4 }}>关键词研究</Title>
          <Text style={{ color: "#64748b" }}>
            输入关键词，分析搜索量、竞争度、难度和趋势，发现 YouTube 内容机会。
          </Text>
        </div>

        {/* 搜索表单 */}
        <Card className="!bg-white !border-slate-200 !shadow-sm" bodyStyle={{ padding: 24 }}>
          <Form form={form} layout="inline" initialValues={{ region: "US", language: "zh" }}>
            <Form.Item
              name="keyword"
              rules={[{ required: true, message: "请输入关键词" }]}
              className="flex-1 min-w-[200px]"
            >
              <Input
                size="large"
                placeholder="输入关键词，如：tech review, 美妆教程, cooking"
                onPressEnter={() => void onSearch()}
              />
            </Form.Item>
            <Form.Item name="region">
              <Select options={REGION_OPTIONS} size="large" style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="language">
              <Select options={LANGUAGE_OPTIONS} size="large" style={{ width: 120 }} />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                size="large"
                icon={<SearchOutlined />}
                loading={loading}
                onClick={() => void onSearch()}
                className="!rounded-lg"
              >
                分析
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {loading && (
          <div className="flex flex-col items-center justify-center py-16">
            <Spin size="large" />
            <Text type="secondary" className="mt-4">正在分析关键词数据…</Text>
          </div>
        )}

        {/* 分析结果 */}
        {!loading && result && (
          <>
            {/* 综合评分 + 趋势方向 */}
            <Row gutter={16}>
              <Col span={8}>
                <Card
                  className="!bg-white !border-slate-200 !shadow-sm"
                  bodyStyle={{ padding: 20 }}
                >
                  <Statistic
                    title="综合评分"
                    value={result.keyword_score}
                    suffix="/ 100"
                    valueStyle={{ color: volumeColor(result.keyword_score), fontSize: 32 }}
                  />
                  <Progress
                    percent={result.keyword_score}
                    strokeColor={volumeColor(result.keyword_score)}
                    showInfo={false}
                    className="mt-2"
                  />
                  <div className="mt-2 flex items-center gap-2">
                    <Tag color={volumeColor(result.keyword_score) === "#22c55e" ? "success" : volumeColor(result.keyword_score) === "#f59e0b" ? "warning" : "error"}>
                      {scoreLabel(result.keyword_score)}
                    </Tag>
                    <Text type="secondary" className="text-xs">
                      Volume×0.30 + Comp_inv×0.25 + KD_inv×0.25 + Opp×0.20
                    </Text>
                  </div>
                </Card>
              </Col>
              <Col span={8}>
                <Card
                  className="!bg-white !border-slate-200 !shadow-sm"
                  bodyStyle={{ padding: 20 }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Text type="secondary" className="text-sm">趋势方向</Text>
                    {trendIcon(result.trend_direction)}
                  </div>
                  <div className="flex items-center gap-3">
                    <Tag
                      color={trendTagColor(result.trend_direction)}
                      className="text-lg px-4 py-1"
                    >
                      {trendLabel(result.trend_direction)}
                    </Tag>
                    <div>
                      <Text strong style={{ fontSize: 20 }}>
                        {result.trend_direction === "rising" ? "↑" : result.trend_direction === "declining" ? "↓" : "→"}
                      </Text>
                    </div>
                  </div>
                  <div className="mt-3">
                    <Text type="secondary" className="text-xs">
                      {result.trend_direction === "rising"
                        ? "该关键词近期搜索活跃度上升，值得投入"
                        : result.trend_direction === "declining"
                        ? "该关键词热度正在下降，需谨慎投入"
                        : "该关键词热度稳定，可持续关注"}
                    </Text>
                  </div>
                </Card>
              </Col>
              <Col span={8}>
                <Card
                  className="!bg-white !border-slate-200 !shadow-sm"
                  bodyStyle={{ padding: 20 }}
                >
                  <Statistic
                    title="机会得分"
                    value={result.opportunity_score}
                    suffix="/ 100"
                    valueStyle={{ color: opportunityColor(result.opportunity_score), fontSize: 32 }}
                    prefix={<BulbOutlined />}
                  />
                  <Progress
                    percent={result.opportunity_score}
                    strokeColor={opportunityColor(result.opportunity_score)}
                    showInfo={false}
                    className="mt-2"
                  />
                  <div className="mt-2 flex items-center gap-2">
                    <Text type="secondary" className="text-xs">
                      内容缺口比率：{(result.content_gap_ratio * 100).toFixed(0)}%
                    </Text>
                    {result.content_gap_ratio > 0.3 && (
                      <Tag color="green" className="text-xs">缺口较大</Tag>
                    )}
                  </div>
                </Card>
              </Col>
            </Row>

            {/* 四维评分 */}
            <Row gutter={16}>
              <Col span={6}>
                <Card
                  className="!bg-white !border-slate-200 !shadow-sm"
                  bodyStyle={{ padding: 16 }}
                >
                  <div className="text-center">
                    <Text type="secondary" className="text-xs block mb-1">搜索量评分</Text>
                    <Progress
                      type="dashboard"
                      percent={result.search_volume_score}
                      size={90}
                      strokeColor={volumeColor(result.search_volume_score)}
                      format={(p) => <span style={{ fontSize: 18, fontWeight: 600 }}>{p}</span>}
                    />
                    <Text type="secondary" className="text-xs block mt-1">
                      估算 {result.total_results.toLocaleString()} 结果
                    </Text>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card
                  className="!bg-white !border-slate-200 !shadow-sm"
                  bodyStyle={{ padding: 16 }}
                >
                  <div className="text-center">
                    <Text type="secondary" className="text-xs block mb-1">竞争度</Text>
                    <Progress
                      type="dashboard"
                      percent={result.competition_score}
                      size={90}
                      strokeColor={competitionColor(result.competition_score)}
                      format={(p) => <span style={{ fontSize: 18, fontWeight: 600 }}>{p}</span>}
                    />
                    <Text type="secondary" className="text-xs block mt-1">
                      均订阅 {result.avg_channel_subscribers.toLocaleString()}
                    </Text>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card
                  className="!bg-white !border-slate-200 !shadow-sm"
                  bodyStyle={{ padding: 16 }}
                >
                  <div className="text-center">
                    <Text type="secondary" className="text-xs block mb-1">关键词难度 (KD)</Text>
                    <Progress
                      type="dashboard"
                      percent={result.keyword_difficulty}
                      size={90}
                      strokeColor={difficultyColor(result.keyword_difficulty)}
                      format={(p) => <span style={{ fontSize: 18, fontWeight: 600 }}>{p}</span>}
                    />
                    <Text type="secondary" className="text-xs block mt-1">
                      {difficultyLabel(result.keyword_difficulty)}
                    </Text>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card
                  className="!bg-white !border-slate-200 !shadow-sm"
                  bodyStyle={{ padding: 16 }}
                >
                  <div className="text-center">
                    <Text type="secondary" className="text-xs block mb-1">内容缺口</Text>
                    <Progress
                      type="dashboard"
                      percent={Math.round(result.content_gap_ratio * 100)}
                      size={90}
                      strokeColor={result.content_gap_ratio > 0.3 ? "#22c55e" : result.content_gap_ratio > 0.15 ? "#f59e0b" : "#94a3b8"}
                      format={(p) => <span style={{ fontSize: 18, fontWeight: 600 }}>{p}%</span>}
                    />
                    <Text type="secondary" className="text-xs block mt-1">
                      {result.content_gap_ratio > 0.3 ? "缺口大，机会多" : result.content_gap_ratio > 0.15 ? "有一定缺口" : "供给充足"}
                    </Text>
                  </div>
                </Card>
              </Col>
            </Row>

            {/* 趋势数据 */}
            <Card className="!bg-white !border-slate-200 !shadow-sm" title="趋势数据" bodyStyle={{ padding: 20 }}>
              <div className="grid grid-cols-4 gap-4">
                {result.trend_data.map((t) => {
                  const maxCount = Math.max(...result.trend_data.map((x) => x.result_count), 1);
                  const pct = Math.round((t.result_count / maxCount) * 100);
                  return (
                    <div key={t.period} className="text-center">
                      <Text type="secondary" className="text-xs block mb-1">{t.period}内</Text>
                      <Progress
                        type="dashboard"
                        percent={pct}
                        size={80}
                        strokeColor="#3b82f6"
                        format={() => (
                          <span className="text-xs">
                            {t.result_count > 1000000
                              ? `${(t.result_count / 1000000).toFixed(1)}M`
                              : t.result_count > 1000
                              ? `${(t.result_count / 1000).toFixed(0)}K`
                              : t.result_count}
                          </span>
                        )}
                      />
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* 相关关键词（带评分表格） */}
            {result.related_keywords_with_scores.length > 0 && (
              <Card
                className="!bg-white !border-slate-200 !shadow-sm"
                title="相关关键词"
                extra={<Text type="secondary" className="text-xs">点击关键词可重新搜索</Text>}
                bodyStyle={{ padding: 20 }}
              >
                <Table<RelatedKeywordItem>
                  rowKey="keyword"
                  columns={relatedColumns}
                  dataSource={result.related_keywords_with_scores}
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            )}

            {/* 热门视频 */}
            {result.top_videos.length > 0 && (
              <Card className="!bg-white !border-slate-200 !shadow-sm" title="热门视频" bodyStyle={{ padding: 20 }}>
                <Table<TopVideoItem>
                  rowKey={(_, i) => String(i)}
                  columns={videoColumns}
                  dataSource={result.top_videos}
                  size="small"
                  pagination={{ pageSize: 5 }}
                />
              </Card>
            )}

            {/* 导入蓝海雷达 */}
            <Card className="!bg-blue-50/50 !border-blue-200 !shadow-sm" bodyStyle={{ padding: 20 }}>
              <div className="flex items-center justify-between">
                <div>
                  <Text strong className="text-blue-700">将此关键词导入蓝海雷达深度扫描</Text>
                  <br />
                  <Text type="secondary" className="text-xs">
                    蓝海雷达将搜索该关键词下的低粉丝高爆款频道，验证品类机会
                  </Text>
                </div>
                <Space>
                  <Tag color="blue">API 调用 {result.search_calls} 次</Tag>
                  <Tag color="purple">相关频道 {result.channel_count} 个</Tag>
                  <Button
                    type="primary"
                    size="large"
                    icon={<ThunderboltOutlined />}
                    onClick={() => importToRadar(result.keyword)}
                    className="!rounded-lg"
                  >
                    导入蓝海雷达
                  </Button>
                </Space>
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
