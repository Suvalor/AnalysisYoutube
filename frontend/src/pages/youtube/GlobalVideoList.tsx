import { CheckCircleOutlined, CloudDownloadOutlined, MergeOutlined, ThunderboltOutlined, UserAddOutlined } from "@ant-design/icons";
import { Button, Checkbox, DatePicker, Input, InputNumber, Modal, Pagination, Select, Spin, Tag, Tooltip, message } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { Eye, MessageCircle, ThumbsUp } from "lucide-react";
import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { listYouTubeChannelsApi, listYouTubeVideosAllApi, scrapeVideoCommentsApi, batchCheckVideoAnalysisApi, quickTrackChannelApi, type VideoListItem, type BatchAnalysisStatusItem } from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";
import { analyzeYouTubeVideoApi, getYouTubeVideoAnalysisApi, extractVideoHighlightsApi, getVideoHighlightsApi, type YouTubeVideoAnalysisResponse, type VideoHighlight } from "@/services/videosApi";
import { submitDownload, submitMix } from "@/services/downloadApi";
import MarkdownPreview from "@/components/MarkdownPreview";
import { formatNumber } from "@/utils/format";
import { buildYouTubeWatchUrl } from "@/utils/youtubeLinks";

dayjs.extend(relativeTime);

/** 全局视频：四列可叠加排序，后端优先级为 发布时间 → 播放量 → 点赞数 → 评论数 */
const VIDEO_SORT_METRICS = [
  {
    field: "publish_time" as const,
    stateKey: "sort_publish_time" as const,
    label: "发布时间",
    options: [
      { label: "新→旧", value: "desc" as const },
      { label: "旧→新", value: "asc" as const },
    ],
  },
  {
    field: "view_count" as const,
    stateKey: "sort_view_count" as const,
    label: "播放量",
    options: [
      { label: "高→低", value: "desc" as const },
      { label: "低→高", value: "asc" as const },
    ],
  },
  {
    field: "like_count" as const,
    stateKey: "sort_like_count" as const,
    label: "点赞数",
    options: [
      { label: "高→低", value: "desc" as const },
      { label: "低→高", value: "asc" as const },
    ],
  },
  {
    field: "comment_count" as const,
    stateKey: "sort_comment_count" as const,
    label: "评论数",
    options: [
      { label: "高→低", value: "desc" as const },
      { label: "低→高", value: "asc" as const },
    ],
  },
];

type ModelOption = { value: string; label: string };

function toModelOptions(rows: ModelItem[]): ModelOption[] {
  const out: ModelOption[] = [];
  for (const row of rows) {
    const raw = row.supported_models_json?.trim();
    if (!raw) continue;
    try {
      const arr = JSON.parse(raw) as Array<string | { value?: string; label?: string }>;
      if (!Array.isArray(arr)) continue;
      for (const item of arr) {
        if (typeof item === "string" && item.trim()) {
          out.push({ value: item.trim(), label: `${row.name} / ${item.trim()}` });
        } else if (item && typeof item === "object") {
          const v = String(item.value ?? "").trim();
          if (!v) continue;
          const label = String((item as { label?: string }).label ?? v).trim();
          out.push({ value: v, label: `${row.name} / ${label}` });
        }
      }
    } catch {
      continue;
    }
  }
  // 去重（按 value）
  const dedup = new Map<string, ModelOption>();
  for (const x of out) dedup.set(x.value, x);
  return Array.from(dedup.values());
}

