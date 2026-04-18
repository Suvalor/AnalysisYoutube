import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Progress,
  Rate,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tabs,
  Tag,
  Timeline,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  WarningOutlined,
  ThunderboltOutlined,
  RocketOutlined,
  DollarOutlined,
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  RadarChartOutlined,
  GlobalOutlined,
  BarChartOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import { useEffect, useRef, useState } from "react";
import {
  getYouTubeQuotaDashboardApi,
  navigationGuideApi,
  navigationChatApi,
  blueOceanRadarScanApi,
  categoryOpportunityApi,
  crossRegionCompareApi,
  type NicheRecommendation,
  type AvoidNiche,
  type NavigationGuideResponse,
  type NavigationQuotaUsage,
  type QuotaCheckInfo,
  type RoadmapStep,
  type BlueOceanChannelItem,
  type CategoryOpportunityResponse,
  type CrossRegionCompareResponse,
} from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";

const { Title, Text, Paragraph } = Typography;

// ── 常量选项 ──

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
  { value: "zero", label: "零预算（纯AI制作）" },
  { value: "low", label: "低预算（个人/小团队）" },
  { value: "medium", label: "中预算（工作室）" },
  { value: "high", label: "高预算（公司级）" },
];

const MONETIZATION_OPTIONS = [
  { value: "adsense", label: "YouTube AdSense 广告收入" },
  { value: "course", label: "卖课 / 知识付费" },
  { value: "affiliate", label: "带货 / 联盟营销" },
  { value: "sponsor", label: "接商单 / 品牌合作" },
];

const REGION_OPTIONS = [
  { value: "US", label: "🇺🇸 美国" },
  { value: "GB", label: "🇬🇧 英国" },
  { value: "CA", label: "🇨🇦 加拿大" },
  { value: "AU", label: "🇦🇺 澳大利亚" },
  { value: "SG", label: "🇸🇬 新加坡" },
  { value: "MY", label: "🇲🇾 马来西亚" },
  { value: "PH", label: "🇵🇭 菲律宾" },
  { value: "VN", label: "🇻🇳 越南" },
  { value: "ID", label: "🇮🇩 印尼" },
  { value: "TH", label: "🇹🇭 泰国" },
  { value: "AE", label: "🇦🇪 阿联酋" },
  { value: "SA", label: "🇸🇦 沙特" },
  { value: "JP", label: "🇯🇵 日本" },
  { value: "KR", label: "🇰🇷 韩国" },
  { value: "DE", label: "🇩🇪 德国" },
  { value: "FR", label: "🇫🇷 法国" },
  { value: "BR", label: "🇧🇷 巴西" },
  { value: "IN", label: "🇮🇳 印度" },
];

const WEEKLY_HOURS_OPTIONS = [
  { value: "<5h", label: "< 5小时（兼职尝试）" },
  { value: "5-10h", label: "5-10小时（认真投入）" },
  { value: "10-20h", label: "10-20小时（半职投入）" },
  { value: "20h+", label: "20小时+（全职投入）" },
];

// ── 工具函数 ──

/** 解析模型配置的 supported_models_json 为下拉选项 */
type ModelNameOption = { value: string; label: string };

function parseModelNames(supportedModelsJson: string | null | undefined): ModelNameOption[] {
  const raw = supportedModelsJson?.trim();
  if (!raw) return [];
  try {
    const arr = JSON.parse(raw) as Array<string | { value?: string; label?: string }>;
    if (!Array.isArray(arr)) return [];
    return arr
      .map((item) => {
        if (typeof item === "string" && item.trim()) {
          return { value: item.trim(), label: item.trim() };
        }
        if (item && typeof item === "object" && item.value?.trim()) {
          return { value: item.value.trim(), label: item.label?.trim() || item.value.trim() };
        }
        return null;
      })
      .filter((x): x is ModelNameOption => x !== null);
  } catch {
    return [];
  }
}

function matchScoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 50) return "#f59e0b";
  return "#ef4444";
}

