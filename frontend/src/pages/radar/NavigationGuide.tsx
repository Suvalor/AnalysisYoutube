import {
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  Pagination,
  Popconfirm,
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
  HistoryOutlined,
  DeleteOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  getYouTubeQuotaDashboardApi,
  navigationGuideApi,
  navigationChatApi,
  blueOceanRadarScanApi,
  categoryOpportunityApi,
  crossRegionCompareApi,
  listNavigationRecordsApi,
  getNavigationRecordApi,
  deleteNavigationRecordApi,
  type NicheRecommendation,
  type AvoidNiche,
  type NavigationGuideResponse,
  type NavigationQuotaUsage,
  type QuotaCheckInfo,
  type RoadmapStep,
  type BlueOceanChannelItem,
  type CategoryOpportunityResponse,
  type CrossRegionCompareResponse,
  type NavigationGuideRecordItem,
  type NavigationGuideRecordDetail,
} from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";

const { Title, Text, Paragraph } = Typography;

// ── 工具函数 ──

function matchScoreColor(score: number): string {
  if (score >= 80) return "var(--color-success)";
  if (score >= 50) return "var(--color-warning)";
  return "var(--color-danger)";
}

/** 配额仪表盘 */
function QuotaDashboardCard({ quotaCheck }: { quotaCheck: QuotaCheckInfo | null }) {
  const { t } = useTranslation("navigation");
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
    <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm" title={t("quota.title")} size="small">
      <div className="grid grid-cols-3 gap-4 mb-3">
        <Statistic title={t("quota.todayTotal")} value={total.toLocaleString()} />
        <Statistic title={t("quota.used")} value={used.toLocaleString()} />
        <Statistic title={t("quota.remaining")} value={remaining.toLocaleString()} valueStyle={{ color: isLow ? "var(--color-danger)" : "var(--color-success)" }} />
      </div>
      <Progress percent={pct} status={isLow ? "exception" : "normal"} format={(p) => `${p}%`} />
      {isLow && <Text type="danger" className="block mt-2"><WarningOutlined /> {t("quota.lowWarning")}</Text>}
    </Card>
  );
}

/** 配额消耗明细 */
function QuotaBreakdown({ usage }: { usage: NavigationQuotaUsage }) {
  const { t } = useTranslation("navigation");
  return (
    <div className="text-sm text-yc-text-secondary space-y-1">
      <div>{t("breakdown.searchLine", { count: usage.search_calls, points: usage.search_calls * 100 })}</div>
      <div>{t("breakdown.channelsLine", { count: usage.channels_calls, points: usage.channels_calls })}</div>
      <div className="font-medium border-t pt-1 mt-1">{t("breakdown.totalLine", { points: usage.total_points })}</div>
    </div>
  );
}