export default function GlobalVideoList() {
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [pool, setPool] = useState<Array<{ id: number; title: string }>>([]);
  const [filters, setFilters] = useState({
    keyword: "",
    dateRange: null as [dayjs.Dayjs, dayjs.Dayjs] | null,
    min_duration: undefined as number | undefined,
    max_duration: undefined as number | undefined,
    channel_id: undefined as number | undefined,
    definition: undefined as string | undefined,
    privacy_status: undefined as string | undefined,
    /** 多列可同时生效；未设置的列不参与 ORDER BY */
    sort_publish_time: "desc" as "asc" | "desc" | undefined,
    sort_view_count: undefined as "asc" | "desc" | undefined,
    sort_like_count: undefined as "asc" | "desc" | undefined,
    sort_comment_count: undefined as "asc" | "desc" | undefined,
  });

  const [scrapeOpen, setScrapeOpen] = useState(false);
  const [scrapeKeyword, setScrapeKeyword] = useState("");
  const [scrapeVideoId, setScrapeVideoId] = useState<number | null>(null);
  const [scrapeLoading, setScrapeLoading] = useState(false);

  const [modelRows, setModelRows] = useState<ModelItem[]>([]);
  const [promptAgents, setPromptAgents] = useState<PromptItem[]>([]);
  const [panelOpenVideoId, setPanelOpenVideoId] = useState<number | null>(null);
  const [panelLoading, setPanelLoading] = useState<Record<number, boolean>>({});
  const [panelContentByVideoId, setPanelContentByVideoId] = useState<Record<number, string>>({});
  /** 分析成功后立即把列表标为「已分析」，与接口 has_analysis 合并 */
  const [analysisStatusOverride, setAnalysisStatusOverride] = useState<Record<number, BatchAnalysisStatusItem>>({});
  const [selectedModelByVideoId, setSelectedModelByVideoId] = useState<Record<number, string>>({});
  const [selectedAgentByVideoId, setSelectedAgentByVideoId] = useState<Record<number, number | undefined>>({});
  const [selectedVideoIds, setSelectedVideoIds] = useState<Set<string>>(new Set());
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [mixModalOpen, setMixModalOpen] = useState(false);
  const [highlightsByVideoId, setHighlightsByVideoId] = useState<Record<number, VideoHighlight[]>>({});
  const [extractingHighlights, setExtractingHighlights] = useState<Record<number, boolean>>({});
  const [trackingChannelIds, setTrackingChannelIds] = useState<Set<string>>(new Set());
  const [trackedChannelIds, setTrackedChannelIds] = useState<Set<string>>(new Set());

  const toggleVideoSelect = (ytVideoId: string) => {
    setSelectedVideoIds((prev) => {
      const next = new Set(prev);
      if (next.has(ytVideoId)) next.delete(ytVideoId);
      else next.add(ytVideoId);
      return next;
    });
  };

  const handleBatchDownload = async () => {
    if (selectedVideoIds.size === 0) {
      message.warning('请选择至少一个视频');
      return;
    }
    setDownloadLoading(true);
    try {
      const res = await submitDownload({ video_ids: Array.from(selectedVideoIds) });
      message.success(res.message || `已提交 ${res.task_count} 个下载任务`);
      if (res.skipped?.length) {
        message.info(`${res.skipped.length} 个视频已在下载队列中，已跳过`);
      }
      setSelectedVideoIds(new Set());
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : '批量下载提交失败');
    } finally {
      setDownloadLoading(false);
    }
  };

  const handleTrackChannel = async (channelId: string, e?: MouseEvent) => {
    if (e) e.stopPropagation();
    if (trackedChannelIds.has(channelId) || trackingChannelIds.has(channelId)) return;
    setTrackingChannelIds((prev) => new Set(prev).add(channelId));
    try {
      const res = await quickTrackChannelApi({ channel_id: channelId });
      if (res.success) {
        message.success(res.message);
        setTrackedChannelIds((prev) => new Set(prev).add(channelId));
      } else {
        message.warning(res.message);
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "追踪博主失败");
    } finally {
      setTrackingChannelIds((prev) => {
        const next = new Set(prev);
        next.delete(channelId);
        return next;
      });
    }
  };

  const handleExtractHighlights = async (videoId: number) => {
    setExtractingHighlights((prev) => ({ ...prev, [videoId]: true }));
    try {
      const res = await extractVideoHighlightsApi(videoId);
      setHighlightsByVideoId((prev) => ({ ...prev, [videoId]: res.highlights }));
      message.success(res.message || `已提取 ${res.highlights.length} 个精彩片段`);
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : '提取精彩片段失败');
    } finally {
      setExtractingHighlights((prev) => ({ ...prev, [videoId]: false }));
    }
  };

  const modelOptions = useMemo(() => toModelOptions(modelRows), [modelRows]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [models, prompts] = await Promise.all([listModelsApi(), listPromptsApi()]);
        if (!mounted) return;
        setModelRows(models);
        setPromptAgents(prompts);
      } catch (e) {
        if (!mounted) return;
        message.error(e instanceof Error ? e.message : "加载模型/智能体配置失败");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const loadVideos = async (p: number, ps: number, f: typeof filters) => {
    setLoading(true);
    try {
      const hasMultiSort =
        !!f.sort_publish_time ||
        !!f.sort_view_count ||
        !!f.sort_like_count ||
        !!f.sort_comment_count;
      const data = await listYouTubeVideosAllApi({
        keyword: f.keyword || undefined,
        start_date: f.dateRange?.[0]?.format("YYYY-MM-DD"),
        end_date: f.dateRange?.[1]?.format("YYYY-MM-DD"),
        min_duration: f.min_duration,
        max_duration: f.max_duration,
        channel_id: f.channel_id,
        definition: f.definition,
        privacy_status: f.privacy_status,
        ...(hasMultiSort
          ? {
            ...(f.sort_publish_time && { publish_time_sort: f.sort_publish_time }),
            ...(f.sort_view_count && { view_count_sort: f.sort_view_count }),
            ...(f.sort_like_count && { like_count_sort: f.sort_like_count }),
            ...(f.sort_comment_count && { comment_count_sort: f.sort_comment_count }),
          }
          : { sort_by: "publish_time_desc" }),
        page: p,
        page_size: ps,
      });
      setVideos(data.items);
      setAnalysisStatusOverride({});
      setSelectedVideoIds(new Set());
      setTotal(data.total);
      setPage(data.page);
      setPageSize(data.page_size);
      // Batch-check analysis status to ensure has_analysis is accurate
      const videoIds = data.items.map((v) => v.id);
      if (videoIds.length) {
        try {
          const statusMap = await batchCheckVideoAnalysisApi(videoIds);
          setAnalysisStatusOverride(statusMap);
        } catch {
          // Non-critical: fallback to has_analysis from list API
        }
      }
    } catch {
      message.error("加载视频列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void listYouTubeChannelsApi().then((rows) =>
      setPool(rows.map((x) => ({ id: x.channel.id, title: x.channel.title })))
    );
  }, []);

  useEffect(() => {
    void loadVideos(1, 20, filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openScrape = (videoId: number) => {
    setScrapeVideoId(videoId);
    setScrapeKeyword("");
    setScrapeOpen(true);
  };

  const confirmScrape = async () => {
    if (!scrapeVideoId || !scrapeKeyword.trim()) {
      message.warning("请输入关键字");
      return;
    }
    setScrapeLoading(true);
    try {
      const res = await scrapeVideoCommentsApi(scrapeVideoId, scrapeKeyword.trim());
      message.success(`已抓取并保存 ${res.scraped_count} 条评论，消耗额度 ${res.quota_used} 点`);
      setScrapeOpen(false);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail ?? "抓取失败");
    } finally {
      setScrapeLoading(false);
    }
  };

  const handleViewAnalysis = async (videoId: number) => {
    // Toggle: if panel is already open for this video, close it
    if (panelOpenVideoId === videoId) {
      setPanelOpenVideoId(null);
      return;
    }
    setPanelOpenVideoId(videoId);
    // Skip fetch if content is already cached
    if (panelContentByVideoId[videoId]) return;
    try {
      const res = await getYouTubeVideoAnalysisApi(videoId);
      setPanelContentByVideoId((prev) => ({ ...prev, [videoId]: res.content }));
      setAnalysisStatusOverride((prev) => ({ ...prev, [videoId]: { has_analysis: true, analyzed_at: res.updated_at } }));
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : "获取分析结果失败");
    }
  };

  const handleAnalyzeVideo = async (video: VideoListItem) => {
    const videoId = video.id;
    const defaultModelId = modelOptions[0]?.value ?? "";
    const modelId = selectedModelByVideoId[videoId] ?? defaultModelId;
    if (!modelId) {
      message.warning("请先在设置中心配置模型，并为模型选择一个可用的 Model ID");
      return;
    }

    const agentId = selectedAgentByVideoId[videoId] ?? undefined;
    setPanelOpenVideoId(videoId);
    setPanelLoading((prev) => ({ ...prev, [videoId]: true }));
    try {
      const res = await analyzeYouTubeVideoApi({
        video_id: videoId,
        model_id: modelId,
        agent_id: agentId ?? null,
      });
      setPanelContentByVideoId((prev) => ({ ...prev, [videoId]: res.content }));
      setAnalysisStatusOverride((prev) => ({ ...prev, [videoId]: { has_analysis: true, analyzed_at: res.updated_at } }));
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : "视频分析失败");
    } finally {
      setPanelLoading((prev) => ({ ...prev, [videoId]: false }));
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="bg-yc-bg-card border border-yc-border rounded-lg p-3 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-6 gap-2">
          <Input
            placeholder="标题关键词"
            value={filters.keyword}
            onChange={(e) => setFilters((s) => ({ ...s, keyword: e.target.value }))}
          />
          <DatePicker.RangePicker
            value={filters.dateRange as any}
            onChange={(v) => setFilters((s) => ({ ...s, dateRange: v as any }))}
          />
          <InputNumber className="w-full" placeholder="最小时长(秒)" value={filters.min_duration} onChange={(v) => setFilters((s) => ({ ...s, min_duration: Number(v) || undefined }))} />
          <InputNumber className="w-full" placeholder="最大时长(秒)" value={filters.max_duration} onChange={(v) => setFilters((s) => ({ ...s, max_duration: Number(v) || undefined }))} />
          <Select
            allowClear
            placeholder="频道"
            value={filters.channel_id}
            onChange={(v) => setFilters((s) => ({ ...s, channel_id: v }))}
            options={pool.map((x) => ({ label: x.title, value: x.id }))}
            className="min-w-0"
          />
          <Select
            allowClear
            placeholder="清晰度"
            value={filters.definition}
            onChange={(v) => setFilters((s) => ({ ...s, definition: v }))}
            options={[
              { label: "HD", value: "hd" },
              { label: "SD", value: "sd" },
            ]}
          />
          <Select
            allowClear
            placeholder="隐私"
            value={filters.privacy_status}
            onChange={(v) => setFilters((s) => ({ ...s, privacy_status: v }))}
            options={[
              { label: "公开", value: "public" },
              { label: "不公开", value: "unlisted" },
              { label: "私密", value: "private" },
            ]}
          />
          <div className="col-span-1 md:col-span-4 lg:col-span-6 space-y-2 pt-1 border-t border-yc-border-light mt-1">
            <p className="text-xs text-yc-text-tertiary">
              以下四列可同时参与排序；数据库优先级为：发布时间 → 播放量 → 点赞数 → 评论数（先按第一列排，相同再按下一列）。
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2">
              {VIDEO_SORT_METRICS.map(({ field, stateKey, label, options }) => (
                <div key={field} className="flex flex-col gap-1 min-w-0">
                  <span className="text-xs text-yc-text-tertiary">{label}</span>
                  <Select
                    allowClear
                    placeholder={`按${label}`}
                    className="w-full"
                    value={filters[stateKey]}
                    onChange={(v) => {
                      setFilters((s) => {
                        const next = {
                          ...s,
                          [stateKey]: (v ?? undefined) as (typeof s)[typeof stateKey],
                        };
                        void loadVideos(1, pageSize, next);
                        return next;
                      });
                    }}
                    options={options}
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-2 md:col-span-2">
            <Button type="primary" onClick={() => void loadVideos(1, pageSize, filters)}>
              筛选
            </Button>
            <Button
              onClick={() => {
                const reset = {
                  keyword: "",
                  dateRange: null as [dayjs.Dayjs, dayjs.Dayjs] | null,
                  min_duration: undefined,
                  max_duration: undefined,
                  channel_id: undefined,
                  definition: undefined,
                  privacy_status: undefined,
                  sort_publish_time: "desc",
                  sort_view_count: undefined,
                  sort_like_count: undefined,
                  sort_comment_count: undefined,
                };
                setFilters(reset);
                void loadVideos(1, pageSize, reset);
              }}
            >
              重置
            </Button>
          </div>
        </div>
      </div>

      {selectedVideoIds.size > 0 && (
        <div className="flex items-center gap-3 bg-yc-info-bg border border-yc-info rounded-lg px-4 py-2">
          <CloudDownloadOutlined className="text-yc-info text-lg" />
          <span className="text-sm text-yc-info">已选 {selectedVideoIds.size} 个视频</span>
          <Button
            type="primary"
            size="small"
            loading={downloadLoading}
            onClick={() => void handleBatchDownload()}
          >
            批量下载素材
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<MergeOutlined />}
            onClick={() => setMixModalOpen(true)}
          >
            AI 混剪
          </Button>
          <Button
            size="small"
            onClick={() => setSelectedVideoIds(new Set())}
          >
            清除选择
          </Button>
        </div>
      )}

      <div className="space-y-2">
        {loading ? (
          <div className="text-yc-text-tertiary">加载中...</div>
        ) : (
          videos.map((video) => {
            const hasAnalyzed = video.has_analysis || !!analysisStatusOverride[video.id]?.has_analysis;
            const analyzedAt = analysisStatusOverride[video.id]?.analyzed_at ?? null;
            const watchUrl = buildYouTubeWatchUrl(video.yt_video_id);
            const openYouTube = (e: MouseEvent) => {
              e.stopPropagation();
              if (!watchUrl) {
                message.warning("该视频缺少有效的 YouTube 视频 ID，无法跳转");
                return;
              }
              window.open(watchUrl, "_blank", "noopener,noreferrer");
            };
            return (
              <div
                key={video.id}
                className={`bg-yc-bg-card border rounded-lg p-3 shadow-sm relative ${selectedVideoIds.has(video.yt_video_id) ? 'border-yc-border-selected ring-2 ring-yc-border-selected' : 'border-yc-border'}`}
              >
                <div className="absolute top-2 left-2 z-10">
                  <Checkbox
                    checked={selectedVideoIds.has(video.yt_video_id)}
                    onChange={() => toggleVideoSelect(video.yt_video_id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
                <div className="flex flex-col md:flex-row gap-4">
                  {/* 缩略图 */}
                  <div className="relative w-full md:w-64 shrink-0">
                    {watchUrl ? (
                      <button
                        type="button"
                        onClick={openYouTube}
                        className="block w-full p-0 border-0 bg-transparent cursor-pointer rounded overflow-hidden group/thumb"
                        aria-label="在 YouTube 打开视频"
                      >
                        <img
                          src={video.thumbnail_url || ""}
                          alt=""
                          className="w-full h-36 object-cover rounded transition-opacity group-hover/thumb:opacity-90"
                        />
                      </button>
                    ) : (
                      <img src={video.thumbnail_url || ""} alt="" className="w-full h-36 object-cover rounded opacity-90" />
                    )}
                    <div className="absolute right-2 bottom-2 text-xs px-2 py-0.5 rounded bg-yc-overlay text-yc-text-inverse pointer-events-none">
                      {video.duration_str}
                    </div>
                  </div>
                  {/* 信息区 */}
                  <div className="flex-1 min-w-0">
                    {watchUrl ? (
                      <button
                        type="button"
                        onClick={openYouTube}
                        className="font-semibold text-yc-text-primary truncate text-left w-full p-0 border-0 bg-transparent cursor-pointer hover:text-yc-primary-hover transition-colors"
                      >
                        {video.title}
                      </button>
                    ) : (
                      <div className="font-semibold text-yc-text-primary truncate">{video.title}</div>
                    )}
                    
                    <div className="mt-2 flex flex-wrap gap-2">
                      {video.channel_title && <div className="text-xs text-yc-text-tertiary mt-0.5 truncate">频道：{video.channel_title}</div>}
                      <Tag className="!border-yc-border !bg-yc-bg-card !text-yc-text-secondary">{video.definition.toUpperCase()}</Tag>
                      <Tag className="!border-yc-border !bg-yc-bg-card !text-yc-text-secondary">{video.privacy_status}</Tag>
                      {hasAnalyzed && (
                        <Tag
                          color="success"
                          icon={<CheckCircleOutlined />}
                          className="cursor-pointer"
                          onClick={(e) => { e.stopPropagation(); void handleViewAnalysis(video.id); }}
                        >
                          已分析{analyzedAt ? ` ${dayjs(analyzedAt).fromNow()}` : ''}
                        </Tag>
                      )}
                    </div>
                    <div className="text-yc-text-tertiary text-sm mt-2">
                      发布于 {video.published_at ? dayjs(video.published_at).format("YYYY-MM-DD HH:mm") : "-"} ·{" "}
                      {video.published_at ? dayjs(video.published_at).fromNow() : ""}
                    </div>
                    {highlightsByVideoId[video.id] && highlightsByVideoId[video.id].length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {highlightsByVideoId[video.id].map((hl) => (
                          <Tag key={hl.id} color="gold" className="text-xs">
                            {hl.start_sec.toFixed(0)}s-{hl.end_sec.toFixed(0)}s {hl.label}
                          </Tag>
                        ))}
                      </div>
                    )}
                    {/* 统计数据 */}
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm">
                      <span className="text-yc-info flex items-center gap-1"><Eye className="h-4 w-4 shrink-0" aria-hidden />播放量：{formatNumber(video.view_count)}</span>
                      <span className="text-yc-success flex items-center gap-1"><ThumbsUp className="h-4 w-4 shrink-0" aria-hidden />点赞：{formatNumber(video.like_count)}</span>
                      <span className="text-yc-warning flex items-center gap-1"><MessageCircle className="h-4 w-4 shrink-0" aria-hidden />评论：{formatNumber(video.comment_count)}</span>
                    </div>
                    {/* 操作按钮栏 */}
                    <div className="mt-3 flex flex-wrap gap-2 items-center">
                      <Button
                        size="small"
                        icon={<UserAddOutlined />}
                        loading={trackingChannelIds.has(video.yt_channel_id ?? "")}
                        disabled={!video.yt_channel_id || trackedChannelIds.has(video.yt_channel_id ?? "") || trackingChannelIds.has(video.yt_channel_id ?? "")}
                        onClick={(e) => video.yt_channel_id && void handleTrackChannel(video.yt_channel_id, e)}
                      >
                        {trackedChannelIds.has(video.yt_channel_id ?? "") ? "已追踪" : "追踪博主"}
                      </Button>
                      <Button type="primary" size="small" onClick={() => openScrape(video.id)}>
                        抓取评论
                      </Button>
                      <Button
                        size="small"
                        icon={<ThunderboltOutlined />}
                        loading={Boolean(extractingHighlights[video.id])}
                        onClick={() => void handleExtractHighlights(video.id)}
                      >
                        提取精彩片段
                      </Button>
                      <Select
                        showSearch
                        placeholder="选择模型"
                        style={{ minWidth: 160 }}
                        value={selectedModelByVideoId[video.id] ?? (modelOptions[0]?.value ?? undefined)}
                        options={modelOptions}
                        onChange={(v) => setSelectedModelByVideoId((prev) => ({ ...prev, [video.id]: String(v) }))}
                      />
                      <Select
                        allowClear
                        placeholder="选择智能体（可选）"
                        style={{ minWidth: 160 }}
                        value={selectedAgentByVideoId[video.id] ?? undefined}
                        options={promptAgents.map((p) => ({ value: p.id, label: p.title }))}
                        onChange={(v) => setSelectedAgentByVideoId((prev) => ({ ...prev, [video.id]: v === undefined ? undefined : Number(v) }))}
                      />
                      <Button
                        type={hasAnalyzed ? "dashed" : "primary"}
                        size="small"
                        onClick={() => void handleAnalyzeVideo(video)}
                        loading={Boolean(panelLoading[video.id])}
                      >
                        {hasAnalyzed ? "重新分析" : "一键 AI 视频分析"}
                      </Button>
                      {hasAnalyzed && (
                        <Button
                          type="primary"
                          size="small"
                          icon={<CheckCircleOutlined />}
                          onClick={() => void handleViewAnalysis(video.id)}
                          disabled={Boolean(panelLoading[video.id])}
                          className={panelOpenVideoId !== video.id ? "!bg-yc-success !border-yc-success" : undefined}
                        >
                          查看结果{analyzedAt ? `(${dayjs(analyzedAt).fromNow()})` : ''}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                {panelOpenVideoId === video.id ? (
                  <div className="mt-3 rounded-lg border border-yc-border bg-yc-bg-inset p-3">
                    {panelLoading[video.id] ? (
                      <div className="flex items-center gap-2 text-yc-text-secondary">
                        <Spin size="small" /> 分析中…
                      </div>
                    ) : panelContentByVideoId[video.id] ? (
                      <MarkdownPreview>{panelContentByVideoId[video.id]}</MarkdownPreview>
                    ) : (
                      <div className="text-yc-text-tertiary text-sm">
                        {hasAnalyzed
                          ? "暂无缓存展示。请点击「查看结果」拉取已保存的分析内容。"
                          : "暂无分析结果。点击「一键 AI 视频分析」生成内容。"}
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>

      <div className="flex justify-end bg-yc-bg-card border border-yc-border rounded-lg p-3">
        <Pagination
          current={page}
          pageSize={pageSize}
          total={total}
          showSizeChanger
          onChange={(p, ps) => void loadVideos(p, ps, filters)}
        />
      </div>

      <Modal
        title="定向抓取评论"
        open={scrapeOpen}
        onOk={() => void confirmScrape()}
        onCancel={() => setScrapeOpen(false)}
        confirmLoading={scrapeLoading}
        okText="开始抓取"
      >
        <p className="text-sm text-yc-text-secondary mb-2">将使用 YouTube commentThreads 接口按关键字搜索评论（最多 100 条）。</p>
        <Input placeholder="搜索关键字" value={scrapeKeyword} onChange={(e) => setScrapeKeyword(e.target.value)} />
      </Modal>

      <Modal
        title="AI 混剪"
        open={mixModalOpen}
        onCancel={() => setMixModalOpen(false)}
        onOk={async () => {
          try {
            const res = await submitMix({
              video_ids: Array.from(selectedVideoIds),
              aspect_ratio: '9:16',
              use_highlights: true,
            });
            message.success(res.message || '混剪任务已提交');
            setMixModalOpen(false);
            setSelectedVideoIds(new Set());
          } catch (err: unknown) {
            const d = err && typeof err === 'object' && 'response' in err
              ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
              : undefined;
            message.error(typeof d === 'string' ? d : '混剪提交失败');
          }
        }}
        okText="提交混剪"
      >
        <div className="space-y-3">
          <p className="text-sm text-yc-text-secondary">
            将对选中的 {selectedVideoIds.size} 个视频执行 AI 混剪，优先使用已提取的精彩片段。
          </p>
          <p className="text-xs text-yc-text-tertiary">
            混剪为后台任务，提交后可在任务中心查看进度与结果。
          </p>
        </div>
      </Modal>
    </div>
  );
}