/** 配额仪表盘 */
function QuotaDashboardCard({ quotaCheck }: { quotaCheck: QuotaCheckInfo | null }) {
  const [quotaData, setQuotaData] = useState<{
    today_total: number; today_used: number; today_remaining: number;
  } | null>(null);

  useEffect(() => {
    const load = async () => {
      try { setQuotaData(await getYouTubeQuotaDashboardApi()); } catch { /* */ }
    };
    void load();
    const timer = setInterval(() => void load(), 60_000);
    return () => clearInterval(timer);
  }, []);

  const total = quotaCheck?.today_total ?? quotaData?.today_total ?? 10_000;
  const used = quotaCheck?.today_used ?? quotaData?.today_used ?? 0;
  const remaining = quotaCheck?.remaining ?? quotaData?.today_remaining ?? total;
  const pct = total > 0 ? Math.round((used / total) * 100) : 0;
  const isLow = remaining < total * 0.2;

  return (
    <Card className="!bg-white !border-slate-200 !shadow-sm" title="API 配额仪表盘" size="small">
      <div className="grid grid-cols-3 gap-4 mb-3">
        <Statistic title="今日总量" value={total.toLocaleString()} />
        <Statistic title="已用" value={used.toLocaleString()} />
        <Statistic title="剩余" value={remaining.toLocaleString()} valueStyle={{ color: isLow ? "#cf1322" : "#3f8600" }} />
      </div>
      <Progress percent={pct} status={isLow ? "exception" : "normal"} format={(p) => `${p}%`} />
      {isLow && <Text type="danger" className="block mt-2"><WarningOutlined /> 配额不足 20%</Text>}
    </Card>
  );
}

/** 配额消耗明细 */
function QuotaBreakdown({ usage }: { usage: NavigationQuotaUsage }) {
  return (
    <div className="text-sm text-slate-600 space-y-1">
      <div>search.list × {usage.search_calls} (100点/次) = {usage.search_calls * 100} 点</div>
      <div>channels.list × {usage.channels_calls} (1点/次) = {usage.channels_calls} 点</div>
      <div className="font-medium border-t pt-1 mt-1">本次合计：{usage.total_points} 点</div>
    </div>
  );
}

/** 推荐品类卡片 — 现代SaaS极简风 */
function NicheCard({ rec, index, isExpanded, onToggleExpand }: { rec: NicheRecommendation; index: number; isExpanded: boolean; onToggleExpand: () => void }) {
  const isHighGrowth = index === 2; // 第3个是高增长潜力品类

  return (
    <Card
      className={`!border-slate-200 !shadow-sm hover:!shadow-md transition-shadow duration-200 ${isHighGrowth ? "!border-amber-200 !bg-amber-50/30" : ""}`}
      bodyStyle={{ padding: 24 }}
    >
      {/* 顶部：品类名称 + 匹配度进度条 */}
      <div className="flex items-start justify-between mb-5">
        <div className="flex-1 mr-4">
          <div className="flex items-center gap-2 mb-1">
            {isHighGrowth && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
                <RocketOutlined className="mr-1" />高增长潜力
              </span>
            )}
            <Title level={4} style={{ margin: 0, color: "#0f172a" }}>{rec.niche_title}</Title>
          </div>
        </div>
        <div className="flex-shrink-0 w-28">
          <Progress
            type="dashboard"
            percent={rec.match_score}
            size={72}
            strokeColor={matchScoreColor(rec.match_score)}
            format={(p) => <span className="text-sm font-semibold">{p}</span>}
          />
          <div className="text-center text-xs text-slate-500 mt-1">匹配度</div>
        </div>
      </div>

      {/* 指标区：左右两栏 */}
      <div className="grid grid-cols-2 gap-x-8 gap-y-4 mb-5">
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">市场热度</Text>
          <div className="flex items-center gap-2 mt-1">
            <Rate disabled value={rec.market_heat_stars} className="!text-sm" />
            <span className="text-sm text-slate-600">{rec.market_heat_desc}</span>
          </div>
        </div>
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">竞争强度</Text>
          <div className="flex items-center gap-2 mt-1">
            <Rate disabled value={rec.competition_stars} className="!text-sm" />
            <span className="text-sm text-slate-600">{rec.competition_desc}</span>
          </div>
        </div>
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">内容缺口</Text>
          <div className="text-sm text-slate-700 mt-1">{rec.content_gap}</div>
        </div>
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">预估冷启动期</Text>
          <div className="text-sm text-slate-700 mt-1">{rec.cold_start_period}</div>
        </div>
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">对标频道</Text>
          <div className="text-sm text-slate-700 mt-1">{rec.target_channel_example}</div>
        </div>
        {rec.estimated_monthly_income && (
          <div>
            <Text type="secondary" className="text-xs uppercase tracking-wider">
              <DollarOutlined className="mr-1" />预估月收入
            </Text>
            <div className="text-base font-semibold text-emerald-600 mt-1">{rec.estimated_monthly_income}</div>
          </div>
        )}
      </div>

      {/* 行动路线图 Timeline */}
      {rec.action_roadmap && rec.action_roadmap.length > 0 && (
        <div className="mb-5">
          <Text type="secondary" className="text-xs uppercase tracking-wider block mb-2">
            <RocketOutlined className="mr-1" />30天行动路线图
          </Text>
          <Timeline
            items={rec.action_roadmap.map((step: RoadmapStep) => ({
              color: "blue",
              children: (
                <div>
                  <div className="text-sm font-medium text-slate-800">
                    Day {step.day_range}：{step.task}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">预期：{step.expected_result}</div>
                </div>
              ),
            }))}
          />
        </div>
      )}

      {/* 执行建议 */}
      <div className="bg-slate-50 rounded-lg p-4 mb-5">
        <Text type="secondary" className="text-xs uppercase tracking-wider block mb-1">执行建议</Text>
        <Paragraph className="!mb-0 text-sm text-slate-800 leading-relaxed">{rec.action_advice}</Paragraph>
      </div>

      {/* CTA：一键导入蓝海雷达 */}
      <Button
        type="primary"
        icon={<ThunderboltOutlined />}
        onClick={onToggleExpand}
        className="!rounded-lg"
      >
        {isExpanded ? "收起蓝海雷达分析" : "一键将此品类导入蓝海雷达"}
      </Button>
    </Card>
  );
}