/** 推荐品类卡片 — 现代SaaS极简风 */
function NicheCard({ rec, index, isExpanded, onToggleExpand }: { rec: NicheRecommendation; index: number; isExpanded: boolean; onToggleExpand: () => void }) {
  const { t } = useTranslation("navigation");
  const isHighGrowth = index === 2; // 第3个是高增长潜力品类

  return (
    <Card
      className={`!border-yc-border !shadow-sm hover:!shadow-md transition-shadow duration-200 ${isHighGrowth ? "!border-yc-warning !bg-yc-warning-bg/30" : ""}`}
      bodyStyle={{ padding: 24 }}
    >
      {/* 顶部：品类名称 + 匹配度进度条 */}
      <div className="flex items-start justify-between mb-5">
        <div className="flex-1 mr-4">
          <div className="flex items-center gap-2 mb-1">
            {isHighGrowth && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yc-warning-bg text-yc-warning">
                <RocketOutlined className="mr-1" />{t("card.highGrowth")}
              </span>
            )}
            <Title level={4} style={{ margin: 0, color: "var(--color-text-primary)" }}>{rec.niche_title}</Title>
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
          <div className="text-center text-xs text-yc-text-tertiary mt-1">{t("card.matchScore")}</div>
        </div>
      </div>

      {/* 指标区：左右两栏 */}
      <div className="grid grid-cols-2 gap-x-8 gap-y-4 mb-5">
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">{t("card.marketHeat")}</Text>
          <div className="flex items-center gap-2 mt-1">
            <Rate disabled value={rec.market_heat_stars} className="!text-sm" />
            <span className="text-sm text-yc-text-secondary">{rec.market_heat_desc}</span>
          </div>
        </div>
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">{t("card.competition")}</Text>
          <div className="flex items-center gap-2 mt-1">
            <Rate disabled value={rec.competition_stars} className="!text-sm" />
            <span className="text-sm text-yc-text-secondary">{rec.competition_desc}</span>
          </div>
        </div>
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">{t("card.contentGap")}</Text>
          <div className="text-sm text-yc-text-primary mt-1">{rec.content_gap}</div>
        </div>
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">{t("card.coldStart")}</Text>
          <div className="text-sm text-yc-text-primary mt-1">{rec.cold_start_period}</div>
        </div>
        <div>
          <Text type="secondary" className="text-xs uppercase tracking-wider">{t("card.targetChannel")}</Text>
          <div className="text-sm text-yc-text-primary mt-1">{rec.target_channel_example}</div>
        </div>
        {rec.estimated_monthly_income && (
          <div>
            <Text type="secondary" className="text-xs uppercase tracking-wider">
              <DollarOutlined className="mr-1" />{t("card.estimatedIncome")}
            </Text>
            <div className="text-base font-semibold text-yc-success mt-1">{rec.estimated_monthly_income}</div>
          </div>
        )}
      </div>

      {/* 行动路线图 Timeline */}
      {rec.action_roadmap && rec.action_roadmap.length > 0 && (
        <div className="mb-5">
          <Text type="secondary" className="text-xs uppercase tracking-wider block mb-2">
            <RocketOutlined className="mr-1" />{t("card.roadmap")}
          </Text>
          <Timeline
            items={rec.action_roadmap.map((step: RoadmapStep) => ({
              color: "blue",
              children: (
                <div>
                  <div className="text-sm font-medium text-yc-text-primary">
                    Day {step.day_range}：{step.task}
                  </div>
                  <div className="text-xs text-yc-text-tertiary mt-0.5">{t("card.expectedResult", { result: step.expected_result })}</div>
                </div>
              ),
            }))}
          />
        </div>
      )}

      {/* 执行建议 */}
      <div className="bg-yc-bg-inset rounded-lg p-4 mb-5">
        <Text type="secondary" className="text-xs uppercase tracking-wider block mb-1">{t("card.actionAdvice")}</Text>
        <Paragraph className="!mb-0 text-sm text-yc-text-primary leading-relaxed">{rec.action_advice}</Paragraph>
      </div>

      {/* CTA：一键导入蓝海雷达 */}
      <Button
        type="primary"
        icon={<ThunderboltOutlined />}
        onClick={onToggleExpand}
        className="!rounded-lg"
      >
        {isExpanded ? t("card.collapseRadar") : t("card.importRadar")}
      </Button>
    </Card>
  );
}

