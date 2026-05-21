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
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  analyzeYouTubeBatchApi,
  blueOceanRadarScanApi,
  radarAiRetrospectiveApi,
  categoryOpportunityApi,
  crossRegionCompareApi,
  exportReportApi,
  type BlueOceanChannelItem,
  type RadarAiRetrospectiveResponse,
  type CategoryOpportunityResponse,
  type CrossRegionCompareResponse,
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
  const { t } = useTranslation("radar");
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

  // 品类机会报告
  const [catOppLoading, setCatOppLoading] = useState(false);
  const [catOppResult, setCatOppResult] = useState<CategoryOpportunityResponse | null>(null);
  const [catOppKeyword, setCatOppKeyword] = useState("");
  const [catOppRegion, setCatOppRegion] = useState("US");

  // 跨地区对比
  const [crossRegionLoading, setCrossRegionLoading] = useState(false);
  const [crossRegionResult, setCrossRegionResult] = useState<CrossRegionCompareResponse | null>(null);
  const [crossRegionKeyword, setCrossRegionKeyword] = useState("");
  const [crossRegionCodes, setCrossRegionCodes] = useState<string[]>(["US", "SG", "AE"]);

  const columns: ColumnsType<BlueOceanChannelItem> = useMemo(
    () => [
      {
        title: t("table.channel"),
        key: "channel",
        width: 280,
        render: (_, row) => (
          <Space>
            <Avatar src={row.thumbnail_url ?? undefined} size={40}>
              {row.title?.slice(0, 1) ?? "?"}
            </Avatar>
            <div className="min-w-0">
              <div className="font-medium text-yc-text-primary truncate max-w-[200px]">{row.title}</div>
              <Text type="secondary" className="text-xs">
                {row.yt_channel_id}
              </Text>
            </div>
          </Space>
        ),
      },
      {
        title: t("table.subscribers"),
        dataIndex: "subscriber_count",
        sorter: (a, b) => a.subscriber_count - b.subscriber_count,
        render: (v: number) => formatNumber(v),
      },
      {
        title: t("table.totalViews"),
        dataIndex: "total_views",
        sorter: (a, b) => a.total_views - b.total_views,
        render: (v: number) => formatNumber(v),
      },
      {
        title: t("table.viralViews"),
        key: "viral",
        render: (_, row) => (
          <Link href={row.viral_video_url} target="_blank" rel="noopener noreferrer">
            {t("action.openYoutube")}
          </Link>
        ),
      },
      {
        title: t("table.viewCount"),
        dataIndex: "viral_view_count",
        sorter: (a, b) => a.viral_view_count - b.viral_view_count,
        render: (v: number) => formatNumber(v),
      },
      {
        title: t("table.outlierScore"),
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
        title: t("table.action"),
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
              {done ? t("action.imported") : t("action.importFollow")}
            </Button>
          );
        },
      },
    ],
    [t, importedIds, addingId]
  );

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

  const handleImport = async (row: BlueOceanChannelItem) => {
    setAddingId(row.yt_channel_id);
    try {
      await analyzeYouTubeBatchApi({ urls: row.channel_url, group_name: t("title") });
      setImportedIds((prev) => new Set([...prev, row.yt_channel_id]));
      message.success(t("message.importSuccess"));
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? t("message.importFailed"));
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
        message.warning(t("message.aiConfigLoadFailed"));
      }
    };
    void loadAiConfigs();


    // 自动加载最新推荐参数回填到扫描表单
    const loadLatestParams = async () => {
      try {
        const { getLatestParamIterationApi } = await import("@/services/authApi");
        const res = await getLatestParamIterationApi();
        if (res.recommended_params) {
          const p = res.recommended_params;
          if (p.max_subscribers != null) form.setFieldValue("max_subscribers", Number(p.max_subscribers));
          if (p.outlier_multiplier != null) form.setFieldValue("outlier_multiplier", Number(p.outlier_multiplier));
        }
      } catch {
        // 静默失败，使用默认参数
      }
    };
    void loadLatestParams();
  }, []);

  const openAiDrawer = async () => {
    if (!selectedModelLibId || !selectedLlmModelName || !selectedAgentId) {
      message.warning(t("message.needAiConfig"));
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
      setAiError(err?.response?.data?.detail ?? t("message.retrospectiveFailed"));
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

  // 品类机会报告
  const onCategoryOpportunity = async () => {
    const kw = catOppKeyword.trim();
    if (!kw) { message.warning(t("message.needKeyword")); return; }
    setCatOppLoading(true);
    try {
      const data = await categoryOpportunityApi({ keyword: kw, region: catOppRegion });
      setCatOppResult(data);
      message.success(t("message.categorySuccess"));
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? t("message.categoryFailed"));
    } finally {
      setCatOppLoading(false);
    }
  };

  // 跨地区对比
  const onCrossRegionCompare = async () => {
    const kw = crossRegionKeyword.trim();
    if (!kw) { message.warning(t("message.needKeywordShort")); return; }
    if (crossRegionCodes.length < 2) { message.warning(t("message.needTwoRegions")); return; }
    setCrossRegionLoading(true);
    try {
      const data = await crossRegionCompareApi({ keyword: kw, regions: crossRegionCodes });
      setCrossRegionResult(data);
      message.success(t("message.crossSuccess"));
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? t("message.crossFailed"));
    } finally {
      setCrossRegionLoading(false);
    }
  };

  // 一键出报告
  const onExportReport = async () => {
    if (items.length === 0) { message.warning(t("message.needScanFirst")); return; }
    try {
      const data = await exportReportApi({ scan_items: items, keyword: form.getFieldValue("keyword") });
      const win = window.open("", "_blank");
      if (win) {
        // 简易 Markdown → HTML 转换（标题、表格、粗体、列表、分隔线）
        const md = data.markdown_content;
        const rawHtml = md
          .replace(/^### (.+)$/gm, "<h3>$1</h3>")
          .replace(/^## (.+)$/gm, "<h2>$1</h2>")
          .replace(/^# (.+)$/gm, "<h1>$1</h1>")
          .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
          .replace(/^---$/gm, "<hr>")
          .replace(/^- (.+)$/gm, "<li>$1</li>")
          .replace(/^\|(.+)\|$/gm, (match) => {
            const cells = match.split("|").filter((c) => c.trim() !== "");
            const isHeader = cells.every((c) => /^[\s-]+$/.test(c));
            if (isHeader) return "";
            const tag = "td";
            return "<tr>" + cells.map((c) => `<${tag}>${c.trim()}</${tag}>`).join("") + "</tr>";
          })
          .replace(/\n/g, "<br>");
        // 用 DOMPurify 净化 HTML，防止 XSS
        const DOMPurify = (await import("dompurify")).default;
        const safeHtml = DOMPurify.sanitize(rawHtml);
        win.document.write(`<html><head><title>${t("title")}</title><style>body{font-family:system-ui;max-width:900px;margin:0 auto;padding:24px;color:#1e293b}table{border-collapse:collapse;width:100%}th,td{border:1px solid #e2e8f0;padding:8px;text-align:left}th{background:#f1f5f9}h1{color:#0f172a}h2{color:#1e293b;border-bottom:1px solid #e2e8f0;padding-bottom:8px}hr{border:none;border-top:1px solid #e2e8f0;margin:16px 0}li{margin:4px 0}</style></head><body>`);
        win.document.write(safeHtml);
        win.document.write("</body></html>");
        win.document.close();
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? t("message.exportFailed"));
    }
  };

  const applyAiParams = () => {
    if (!aiResult) return;
    form.setFieldsValue({
      max_subscribers: aiResult.recommended_parameters.max_subscribers,
      outlier_multiplier: aiResult.recommended_parameters.outlier_multiplier,
    });
    setAiOpen(false);
    message.success(t("message.applySuccess"));
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
        message.info(t("message.noResults"));
      } else {
        message.success(t("message.scanSuccess", { count: data.items.length }));
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; errorFields?: unknown };
      if (err?.errorFields) return;
      message.error(err?.response?.data?.detail ?? t("message.scanFailed"));
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="min-h-screen bg-yc-bg-base p-6 md:p-10 text-yc-text-primary">
      <div className="max-w-7xl mx-auto space-y-6">
        <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm">
          <Title level={3} style={{ color: "var(--color-text-primary)", marginBottom: 8 }}>
            {t("title")}
          </Title>
          <Text style={{ color: "var(--color-text-secondary)" }}>
            {t("desc")}
          </Text>
        </Card>

        <Tabs
          defaultActiveKey="scan"
          items={[
            {
              key: "scan",
              label: t("tab.scan"),
              children: (
                <>
                  <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm" title={t("card.scanConsole")}>
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
                        label={t("form.keyword")}
                        rules={[{ required: true, message: t("form.keywordRequired") }]}
                      >
                        <Input placeholder={t("form.keywordPlaceholder")} allowClear />
                      </Form.Item>
                      <Form.Item name="published_after" label={t("form.publishedAfter")}>
                        <Select
                          options={[
                            { value: 30, label: t("option.lastMonth") },
                            { value: 90, label: t("option.last3Months") },
                            { value: 180, label: t("option.lastHalfYear") },
                          ]}
                        />
                      </Form.Item>
                      <Space wrap className="w-full" size="large">
                        <Form.Item name="max_subscribers" label={t("form.maxSubscribers")} className="mb-0 min-w-[200px]">
                          <InputNumber min={0} className="w-full" />
                        </Form.Item>
                        <Form.Item name="outlier_multiplier" label={t("form.outlierMultiplier")} className="mb-0 min-w-[200px]">
                          <InputNumber min={0.1} step={0.5} className="w-full" />
                        </Form.Item>
                      </Space>
                      <Form.Item name="video_duration" label={t("form.videoDuration")} className="mt-4">
                        <Select
                          allowClear
                          placeholder={t("form.videoDurationPlaceholder")}
                          options={[
                            { value: "short", label: t("option.shortVideo") },
                            { value: "medium", label: t("option.medium") },
                            { value: "long", label: t("option.longVideo") },
                          ]}
                        />
                      </Form.Item>
                      <Space className="mt-4" wrap>
                        <Form.Item label={t("form.modelName")} className="mb-0 min-w-[260px]">
                          <Select
                            showSearch
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
                            placeholder={t("form.selectModel")}
                            filterOption={(input, opt) =>
                              String(opt?.label ?? "").toLowerCase().includes(input.toLowerCase())
                            }
                            allowClear
                            onClear={() => { setSelectedModelLibId(undefined); setSelectedLlmModelName(""); }}
                          />
                        </Form.Item>
                        <Form.Item label={t("form.aiAgent")} className="mb-0 min-w-[220px]">
                          <Select
                            value={selectedAgentId}
                            onChange={setSelectedAgentId}
                            options={agentOptions.map((p) => ({ value: p.id, label: p.title }))}
                            placeholder={t("form.selectAgent")}
                          />
                        </Form.Item>
                      </Space>
                      <Form.Item className="mb-0 mt-4">
                        <Space wrap>
                          <Button type="primary" size="large" loading={scanning} onClick={() => void onScan()}>
                            {t("form.submit")}
                          </Button>
                          <Button
                            size="large"
                            className="!text-yc-accent !border-yc-accent-bg hover:!border-yc-accent hover:!text-yc-accent"
                            onClick={() => void openAiDrawer()}
                          >
                            {t("message.aiRetrospective")}
                          </Button>
                        </Space>
                      </Form.Item>
                    </Form>
                  </Card>

                  {warnings.length > 0 && (
                    <Alert type="warning" showIcon message={t("message.partialData")} description={
                      <ul className="list-disc pl-4 mb-0">
                        {warnings.map((w, i) => (
                          <li key={`${i}-${w.slice(0, 40)}`}>{w}</li>
                        ))}
                      </ul>
                    } />
                  )}

                  <Card
                    className="!bg-yc-bg-card !border-yc-border !shadow-sm"
                    title={t("card.scanResults")}
                    extra={
                      items.length > 0 ? (
                        <Button size="small" onClick={() => void onExportReport()}>
                          {t("action.exportReport")}
                        </Button>
                      ) : undefined
                    }
                  >
                    <Table<BlueOceanChannelItem>
                      rowKey={(r) => r.yt_channel_id}
                      columns={columns}
                      dataSource={items}
                      pagination={{ pageSize: 10, showSizeChanger: true }}
                      locale={{ emptyText: scanning ? t("empty.scanning") : t("empty.noDataScanFirst") }}
                    />
                  </Card>
                </>
              ),
            },
            {
              key: "category-opportunity",
              label: t("tab.categoryOpp"),
              children: (
                <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm" title={t("card.categoryReport")}>
                  <Space wrap className="mb-4">
                    <Input
                      value={catOppKeyword}
                      onChange={(e) => setCatOppKeyword(e.target.value)}
                      placeholder={t("form.categoryKeywordPlaceholder")}
                      style={{ width: 240 }}
                    />
                    <Select
                      value={catOppRegion}
                      onChange={setCatOppRegion}
                      options={[
                        { value: "US", label: t("region.US") },
                        { value: "SG", label: t("region.SG") },
                        { value: "AE", label: t("region.AE") },
                        { value: "GB", label: t("region.GB") },
                        { value: "JP", label: t("region.JP") },
                        { value: "IN", label: t("region.IN") },
                        { value: "BR", label: t("region.BR") },
                      ]}
                      style={{ width: 120 }}
                    />
                    <Button type="primary" loading={catOppLoading} onClick={() => void onCategoryOpportunity()}>
                      {t("action.analyzeOpportunity")}
                    </Button>
                  </Space>
                  {catOppResult && (
                    <div className="space-y-4">
                      <Card size="small" title={t("card.topGrowth")} className="!border-yc-border">
                        <Table
                          dataSource={catOppResult.top_channels_growth}
                          rowKey="channel_id"
                          size="small"
                          pagination={false}
                          columns={[
                            { title: t("table.channel"), dataIndex: "title", key: "title" },
                            { title: t("table.subscribers"), dataIndex: "subscriber_count", key: "sub", render: (v: number) => v.toLocaleString() },
                            { title: t("table.monthlyGrowth"), dataIndex: "monthly_growth_rate", key: "rate", render: (v: number) => v.toFixed(1) },
                            { title: t("table.trend"), dataIndex: "trend", key: "trend", render: (v: string) => <Tag color={v === "rising" ? "green" : v === "stable" ? "blue" : "red"}>{v}</Tag> },
                          ]}
                        />
                      </Card>
                      <Card size="small" title={t("card.contentGaps")} className="!border-yc-border">
                        <Table
                          dataSource={catOppResult.content_gaps}
                          rowKey="duration_bucket"
                          size="small"
                          pagination={false}
                          columns={[
                            { title: t("table.duration"), dataIndex: "duration_bucket", key: "dur" },
                            { title: t("table.supplyRatio"), dataIndex: "supply_ratio", key: "ratio", render: (v: number) => `${(v * 100).toFixed(1)}%` },
                            { title: t("table.avgViews"), dataIndex: "avg_views", key: "views", render: (v: number) => v.toLocaleString() },
                            { title: t("table.opportunityScore"), dataIndex: "opportunity_score", key: "score", render: (v: number) => v.toFixed(1) },
                          ]}
                        />
                      </Card>
                      <Card size="small" title={t("card.newcomerStats")} className="!border-yc-border">
                        <Space size="large">
                          <Text>{t("card.newChannels")}：{catOppResult.newcomer_stats.total_new_channels}</Text>
                          <Text>{t("card.successfulChannels")}：{catOppResult.newcomer_stats.successful_channels}</Text>
                          <Text>{t("card.successRate")}：<Text strong>{(catOppResult.newcomer_stats.success_rate * 100).toFixed(1)}%</Text></Text>
                        </Space>
                      </Card>
                      {catOppResult.ai_summary && (
                        <Card size="small" title={t("card.aiSummary")} className="!border-yc-border">
                          <Text>{catOppResult.ai_summary}</Text>
                        </Card>
                      )}
                    </div>
                  )}
                </Card>
              ),
            },
            {
              key: "cross-region",
              label: t("tab.crossRegion"),
              children: (
                <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm" title={t("card.crossCompare")}>
                  <Space wrap className="mb-4">
                    <Input
                      value={crossRegionKeyword}
                      onChange={(e) => setCrossRegionKeyword(e.target.value)}
                      placeholder={t("form.keywordPlaceholder")}
                      style={{ width: 240 }}
                    />
                    <Select
                      mode="multiple"
                      value={crossRegionCodes}
                      onChange={setCrossRegionCodes}
                      options={[
                        { value: "US", label: t("region.US") },
                        { value: "GB", label: t("region.GB") },
                        { value: "SG", label: t("region.SG") },
                        { value: "AE", label: t("region.AE") },
                        { value: "JP", label: t("region.JP") },
                        { value: "IN", label: t("region.IN") },
                        { value: "BR", label: t("region.BR") },
                        { value: "PH", label: t("region.PH") },
                        { value: "ID", label: t("region.ID") },
                        { value: "TH", label: t("region.TH") },
                        { value: "KR", label: t("region.KR") },
                        { value: "TW", label: t("region.TW") },
                      ]}
                      placeholder={t("form.selectRegions")}
                      style={{ minWidth: 240 }}
                    />
                    <Button type="primary" loading={crossRegionLoading} onClick={() => void onCrossRegionCompare()}>
                      {t("action.crossCompare")}
                    </Button>
                  </Space>
                  {crossRegionResult && (
                    <Table
                      dataSource={crossRegionResult.regions}
                      rowKey="region_code"
                      size="small"
                      pagination={false}
                      columns={[
                        { title: t("table.region"), dataIndex: "region_name", key: "name" },
                        { title: t("table.channelCount"), dataIndex: "channel_count", key: "count" },
                        { title: t("table.avgViews"), dataIndex: "avg_views", key: "views", render: (v: number) => v.toLocaleString() },
                        { title: t("table.medianOutlierScore"), dataIndex: "median_outlier_score", key: "score", render: (v: number) => v.toFixed(1) },
                        { title: t("table.topChannel"), dataIndex: "top_channel_title", key: "top" },
                        { title: t("table.topSubscribers"), dataIndex: "top_channel_subscribers", key: "top_sub", render: (v: number) => v.toLocaleString() },
                      ]}
                    />
                  )}
                  {crossRegionResult?.ai_recommendation && (
                    <Card size="small" title={t("card.aiRecommendation")} className="!border-yc-border mt-4">
                      <Text>{crossRegionResult.ai_recommendation}</Text>
                    </Card>
                  )}
                </Card>
              ),
            },
          ]}
        />
      </div>
      <Drawer
        title={t("message.aiRetrospectiveTitle")}
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
          <Alert type="error" showIcon message={t("message.retrospectiveFailed")} description={aiError} />
        ) : aiResult ? (
          <div className="space-y-4">
            <Card size="small" title={t("card.retrospectiveSummary")} className="!border-yc-border">
              <Text>{aiResult.analysis_summary}</Text>
            </Card>
            <Card size="small" title={t("card.suggestedKeywords")} className="!border-yc-border">
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
                  <Text type="secondary">{t("empty.noKeywordSuggestions")}</Text>
                )}
              </Space>
            </Card>
            <Card size="small" title={t("card.recommendedParams")} className="!border-yc-border">
              <div className="space-y-2">
                <div>
                  <Text type="secondary">{t("label.maxSubscribers")}：</Text>
                  <Text strong>{formatNumber(aiResult.recommended_parameters.max_subscribers)}</Text>
                </div>
                <div>
                  <Text type="secondary">{t("label.outlierMultiplier")}：</Text>
                  <Text strong>{aiResult.recommended_parameters.outlier_multiplier}</Text>
                </div>
                <div>
                  <Text type="secondary">{t("label.suggestedAction")}：</Text>
                  <Text>{aiResult.next_step_action}</Text>
                </div>
                <div>
                  <Text type="secondary">
                    {t("label.sampleCoverage", { lookbackDays: aiResult.sample_meta.lookback_days, topCount: aiResult.sample_meta.top_count, lowCount: aiResult.sample_meta.low_count })}
                  </Text>
                </div>
              </div>
            </Card>
            <Button type="primary" size="large" block onClick={applyAiParams}>
              {t("message.applyParams")}
            </Button>
          </div>
        ) : (
          <Text type="secondary">{t("message.noRetrospectiveData")}</Text>
        )}
      </Drawer>
    </div>
  );
}