/** 避坑卡片 — 精致警告色调 */
function AvoidNicheCard({ avoid }: { avoid: AvoidNiche }) {
  return (
    <Card className="!border-red-200 !bg-gradient-to-r !from-red-50 !to-orange-50 !shadow-sm" bodyStyle={{ padding: 20 }}>
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
          <WarningOutlined style={{ color: "#dc2626", fontSize: 16 }} />
        </div>
        <Title level={5} style={{ margin: 0, color: "#dc2626" }}>避坑提示</Title>
      </div>
      <div className="text-base font-medium text-red-700 mb-1">{avoid.niche_title}</div>
      <div className="text-sm text-red-600/80">{avoid.reason}</div>
    </Card>
  );
}

/** 追问区组件 */
function ChatArea({
  conversationId,
  modelLibraryId,
  llmModelName,
  agentId,
}: {
  conversationId: string | null;
  modelLibraryId?: number | null;
  llmModelName?: string | null;
  agentId?: number | null;
}) {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const onSend = async () => {
    if (!input.trim() || !conversationId) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setSending(true);
    try {
      const res = await navigationChatApi({
        conversation_id: conversationId,
        user_message: userMsg,
        model_library_id: modelLibraryId,
        llm_model_name: llmModelName,
        agent_id: agentId,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: res.assistant_message }]);
    } catch {
      message.error("追问失败，请重试");
    } finally {
      setSending(false);
      // 滚动到底部
      setTimeout(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
      }, 100);
    }
  };

  if (!conversationId) return null;

  return (
    <Card className="!bg-white !border-slate-200 !shadow-sm" bodyStyle={{ padding: 20 }}>
      <Title level={5} style={{ color: "#0f172a", marginBottom: 12 }}>
        <RobotOutlined className="mr-2" />追问 AI 分析师
      </Title>
      <Text type="secondary" className="text-xs block mb-3">
        对推荐结果有疑问？继续追问获取更深入的分析
      </Text>

      {/* 对话历史 */}
      {messages.length > 0 && (
        <div ref={scrollRef} className="max-h-64 overflow-y-auto space-y-3 mb-4 pr-2">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-slate-100 text-slate-800"
                }`}
              >
                <span className="mr-1 opacity-60">
                  {msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                </span>
                {msg.content}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 输入框 */}
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={() => void onSend()}
          placeholder="如：为什么推荐这个品类？有没有更保守的选择？"
          disabled={sending}
          className="!rounded-lg"
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          loading={sending}
          onClick={() => void onSend()}
          className="!rounded-lg"
        >
          追问
        </Button>
      </div>
    </Card>
  );
}

/** 蓝海雷达内嵌面板 — 在出海导航页面内展示 scan + 品类机会 + 跨地区对比 */
function RadarInlinePanel({
  keyword,
  region,
  onClose,
}: {
  keyword: string;
  region: string;
  onClose: () => void;
}) {
  const [scanItems, setScanItems] = useState<BlueOceanChannelItem[]>([]);
  const [scanLoading, setScanLoading] = useState(false);
  const [catOppResult, setCatOppResult] = useState<CategoryOpportunityResponse | null>(null);
  const [catOppLoading, setCatOppLoading] = useState(false);
  const [crossResult, setCrossResult] = useState<CrossRegionCompareResponse | null>(null);
  const [crossLoading, setCrossLoading] = useState(false);

  // 根据地区推断跨地区对比的默认地区组合
  const defaultCrossRegions = (() => {
    const regionGroups: Record<string, string[]> = {
      US: ["US", "GB", "CA"],
      GB: ["GB", "US", "DE"],
      SG: ["SG", "MY", "PH"],
      AE: ["AE", "SA", "IN"],
      JP: ["JP", "KR", "TW"],
    };
    return regionGroups[region] || ["US", "SG", "AE"];
  })();

  useEffect(() => {
    // 自动触发三项分析
    const runAll = async () => {
      // 1. 蓝海雷达扫描
      setScanLoading(true);
      try {
        const scanData = await blueOceanRadarScanApi({
          keyword,
          published_after: 90,
          max_subscribers: 30000,
          outlier_multiplier: 10,
        });
        setScanItems(scanData.items);
      } catch {
        message.error("蓝海雷达扫描失败");
      } finally {
        setScanLoading(false);
      }

      // 2. 品类机会
      setCatOppLoading(true);
      try {
        const catData = await categoryOpportunityApi({ keyword, region });
        setCatOppResult(catData);
      } catch {
        message.error("品类机会分析失败");
      } finally {
        setCatOppLoading(false);
      }

      // 3. 跨地区对比
      setCrossLoading(true);
      try {
        const crossData = await crossRegionCompareApi({
          keyword,
          regions: defaultCrossRegions,
          published_after: 90,
        });
        setCrossResult(crossData);
      } catch {
        message.error("跨地区对比失败");
      } finally {
        setCrossLoading(false);
      }
    };
    void runAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyword, region]);

  const scanColumns: ColumnsType<BlueOceanChannelItem> = [
    { title: "频道", dataIndex: "title", key: "title", width: 200, render: (v: string) => <span className="font-medium">{v}</span> },
    { title: "订阅", dataIndex: "subscriber_count", key: "sub", render: (v: number) => v.toLocaleString() },
    { title: "总播放", dataIndex: "total_views", key: "views", render: (v: number) => v.toLocaleString() },
    { title: "爆款播放", dataIndex: "viral_view_count", key: "viral", render: (v: number) => v.toLocaleString() },
    {
      title: "爆款系数", dataIndex: "outlier_score", key: "score", defaultSortOrder: "descend",
      render: (v: number) => <Tag color={v >= 30 ? "magenta" : v >= 15 ? "orange" : "blue"}>{v}</Tag>,
    },
  ];

  const anyLoading = scanLoading || catOppLoading || crossLoading;

  return (
    <Card
      className="!border-blue-200 !bg-blue-50/20 !shadow-md"
      title={
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <RadarChartOutlined style={{ color: "#3b82f6" }} />
            <span>蓝海雷达深度分析：{keyword}</span>
            {anyLoading && <Spin size="small" />}
          </span>
          <Button type="text" icon={<CloseOutlined />} onClick={onClose} size="small" />
        </div>
      }
      bodyStyle={{ padding: 20 }}
    >
      <Tabs
        defaultActiveKey="scan"
        items={[
          {
            key: "scan",
            label: <span><RadarChartOutlined className="mr-1" />深度扫描</span>,
            children: scanLoading ? (
              <div className="flex justify-center py-8"><Spin tip="扫描中…" /></div>
            ) : scanItems.length > 0 ? (
              <Table<BlueOceanChannelItem>
                rowKey="yt_channel_id"
                columns={scanColumns}
                dataSource={scanItems}
                size="small"
                pagination={{ pageSize: 5, showSizeChanger: true }}
              />
            ) : (
              <Text type="secondary">暂无扫描结果</Text>
            ),
          },
          {
            key: "category",
            label: <span><BarChartOutlined className="mr-1" />品类机会</span>,
            children: catOppLoading ? (
              <div className="flex justify-center py-8"><Spin tip="分析中…" /></div>
            ) : catOppResult ? (
              <div className="space-y-4">
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic title="新频道数" value={catOppResult.newcomer_stats.total_new_channels} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="成功频道" value={catOppResult.newcomer_stats.successful_channels} />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="成功率"
                      value={(catOppResult.newcomer_stats.success_rate * 100).toFixed(1)}
                      suffix="%"
                      valueStyle={{ color: catOppResult.newcomer_stats.success_rate > 0.2 ? "#3f8600" : "#cf1322" }}
                    />
                  </Col>
                </Row>
                {catOppResult.top_channels_growth.length > 0 && (
                  <Card size="small" title="头部频道增速" className="!border-slate-200">
                    <Table
                      dataSource={catOppResult.top_channels_growth}
                      rowKey="channel_id"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: "频道", dataIndex: "title", key: "title" },
                        { title: "订阅", dataIndex: "subscriber_count", key: "sub", render: (v: number) => v.toLocaleString() },
                        { title: "月增速%", dataIndex: "monthly_growth_rate", key: "rate", render: (v: number) => v.toFixed(1) },
                        { title: "趋势", dataIndex: "trend", key: "trend", render: (v: string) => <Tag color={v === "rising" ? "green" : v === "stable" ? "blue" : "red"}>{v}</Tag> },
                      ]}
                    />
                  </Card>
                )}
                {catOppResult.content_gaps.length > 0 && (
                  <Card size="small" title="内容缺口" className="!border-slate-200">
                    <Table
                      dataSource={catOppResult.content_gaps}
                      rowKey="duration_bucket"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: "时长", dataIndex: "duration_bucket", key: "dur" },
                        { title: "供给占比", dataIndex: "supply_ratio", key: "ratio", render: (v: number) => `${(v * 100).toFixed(1)}%` },
                        { title: "平均播放", dataIndex: "avg_views", key: "views", render: (v: number) => v.toLocaleString() },
                        { title: "机会分", dataIndex: "opportunity_score", key: "score", render: (v: number) => v.toFixed(1) },
                      ]}
                    />
                  </Card>
                )}
              </div>
            ) : (
              <Text type="secondary">暂无品类机会数据</Text>
            ),
          },
          {
            key: "cross-region",
            label: <span><GlobalOutlined className="mr-1" />跨地区对比</span>,
            children: crossLoading ? (
              <div className="flex justify-center py-8"><Spin tip="对比中…" /></div>
            ) : crossResult ? (
              <div className="space-y-4">
                <Table
                  dataSource={crossResult.regions}
                  rowKey="region_code"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: "地区", dataIndex: "region_name", key: "name" },
                    { title: "频道数", dataIndex: "channel_count", key: "count" },
                    { title: "平均播放", dataIndex: "avg_views", key: "views", render: (v: number) => v.toLocaleString() },
                    { title: "爆款中位数", dataIndex: "median_outlier_score", key: "score", render: (v: number) => v.toFixed(1) },
                    { title: "Top频道", dataIndex: "top_channel_title", key: "top" },
                    { title: "Top订阅", dataIndex: "top_channel_subscribers", key: "top_sub", render: (v: number) => v.toLocaleString() },
                  ]}
                />
                {crossResult.ai_recommendation && (
                  <Card size="small" title="AI 推荐" className="!border-slate-200">
                    <Text>{crossResult.ai_recommendation}</Text>
                  </Card>
                )}
              </div>
            ) : (
              <Text type="secondary">暂无跨地区对比数据</Text>
            ),
          },
        ]}
      />
    </Card>
  );
}

// ── 主页面 ──

export default function NavigationGuide() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<NicheRecommendation[]>([]);
  const [avoidNiche, setAvoidNiche] = useState<AvoidNiche | null>(null);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [quotaUsage, setQuotaUsage] = useState<NavigationQuotaUsage | null>(null);
  const [quotaCheck, setQuotaCheck] = useState<QuotaCheckInfo | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [channelInfo, setChannelInfo] = useState<Record<string, unknown> | null>(null);
  const [modelOptions, setModelOptions] = useState<ModelItem[]>([]);
  const [agentOptions, setAgentOptions] = useState<PromptItem[]>([]);
  const [llmModelNameOptions, setLlmModelNameOptions] = useState<ModelNameOption[]>([]);
  // 保存当前使用的 LLM 配置，供追问使用
  const [activeModelId, setActiveModelId] = useState<number | null>(null);
  const [activeModelName, setActiveModelName] = useState<string | null>(null);
  const [activeAgentId, setActiveAgentId] = useState<number | null>(null);
  // 蓝海雷达内嵌面板：记录当前展开的推荐索引
  const [expandedRadarIndex, setExpandedRadarIndex] = useState<number | null>(null);

  useEffect(() => {
    const loadConfigs = async () => {
      try {
        const [models, prompts] = await Promise.all([listModelsApi(), listPromptsApi()]);
        setModelOptions(models.filter((m) => (m.library_kind ?? "chat") === "chat"));
        setAgentOptions(prompts);
      } catch { /* */ }
    };
    void loadConfigs();
  }, []);

  const onSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      // llm_model_name 直接从表单获取（用户通过下拉选择）
      const llm_model_name = values.llm_model_name || undefined;
      // 保存当前 LLM 配置
      setActiveModelId(values.model_library_id ?? null);
      setActiveModelName(llm_model_name ?? null);
      setActiveAgentId(values.agent_id ?? null);

      const data = await navigationGuideApi({
        languages: values.languages,
        content_format: values.content_format,
        budget_level: values.budget_level,
        core_skills: values.core_skills,
        monetization_goal: values.monetization_goal,
        existing_channel_url: values.existing_channel_url || null,
        target_regions: values.target_regions || [],
        weekly_hours: values.weekly_hours || null,
        model_library_id: values.model_library_id,
        llm_model_name,
        agent_id: values.agent_id,
      });
      setRecommendations(data.recommendations);
      setAvoidNiche(data.avoid_niche ?? null);
      setAiSummary(data.ai_summary ?? null);
      setQuotaUsage(data.quota_usage ?? null);
      setQuotaCheck(data.quota_check ?? null);
      setConversationId(data.conversation_id ?? null);
      setChannelInfo(data.channel_info ?? null);
      if (data.recommendations.length === 0) {
        message.info("暂无推荐结果，请调整输入后重试");
      } else {
        message.success(`找到 ${data.recommendations.length} 个推荐品类`);
      }
    } catch (e: unknown) {
      const err = e as {
        response?: { data?: { detail?: string | { message?: string } }; status?: number };
        errorFields?: unknown;
      };
      if (err?.errorFields) return;
      if (err?.response?.status === 429) {
        const detail = err.response?.data?.detail;
        const msg = typeof detail === "object" ? detail?.message : detail;
        message.error({ content: msg ?? "API 配额不足，请稍后再试", duration: 5 });
      } else {
        const detail = err?.response?.data?.detail;
        const msg = typeof detail === "object" ? JSON.stringify(detail) : detail;
        message.error(msg ?? "导航推荐失败");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] p-6 md:p-10 text-slate-900">
      <div className="max-w-5xl mx-auto space-y-6">
        <QuotaDashboardCard quotaCheck={quotaCheck} />

        {/* 页面标题 */}
        <div className="mb-2">
          <Title level={3} style={{ color: "#0f172a", marginBottom: 4 }}>出海导航</Title>
          <Text style={{ color: "#64748b" }}>
            输入你的完整资源画像，AI 为你推演最适合的 YouTube 细分品类组合，并给出避坑建议。
          </Text>
        </div>

        {/* 表单 — 分组布局 */}
        <Card className="!bg-white !border-slate-200 !shadow-sm" bodyStyle={{ padding: 24 }}>
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              languages: ["中文"],
              content_format: ["video"],
              budget_level: "low",
              core_skills: [],
              target_regions: [],
            }}
            className="max-w-2xl"
          >
            {/* ── 基础画像 ── */}
            <div className="mb-2">
              <Text strong className="text-sm text-slate-500 uppercase tracking-wider">基础画像</Text>
              <div className="h-px bg-slate-200 mt-1 mb-4" />
            </div>

            <Form.Item name="languages" label="语言能力" rules={[{ required: true, message: "请选择至少一种语言" }]}>
              <Select mode="multiple" options={LANGUAGE_OPTIONS} placeholder="选择你会的语言" />
            </Form.Item>
            <Form.Item name="content_format" label="内容形式" rules={[{ required: true, message: "请选择内容形式" }]}>
              <Select mode="multiple" options={FORMAT_OPTIONS} placeholder="选择内容形式" />
            </Form.Item>
            <Form.Item name="budget_level" label="预算水平" rules={[{ required: true }]}>
              <Select options={BUDGET_OPTIONS} />
            </Form.Item>

            {/* ── 个性化画像 ── */}
            <div className="mb-2 mt-6">
              <Text strong className="text-sm text-slate-500 uppercase tracking-wider">个性化画像</Text>
              <div className="h-px bg-slate-200 mt-1 mb-4" />
            </div>

            <Form.Item
              name="core_skills"
              label="核心技能 / 内容方向"
              rules={[{ required: true, message: "请输入至少1个核心技能" }]}
              extra="这是破除同质化的关键，如：编程、美妆、恐怖故事、宠物"
            >
              <Select mode="tags" maxCount={3} placeholder="输入技能后按回车添加" />
            </Form.Item>
            <Form.Item name="monetization_goal" label="变现目标">
              <Select options={MONETIZATION_OPTIONS} placeholder="选择你的主要变现方式" allowClear />
            </Form.Item>
            <Form.Item name="target_regions" label="目标市场地区" extra="选择你希望进入的市场">
              <Select mode="multiple" options={REGION_OPTIONS} placeholder="选择目标地区" />
            </Form.Item>
            <Form.Item name="weekly_hours" label="每周可投入时间">
              <Select options={WEEKLY_HOURS_OPTIONS} placeholder="选择投入时间" allowClear />
            </Form.Item>

            {/* ── 已有频道 ── */}
            <div className="mb-2 mt-6">
              <Text strong className="text-sm text-slate-500 uppercase tracking-wider">已有频道（可选）</Text>
              <div className="h-px bg-slate-200 mt-1 mb-4" />
            </div>

            <Form.Item
              name="existing_channel_url"
              label="YouTube 频道 URL"
              extra="提供已有频道可让 AI 基于你现有内容给出更精准的推荐"
            >
              <Input placeholder="https://www.youtube.com/@yourchannel" allowClear />
            </Form.Item>

            {/* ── AI 配置 ── */}
            <div className="mb-2 mt-6">
              <Text strong className="text-sm text-slate-500 uppercase tracking-wider">AI 配置</Text>
              <div className="h-px bg-slate-200 mt-1 mb-4" />
            </div>

            <Space wrap className="w-full" size="large">
              <Form.Item name="model_library_id" label="AI 模型配置" className="mb-0 min-w-[200px]">
                <Select
                  options={modelOptions.map((m) => ({ value: m.id, label: m.name }))}
                  placeholder="可选"
                  allowClear
                  onChange={(value: number | undefined) => {
                    // 切换模型配置时，解析其支持的模型名称列表
                    const target = modelOptions.find((m) => m.id === value);
                    const names = parseModelNames(target?.supported_models_json);
                    setLlmModelNameOptions(names);
                    // 自动选中第一个模型名称
                    if (names.length > 0) {
                      form.setFieldsValue({ llm_model_name: names[0].value });
                    } else {
                      form.setFieldsValue({ llm_model_name: undefined });
                    }
                  }}
                />
              </Form.Item>
              <Form.Item name="llm_model_name" label="模型名称" className="mb-0 min-w-[200px]">
                <Select
                  options={llmModelNameOptions}
                  placeholder="选择模型配置后可选"
                  allowClear
                  disabled={llmModelNameOptions.length === 0}
                />
              </Form.Item>
              <Form.Item name="agent_id" label="AI 智能体" className="mb-0 min-w-[200px]">
                <Select options={agentOptions.map((p) => ({ value: p.id, label: p.title }))} placeholder="可选" allowClear />
              </Form.Item>
            </Space>

            <Form.Item className="mb-0 mt-6">
              <Button type="primary" size="large" loading={loading} onClick={() => void onSubmit()} className="!rounded-lg !px-8">
                开始深度推荐
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {loading && (
          <div className="flex flex-col items-center justify-center py-16">
            <Spin size="large" />
            <Text type="secondary" className="mt-4">AI 正在分析你的资源画像，推演最佳品类…</Text>
          </div>
        )}

        {/* 频道信息摘要 */}
        {!loading && channelInfo && (
          <Card className="!bg-blue-50/50 !border-blue-200 !shadow-sm" size="small" bodyStyle={{ padding: 16 }}>
            <div className="flex items-center gap-2 mb-1">
              <Text strong className="text-sm text-blue-700">已识别频道</Text>
            </div>
            <div className="text-sm text-slate-700">
              {String(channelInfo.title)} — {Number(channelInfo.subscriber_count).toLocaleString()} 订阅 · {Number(channelInfo.video_count)} 个视频
            </div>
          </Card>
        )}

        {!loading && aiSummary && (
          <Card className="!bg-white !border-slate-200 !shadow-sm" bodyStyle={{ padding: 16 }}>
            <Text>{aiSummary}</Text>
          </Card>
        )}

        {/* 推荐结果 */}
        {!loading && recommendations.length > 0 && (
          <div className="space-y-5">
            <Title level={4} style={{ color: "#0f172a" }}>推荐品类</Title>
            {recommendations.map((rec, i) => {
              const isExpanded = expandedRadarIndex === i;
              // 从 niche_title 提取关键词和地区
              const keyword = rec.niche_title.split(" - ")[0].split(" → ")[0].trim() || rec.niche_title;
              // 从 niche_title 提取地区代码（如 "美国" → "US"）
              const regionNameToCode: Record<string, string> = {
                "美国": "US", "英国": "GB", "加拿大": "CA", "澳大利亚": "AU",
                "新加坡": "SG", "马来西亚": "MY", "菲律宾": "PH", "越南": "VN",
                "印尼": "ID", "泰国": "TH", "阿联酋": "AE", "沙特": "SA",
                "日本": "JP", "韩国": "KR", "台湾": "TW", "香港": "HK",
                "德国": "DE", "法国": "FR", "巴西": "BR", "印度": "IN",
              };
              const regionPart = rec.niche_title.split("→").pop()?.trim() || "";
              const regionCode = regionNameToCode[regionPart] || "US";

              return (
                <div key={i} className="space-y-3">
                  <NicheCard
                    rec={rec}
                    index={i}
                    isExpanded={isExpanded}
                    onToggleExpand={() => setExpandedRadarIndex(isExpanded ? null : i)}
                  />
                  {isExpanded && (
                    <RadarInlinePanel
                      keyword={keyword}
                      region={regionCode}
                      onClose={() => setExpandedRadarIndex(null)}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 避坑提示 */}
        {!loading && avoidNiche && <AvoidNicheCard avoid={avoidNiche} />}

        {/* 追问区 */}
        {!loading && recommendations.length > 0 && (
          <ChatArea
            conversationId={conversationId}
            modelLibraryId={activeModelId}
            llmModelName={activeModelName}
            agentId={activeAgentId}
          />
        )}

        {/* 配额消耗明细 */}
        {!loading && quotaUsage && (
          <Card className="!bg-white !border-slate-200 !shadow-sm" title="本次 API 消耗明细" size="small">
            <QuotaBreakdown usage={quotaUsage} />
          </Card>
        )}
      </div>
    </div>
  );
}