/** 避坑卡片 — 精致警告色调 */
function AvoidNicheCard({ avoid }: { avoid: AvoidNiche }) {
  const { t } = useTranslation("navigation");
  return (
    <Card className="!border-yc-danger !bg-yc-danger-bg/30 !shadow-sm" bodyStyle={{ padding: 20 }}>
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-full bg-yc-danger-bg flex items-center justify-center">
          <WarningOutlined style={{ color: "var(--color-danger)", fontSize: 16 }} />
        </div>
        <Title level={5} style={{ margin: 0, color: "var(--color-danger)" }}>{t("avoid.title")}</Title>
      </div>
      <div className="text-base font-medium text-yc-danger mb-1">{avoid.niche_title}</div>
      <div className="text-sm text-yc-danger/80">{avoid.reason}</div>
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
  const { t } = useTranslation("navigation");
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
      message.error(t("message.chatFailed"));
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
    <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm" bodyStyle={{ padding: 20 }}>
      <Title level={5} style={{ color: "var(--color-text-primary)", marginBottom: 12 }}>
        <RobotOutlined className="mr-2" />{t("chat.title")}
      </Title>
      <Text type="secondary" className="text-xs block mb-3">
        {t("chat.desc")}
      </Text>

      {/* 对话历史 */}
      {messages.length > 0 && (
        <div ref={scrollRef} className="max-h-64 overflow-y-auto space-y-3 mb-4 pr-2">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
	              <div
	                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
	                  msg.role === "user"
	                    ? "bg-yc-primary text-yc-text-inverse"
	                    : "bg-yc-bg-inset text-yc-text-primary"
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
          placeholder={t("chat.placeholder")}
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
          {t("chat.send")}
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
  const { t } = useTranslation("navigation");
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
        message.error(t("radar.scanFailed"));
      } finally {
        setScanLoading(false);
      }

      // 2. 品类机会
      setCatOppLoading(true);
      try {
        const catData = await categoryOpportunityApi({ keyword, region });
        setCatOppResult(catData);
      } catch {
        message.error(t("radar.categoryFailed"));
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
        message.error(t("radar.crossFailed"));
      } finally {
        setCrossLoading(false);
      }
    };
    void runAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyword, region]);

  const scanColumns: ColumnsType<BlueOceanChannelItem> = [
    { title: t("radar.table.channel"), dataIndex: "title", key: "title", width: 200, render: (v: string) => <span className="font-medium">{v}</span> },
    { title: t("radar.table.subscribers"), dataIndex: "subscriber_count", key: "sub", render: (v: number) => v.toLocaleString() },
    { title: t("radar.table.totalViews"), dataIndex: "total_views", key: "views", render: (v: number) => v.toLocaleString() },
    { title: t("radar.table.viralViews"), dataIndex: "viral_view_count", key: "viral", render: (v: number) => v.toLocaleString() },
    {
      title: t("radar.table.outlierScore"), dataIndex: "outlier_score", key: "score", defaultSortOrder: "descend",
      render: (v: number) => <Tag color={v >= 30 ? "magenta" : v >= 15 ? "orange" : "blue"}>{v}</Tag>,
    },
  ];

  const anyLoading = scanLoading || catOppLoading || crossLoading;

  return (
    <Card
      className="!border-yc-primary-border !bg-yc-primary-bg/20 !shadow-md"
      title={
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <RadarChartOutlined style={{ color: "var(--color-primary)" }} />
            <span>{t("radar.panelTitle", { keyword })}</span>
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
            label: <span><RadarChartOutlined className="mr-1" />{t("radar.deepScan")}</span>,
            children: scanLoading ? (
              <div className="flex justify-center py-8"><Spin tip={t("radar.scanning")} /></div>
            ) : scanItems.length > 0 ? (
              <Table<BlueOceanChannelItem>
                rowKey="yt_channel_id"
                columns={scanColumns}
                dataSource={scanItems}
                size="small"
                pagination={{ pageSize: 5, showSizeChanger: true }}
              />
            ) : (
              <Text type="secondary">{t("radar.noScanResults")}</Text>
            ),
          },
          {
            key: "category",
            label: <span><BarChartOutlined className="mr-1" />{t("radar.categoryOpp")}</span>,
            children: catOppLoading ? (
              <div className="flex justify-center py-8"><Spin tip={t("radar.scanning")} /></div>
            ) : catOppResult ? (
              <div className="space-y-4">
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic title={t("radar.table.newChannels")} value={catOppResult.newcomer_stats.total_new_channels} />
                  </Col>
                  <Col span={8}>
                    <Statistic title={t("radar.table.successfulChannels")} value={catOppResult.newcomer_stats.successful_channels} />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title={t("radar.table.successRate")}
                      value={(catOppResult.newcomer_stats.success_rate * 100).toFixed(1)}
                      suffix="%"
                      valueStyle={{ color: catOppResult.newcomer_stats.success_rate > 0.2 ? "var(--color-success)" : "var(--color-danger)" }}
                    />
                  </Col>
                </Row>
                {catOppResult.top_channels_growth.length > 0 && (
                  <Card size="small" title={t("radar.table.topGrowth")} className="!border-yc-border">
                    <Table
                      dataSource={catOppResult.top_channels_growth}
                      rowKey="channel_id"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: t("radar.table.channel"), dataIndex: "title", key: "title" },
                        { title: t("radar.table.subscribers"), dataIndex: "subscriber_count", key: "sub", render: (v: number) => v.toLocaleString() },
                        { title: t("radar.table.monthlyGrowth"), dataIndex: "monthly_growth_rate", key: "rate", render: (v: number) => v.toFixed(1) },
                        { title: t("radar.table.trend"), dataIndex: "trend", key: "trend", render: (v: string) => <Tag color={v === "rising" ? "green" : v === "stable" ? "blue" : "red"}>{v}</Tag> },
                      ]}
                    />
                  </Card>
                )}
                {catOppResult.content_gaps.length > 0 && (
                  <Card size="small" title={t("card.contentGap")} className="!border-yc-border">
                    <Table
                      dataSource={catOppResult.content_gaps}
                      rowKey="duration_bucket"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: t("radar.table.duration"), dataIndex: "duration_bucket", key: "dur" },
                        { title: t("radar.table.supplyRatio"), dataIndex: "supply_ratio", key: "ratio", render: (v: number) => `${(v * 100).toFixed(1)}%` },
                        { title: t("radar.table.avgViews"), dataIndex: "avg_views", key: "views", render: (v: number) => v.toLocaleString() },
                        { title: t("radar.table.opportunityScore"), dataIndex: "opportunity_score", key: "score", render: (v: number) => v.toFixed(1) },
                      ]}
                    />
                  </Card>
                )}
              </div>
            ) : (
              <Text type="secondary">{t("radar.noScanResults")}</Text>
            ),
          },
          {
            key: "cross-region",
            label: <span><GlobalOutlined className="mr-1" />{t("radar.crossRegion")}</span>,
            children: crossLoading ? (
              <div className="flex justify-center py-8"><Spin tip={t("radar.comparing")} /></div>
            ) : crossResult ? (
              <div className="space-y-4">
                <Table
                  dataSource={crossResult.regions}
                  rowKey="region_code"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: t("radar.table.region"), dataIndex: "region_name", key: "name" },
                    { title: t("radar.table.channelCount"), dataIndex: "channel_count", key: "count" },
                    { title: t("radar.table.avgViews"), dataIndex: "avg_views", key: "views", render: (v: number) => v.toLocaleString() },
                    { title: t("radar.table.medianScore"), dataIndex: "median_outlier_score", key: "score", render: (v: number) => v.toFixed(1) },
                    { title: t("radar.table.topChannel"), dataIndex: "top_channel_title", key: "top" },
                    { title: t("radar.table.topSubscribers"), dataIndex: "top_channel_subscribers", key: "top_sub", render: (v: number) => v.toLocaleString() },
                  ]}
                />
                {crossResult.ai_recommendation && (
                  <Card size="small" title={t("radar.table.aiRecommendation")} className="!border-yc-border">
                    <Text>{crossResult.ai_recommendation}</Text>
                  </Card>
                )}
              </div>
            ) : (
              <Text type="secondary">{t("radar.noCrossResults")}</Text>
            ),
          },
        ]}
      />
    </Card>
  );
}

// ── 主页面 ──

export default function NavigationGuide() {
  const { t } = useTranslation("navigation");

  // ── 国际化选项 ──
  const LANGUAGE_OPTIONS = useMemo(() => [
    { value: "中文", label: t("option.langChinese") },
    { value: "英语", label: t("option.langEnglish") },
    { value: "日语", label: t("option.langJapanese") },
    { value: "韩语", label: t("option.langKorean") },
    { value: "阿拉伯语", label: t("option.langArabic") },
    { value: "西班牙语", label: t("option.langSpanish") },
    { value: "法语", label: t("option.langFrench") },
    { value: "德语", label: t("option.langGerman") },
    { value: "葡萄牙语", label: t("option.langPortuguese") },
    { value: "印地语", label: t("option.langHindi") },
  ], [t]);

  const FORMAT_OPTIONS = useMemo(() => [
    { value: "video", label: t("option.formatVideo") },
    { value: "short", label: t("option.formatShort") },
    { value: "live", label: t("option.formatLive") },
  ], [t]);

  const BUDGET_OPTIONS = useMemo(() => [
    { value: "zero", label: t("option.budgetZero") },
    { value: "low", label: t("option.budgetLow") },
    { value: "medium", label: t("option.budgetMedium") },
    { value: "high", label: t("option.budgetHigh") },
  ], [t]);

  const MONETIZATION_OPTIONS = useMemo(() => [
    { value: "adsense", label: t("option.monetizeAdsense") },
    { value: "course", label: t("option.monetizeCourse") },
    { value: "affiliate", label: t("option.monetizeAffiliate") },
    { value: "sponsor", label: t("option.monetizeSponsor") },
  ], [t]);

  const REGION_OPTIONS = useMemo(() => [
    { value: "US", label: `🇺🇸 ${t("region.US")}` },
    { value: "GB", label: `🇬🇧 ${t("region.GB")}` },
    { value: "CA", label: `🇨🇦 ${t("region.CA")}` },
    { value: "AU", label: `🇦🇺 ${t("region.AU")}` },
    { value: "SG", label: `🇸🇬 ${t("region.SG")}` },
    { value: "MY", label: `🇲🇾 ${t("region.MY")}` },
    { value: "PH", label: `🇵🇭 ${t("region.PH")}` },
    { value: "VN", label: `🇻🇳 ${t("region.VN")}` },
    { value: "ID", label: `🇮🇩 ${t("region.ID")}` },
    { value: "TH", label: `🇹🇭 ${t("region.TH")}` },
    { value: "AE", label: `🇦🇪 ${t("region.AE")}` },
    { value: "SA", label: `🇸🇦 ${t("region.SA")}` },
    { value: "JP", label: `🇯🇵 ${t("region.JP")}` },
    { value: "KR", label: `🇰🇷 ${t("region.KR")}` },
    { value: "DE", label: `🇩🇪 ${t("region.DE")}` },
    { value: "FR", label: `🇫🇷 ${t("region.FR")}` },
    { value: "BR", label: `🇧🇷 ${t("region.BR")}` },
    { value: "IN", label: `🇮🇳 ${t("region.IN")}` },
  ], [t]);

  const WEEKLY_HOURS_OPTIONS = useMemo(() => [
    { value: "<5h", label: t("option.hoursLt5") },
    { value: "5-10h", label: t("option.hours5to10") },
    { value: "10-20h", label: t("option.hours10to20") },
    { value: "20h+", label: t("option.hoursGt20") },
  ], [t]);
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
  // 所选模型（不走 Form 字段）
  const [navModelLibId, setNavModelLibId] = useState<number | undefined>(undefined);
  const [navModelName, setNavModelName] = useState<string>("");
  // 保存当前使用的 LLM 配置，供追问使用
  const [activeModelId, setActiveModelId] = useState<number | null>(null);
  const [activeModelName, setActiveModelName] = useState<string | null>(null);
  const [activeAgentId, setActiveAgentId] = useState<number | null>(null);
  // 蓝海雷达内嵌面板：记录当前展开的推荐索引
  const [expandedRadarIndex, setExpandedRadarIndex] = useState<number | null>(null);
  // 历史记录抽屉
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyList, setHistoryList] = useState<NavigationGuideRecordItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyLoading, setHistoryLoading] = useState(false);
  // 查看历史详情
  const [historyDetail, setHistoryDetail] = useState<NavigationGuideRecordDetail | null>(null);
  const [historyDetailLoading, setHistoryDetailLoading] = useState(false);

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

  // ── 历史记录加载 ──
  const loadHistory = async (page = 1) => {
    setHistoryLoading(true);
    try {
      const limit = 10;
      const offset = (page - 1) * limit;
      const data = await listNavigationRecordsApi(limit, offset);
      setHistoryList(data.items);
      setHistoryTotal(data.total);
      setHistoryPage(page);
    } catch {
      message.error(t("message.loadHistoryFailed"));
    } finally {
      setHistoryLoading(false);
    }
  };

  const openHistory = () => {
    setHistoryDetail(null);
    setHistoryOpen(true);
    void loadHistory(1);
  };

  const viewRecordDetail = async (recordId: number) => {
    setHistoryDetailLoading(true);
    try {
      const data = await getNavigationRecordApi(recordId);
      setHistoryDetail(data);
    } catch {
      message.error(t("message.loadDetailFailed"));
    } finally {
      setHistoryDetailLoading(false);
    }
  };

  const deleteRecord = async (recordId: number) => {
    try {
      await deleteNavigationRecordApi(recordId);
      message.success(t("message.deleted"));
      void loadHistory(historyPage);
    } catch {
      message.error(t("message.deleteFailed"));
    }
  };

  const onSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      // llm 配置从独立 state 读取（不走 Form 字段）
      const llm_model_name = navModelName || undefined;
      // 保存当前 LLM 配置，供追问区使用
      setActiveModelId(navModelLibId ?? null);
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
        model_library_id: navModelLibId,
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
        message.info(t("message.noResults"));
      } else {
        message.success(t("message.foundCount", { count: data.recommendations.length }));
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
        message.error({ content: msg ?? t("message.quotaLow"), duration: 5 });
      } else {
        const detail = err?.response?.data?.detail;
        const msg = typeof detail === "object" ? JSON.stringify(detail) : detail;
        message.error(msg ?? t("message.navFailed"));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-yc-bg-base p-6 md:p-10 text-yc-text-primary">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* <QuotaDashboardCard quotaCheck={quotaCheck} /> */}

        {/* 页面标题 */}
        <div className="mb-2 flex items-start justify-between">
          <div>
            <Title level={3} style={{ color: "var(--color-text-primary)", marginBottom: 4 }}>{t("title")}</Title>
            <Text style={{ color: "var(--color-text-secondary)" }}>
              {t("desc")}
            </Text>
          </div>
          <Button
            icon={<HistoryOutlined />}
            onClick={openHistory}
            className="!rounded-lg shrink-0"
          >
            {t("historyButton")}
          </Button>
        </div>

        {/* 表单 — 分组布局 */}
        <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm" bodyStyle={{ padding: 24 }}>
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
              <Text strong className="text-sm text-yc-text-tertiary uppercase tracking-wider">{t("form.basicProfile")}</Text>
              <div className="h-px bg-yc-border-light mt-1 mb-4" />
            </div>

            <Form.Item name="languages" label={t("form.languages")} rules={[{ required: true, message: t("form.languagesRequired") }]}>
              <Select mode="multiple" options={LANGUAGE_OPTIONS} placeholder={t("form.languagesPlaceholder")} />
            </Form.Item>
            <Form.Item name="content_format" label={t("form.contentFormat")} rules={[{ required: true, message: t("form.contentFormatRequired") }]}>
              <Select mode="multiple" options={FORMAT_OPTIONS} placeholder={t("form.contentFormatPlaceholder")} />
            </Form.Item>
            <Form.Item name="budget_level" label={t("form.budgetLevel")} rules={[{ required: true }]}>
              <Select options={BUDGET_OPTIONS} />
            </Form.Item>

            {/* ── 个性化画像 ── */}
            <div className="mb-2 mt-6">
              <Text strong className="text-sm text-yc-text-tertiary uppercase tracking-wider">{t("form.personalProfile")}</Text>
              <div className="h-px bg-yc-border-light mt-1 mb-4" />
            </div>

            <Form.Item
              name="core_skills"
              label={t("form.coreSkills")}
              rules={[{ required: true, message: t("form.coreSkillsRequired") }]}
              extra={t("form.coreSkillsExtra")}
            >
              <Select mode="tags" maxCount={3} placeholder={t("form.coreSkillsPlaceholder")} />
            </Form.Item>
            <Form.Item name="monetization_goal" label={t("form.monetizationGoal")}>
              <Select options={MONETIZATION_OPTIONS} placeholder={t("form.monetizationPlaceholder")} allowClear />
            </Form.Item>
            <Form.Item name="target_regions" label={t("form.targetRegions")} extra={t("form.targetRegionsExtra")}>
              <Select mode="multiple" options={REGION_OPTIONS} placeholder={t("form.targetRegionsPlaceholder")} />
            </Form.Item>
            <Form.Item name="weekly_hours" label={t("form.weeklyHours")}>
              <Select options={WEEKLY_HOURS_OPTIONS} placeholder={t("form.weeklyHoursPlaceholder")} allowClear />
            </Form.Item>

            {/* ── 已有频道 ── */}
            <div className="mb-2 mt-6">
              <Text strong className="text-sm text-yc-text-tertiary uppercase tracking-wider">{t("form.existingChannel")}</Text>
              <div className="h-px bg-yc-border-light mt-1 mb-4" />
            </div>

            <Form.Item
              name="existing_channel_url"
              label={t("form.channelUrl")}
              extra={t("form.channelUrlExtra")}
            >
              <Input placeholder={t("form.channelUrlPlaceholder")} allowClear />
            </Form.Item>

            {/* ── AI 配置 ── */}
            <div className="mb-2 mt-6">
              <Text strong className="text-sm text-yc-text-tertiary uppercase tracking-wider">{t("form.aiConfig")}</Text>
              <div className="h-px bg-yc-border-light mt-1 mb-4" />
            </div>

            <Space wrap className="w-full" size="large">
              <Form.Item label={t("form.modelName")} className="mb-0 min-w-[220px]">
                <Select
                  showSearch
                  value={
                    navModelLibId !== undefined && navModelName
                      ? `${navModelLibId}::${navModelName}`
                      : undefined
                  }
                  onChange={(v: string) => {
                    const idx = v.indexOf("::");
                    setNavModelLibId(Number(v.slice(0, idx)));
                    setNavModelName(v.slice(idx + 2));
                  }}
                  options={allModelNameOpts}
                  placeholder={t("form.modelNamePlaceholder")}
                  allowClear
                  onClear={() => { setNavModelLibId(undefined); setNavModelName(""); }}
                  filterOption={(input, opt) =>
                    String(opt?.label ?? "").toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
              <Form.Item name="agent_id" label={t("form.agentName")} className="mb-0 min-w-[200px]">
                <Select options={agentOptions.map((p) => ({ value: p.id, label: p.title }))} placeholder={t("form.agentNamePlaceholder")} allowClear />
              </Form.Item>
            </Space>

            <Form.Item className="mb-0 mt-6">
              <Button type="primary" size="large" loading={loading} onClick={() => void onSubmit()} className="!rounded-lg !px-8">
                {t("form.submit")}
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {loading && (
          <div className="flex flex-col items-center justify-center py-16">
            <Spin size="large" />
            <Text type="secondary" className="mt-4">{t("message.loading")}</Text>
          </div>
        )}

        {/* 频道信息摘要 */}
        {!loading && channelInfo && (
          <Card className="!bg-yc-primary-bg/50 !border-yc-primary-border !shadow-sm" size="small" bodyStyle={{ padding: 16 }}>
            <div className="flex items-center gap-2 mb-1">
              <Text strong className="text-sm text-yc-primary">{t("channel.recognized")}</Text>
            </div>
            <div className="text-sm text-yc-text-primary">
              {String(channelInfo.title)} — {Number(channelInfo.subscriber_count).toLocaleString()} {t("channel.subscribers")} · {Number(channelInfo.video_count)} {t("channel.videos")}
            </div>
          </Card>
        )}

        {!loading && aiSummary && (
          <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm" bodyStyle={{ padding: 16 }}>
            <Text>{aiSummary}</Text>
          </Card>
        )}

        {/* 推荐结果默认 */}
        {!loading && recommendations.length > 0 && (
          <div className="space-y-5">
            <Title level={4} style={{ color: "var(--color-text-primary)" }}>{t("card.niche")}</Title>
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
          <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm" title={t("breakdown.title")} size="small">
            <QuotaBreakdown usage={quotaUsage} />
          </Card>
        )}
      </div>

      {/* ── 历史记录抽屉 ── */}
      <Drawer
        title={historyDetail ? t("history.detailTitle") : t("history.title")}
        open={historyOpen}
        onClose={() => {
          if (historyDetail) {
            setHistoryDetail(null);
          } else {
            setHistoryOpen(false);
          }
        }}
        width={historyDetail ? 720 : 480}
        styles={{ body: { padding: historyDetail ? 16 : 12 } }}
      >
        {historyDetail ? (
          /* ── 详情视图 ── */
          historyDetailLoading ? (
            <div className="flex justify-center py-12"><Spin size="large" /></div>
          ) : (
            <div className="space-y-5">
              {/* 请求参数摘要 */}
              <Card size="small" title={t("history.paramTitle")} className="!border-yc-border">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><Text type="secondary">{t("history.langLabel")}</Text>{(historyDetail.request_params.languages as string[])?.join("、") ?? "-"}</div>
                  <div><Text type="secondary">{t("history.budgetLabel")}</Text>{(historyDetail.request_params.budget_level as string) ?? "-"}</div>
                  <div><Text type="secondary">{t("history.skillLabel")}</Text>{(historyDetail.request_params.core_skills as string[])?.join("、") ?? "-"}</div>
                  <div><Text type="secondary">{t("history.formatLabel")}</Text>{(historyDetail.request_params.content_format as string[])?.join("、") ?? "-"}</div>
                </div>
                <div className="text-xs text-yc-text-muted mt-2">
                  {new Date(historyDetail.created_at).toLocaleString("zh-CN")}
                </div>
              </Card>

              {/* AI 摘要 */}
              {historyDetail.result.ai_summary && (
                <Card size="small" className="!border-yc-border !bg-yc-bg-inset">
                  <Text>{historyDetail.result.ai_summary}</Text>
                </Card>
              )}

              {/* 推荐品类 */}
              {historyDetail.result.recommendations.map((rec, i) => (
                <NicheCard
                  key={i}
                  rec={rec}
                  index={i}
                  isExpanded={false}
                  onToggleExpand={() => {}}
                />
              ))}

              {/* 避坑提示 */}
              {historyDetail.result.avoid_niche && (
                <AvoidNicheCard avoid={historyDetail.result.avoid_niche} />
              )}
            </div>
          )
        ) : (
          /* ── 列表视图 ── */
          <>
            {historyLoading ? (
              <div className="flex justify-center py-12"><Spin /></div>
            ) : historyList.length === 0 ? (
              <Empty description={t("history.empty")} />
            ) : (
              <div className="space-y-3">
                {historyList.map((item) => (
                  <div
                    key={item.id}
                    className="group rounded-lg border border-yc-border p-3 hover:border-yc-primary-border hover:bg-yc-primary-bg/30 transition-all cursor-pointer"
                    onClick={() => void viewRecordDetail(item.id)}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-yc-text-primary truncate">
                          {item.top_niche_title ?? t("history.resultDefault")}
                        </div>
                        <div className="text-xs text-yc-text-tertiary mt-0.5">
                          {(item.request_params.core_skills as string[])?.join("、")}
                          {item.top_match_score != null && (
                            <Tag color="blue" className="ml-2">{t("card.matchScore")} {item.top_match_score}</Tag>
                          )}
                          <Tag className="ml-1">{item.recommendation_count} {t("history.categoryCount")}</Tag>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0 ml-2">
                        <Button
                          type="text"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={(e) => {
                            e.stopPropagation();
                            void viewRecordDetail(item.id);
                          }}
                        />
                        <Popconfirm
                          title={t("history.confirmDelete")}
                          onConfirm={(e) => {
                            e?.stopPropagation();
                            void deleteRecord(item.id);
                          }}
                          onCancel={(e) => e?.stopPropagation()}
                        >
                          <Button
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </Popconfirm>
                      </div>
                    </div>
                    <div className="text-xs text-yc-text-muted">
                      {new Date(item.created_at).toLocaleString("zh-CN")}
                    </div>
                  </div>
                ))}
                {historyTotal > 10 && (
                  <div className="flex justify-center pt-2">
                    <Pagination
                      current={historyPage}
                      total={historyTotal}
                      pageSize={10}
                      size="small"
                      onChange={(page) => void loadHistory(page)}
                    />
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
}
