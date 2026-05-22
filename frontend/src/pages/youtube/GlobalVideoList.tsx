import { CheckCircleOutlined, CloudDownloadOutlined, MergeOutlined, ThunderboltOutlined, UserAddOutlined } from "@ant-design/icons";
import { Button, Checkbox, DatePicker, Input, InputNumber, Modal, Pagination, Select, Spin, Tag, Tooltip, message } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { Eye, MessageCircle, ThumbsUp } from "lucide-react";
import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useTranslation } from "react-i18next";
import { listYouTubeChannelsApi, listYouTubeVideosAllApi, scrapeVideoCommentsApi, batchCheckVideoAnalysisApi, quickTrackChannelApi, type VideoListItem, type BatchAnalysisStatusItem } from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";
import { analyzeYouTubeVideoApi, getYouTubeVideoAnalysisApi, extractVideoHighlightsApi, getVideoHighlightsApi, type YouTubeVideoAnalysisResponse, type VideoHighlight } from "@/services/videosApi";
import { submitDownload, submitMix } from "@/services/downloadApi";
import MarkdownPreview from "@/components/MarkdownPreview";
import { formatNumber } from "@/utils/format";
import { buildYouTubeWatchUrl } from "@/utils/youtubeLinks";

dayjs.extend(relativeTime);

type ModelOption = { value: string; label: string };

function toModelOptions(rows: ModelItem[]): ModelOption[] {
  const multiLib = rows.length > 1;
  const out: ModelOption[] = [];
  for (const row of rows) {
    const raw = row.supported_models_json?.trim();
    if (!raw) continue;
    try {
      const arr = JSON.parse(raw) as Array<string | { value?: string; label?: string }>;
      if (!Array.isArray(arr)) continue;
      for (const item of arr) {
        if (typeof item === "string" && item.trim()) {
          const name = item.trim();
          out.push({ value: name, label: multiLib ? `${name} (${row.name})` : name });
        } else if (item && typeof item === "object") {
          const v = String(item.value ?? "").trim();
          if (!v) continue;
          const display = String((item as { label?: string }).label ?? v).trim();
          out.push({ value: v, label: multiLib ? `${display} (${row.name})` : display });
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
  const { t } = useTranslation("youtube");

  /** 全局视频：四列可叠加排序，后端优先级为 发布时间 → 播放量 → 点赞数 → 评论数 */
  const VIDEO_SORT_METRICS = useMemo(() => [
    {
      field: "publish_time" as const,
      stateKey: "sort_publish_time" as const,
      label: t("globalVideo.sort.publishTime"),
      options: [
        { label: t("globalVideo.sort.newToOld"), value: "desc" as const },
        { label: t("globalVideo.sort.oldToNew"), value: "asc" as const },
      ],
    },
    {
      field: "view_count" as const,
      stateKey: "sort_view_count" as const,
      label: t("globalVideo.sort.viewCount"),
      options: [
        { label: t("globalVideo.sort.highToLow"), value: "desc" as const },
        { label: t("globalVideo.sort.lowToHigh"), value: "asc" as const },
      ],
    },
    {
      field: "like_count" as const,
      stateKey: "sort_like_count" as const,
      label: t("globalVideo.sort.likeCount"),
      options: [
        { label: t("globalVideo.sort.highToLow"), value: "desc" as const },
        { label: t("globalVideo.sort.lowToHigh"), value: "asc" as const },
      ],
    },
    {
      field: "comment_count" as const,
      stateKey: "sort_comment_count" as const,
      label: t("globalVideo.sort.commentCount"),
      options: [
        { label: t("globalVideo.sort.highToLow"), value: "desc" as const },
        { label: t("globalVideo.sort.lowToHigh"), value: "asc" as const },
      ],
    },
  ], [t]);
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
      message.warning(t('globalVideo.message.selectAtLeastOne'));
      return;
    }
    setDownloadLoading(true);
    try {
      const res = await submitDownload({ video_ids: Array.from(selectedVideoIds) });
      message.success(res.message || t('globalVideo.message.batchDownloadSubmitted', { count: res.task_count }));
      if (res.skipped?.length) {
        message.info(t('globalVideo.message.skippedExisting', { count: res.skipped.length }));
      }
      setSelectedVideoIds(new Set());
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : t('globalVideo.message.batchDownloadFailed'));
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
      message.error(detail || t('globalVideo.message.trackFailed'));
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
      message.success(res.message || t('globalVideo.message.extractSuccess', { count: res.highlights.length }));
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : t('globalVideo.message.extractFailed'));
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
        message.error(e instanceof Error ? e.message : t('globalVideo.message.loadModelAgentFailed'));
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
      message.error(t("youtube:globalVideo.message.loadVideoFailed"));
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
      message.warning(t('globalVideo.message.scrapeKeywordRequired'));
      return;
    }
    setScrapeLoading(true);
    try {
      const res = await scrapeVideoCommentsApi(scrapeVideoId, scrapeKeyword.trim());
      message.success(t('globalVideo.message.scrapeSuccess', { count: res.scraped_count, quota: res.quota_used }));
      setScrapeOpen(false);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err.response?.data?.detail ?? t('globalVideo.message.scrapeFailed'));
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
      message.error(typeof d === 'string' ? d : t('globalVideo.message.getResultFailed'));
    }
  };

  const handleAnalyzeVideo = async (video: VideoListItem) => {
    const videoId = video.id;
    const defaultModelId = modelOptions[0]?.value ?? "";
    const modelId = selectedModelByVideoId[videoId] ?? defaultModelId;
    if (!modelId) {
      message.warning(t("youtube:globalVideo.message.configModelFirst"));
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
      message.error(typeof d === 'string' ? d : t('globalVideo.message.analysisFailed'));
    } finally {
      setPanelLoading((prev) => ({ ...prev, [videoId]: false }));
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="bg-yc-bg-card border border-yc-border rounded-lg p-3 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-6 gap-2">
          <Input
            placeholder={t("youtube:globalVideo.filter.titleKeyword")}
            value={filters.keyword}
            onChange={(e) => setFilters((s) => ({ ...s, keyword: e.target.value }))}
          />
          <DatePicker.RangePicker
            value={filters.dateRange as any}
            onChange={(v) => setFilters((s) => ({ ...s, dateRange: v as any }))}
          />
          <InputNumber className="w-full" placeholder={t("youtube:globalVideo.filter.minDuration")} value={filters.min_duration} onChange={(v) => setFilters((s) => ({ ...s, min_duration: Number(v) || undefined }))} />
          <InputNumber className="w-full" placeholder={t("youtube:globalVideo.filter.maxDuration")} value={filters.max_duration} onChange={(v) => setFilters((s) => ({ ...s, max_duration: Number(v) || undefined }))} />
          <Select
            allowClear
            placeholder={t("youtube:globalVideo.filter.channel")}
            value={filters.channel_id}
            onChange={(v) => setFilters((s) => ({ ...s, channel_id: v }))}
            options={pool.map((x) => ({ label: x.title, value: x.id }))}
            className="min-w-0"
          />
          <Select
            allowClear
            placeholder={t("youtube:globalVideo.filter.definition")}
            value={filters.definition}
            onChange={(v) => setFilters((s) => ({ ...s, definition: v }))}
            options={[
              { label: "HD", value: "hd" },
              { label: "SD", value: "sd" },
            ]}
          />
          <Select
            allowClear
            placeholder={t("youtube:globalVideo.filter.privacy")}
            value={filters.privacy_status}
            onChange={(v) => setFilters((s) => ({ ...s, privacy_status: v }))}
            options={[
              { label: t("youtube:globalVideo.filter.public"), value: "public" },
              { label: t("youtube:globalVideo.filter.unlisted"), value: "unlisted" },
              { label: t("youtube:globalVideo.filter.private"), value: "private" },
            ]}
          />
          <div className="col-span-1 md:col-span-4 lg:col-span-6 space-y-2 pt-1 border-t border-yc-border-light mt-1">
            <p className="text-xs text-yc-text-tertiary">
              {t('globalVideo.sort.priorityHint')}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2">
              {VIDEO_SORT_METRICS.map(({ field, stateKey, label, options }) => (
                <div key={field} className="flex flex-col gap-1 min-w-0">
                  <span className="text-xs text-yc-text-tertiary">{label}</span>
                  <Select
                    allowClear
                    placeholder={t('globalVideo.sort.sortBy', { label })}
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
              {t('globalVideo.filter.screen')}
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
                  sort_publish_time: "desc" as "asc" | "desc" | undefined,
                  sort_view_count: undefined as "asc" | "desc" | undefined,
                  sort_like_count: undefined as "asc" | "desc" | undefined,
                  sort_comment_count: undefined as "asc" | "desc" | undefined,
                };
                setFilters(reset);
                void loadVideos(1, pageSize, reset);
              }}
            >
              {t('globalVideo.filter.reset')}
            </Button>
          </div>
        </div>
      </div>

      {selectedVideoIds.size > 0 && (
        <div className="flex items-center gap-3 bg-yc-info-bg border border-yc-info rounded-lg px-4 py-2">
          <CloudDownloadOutlined className="text-yc-info text-lg" />
          <span className="text-sm text-yc-info">{t('globalVideo.action.selectedVideos', { count: selectedVideoIds.size })}</span>
          <Button
            type="primary"
            size="small"
            loading={downloadLoading}
            onClick={() => void handleBatchDownload()}
          >
            {t('globalVideo.action.batchDownload')}
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<MergeOutlined />}
            onClick={() => setMixModalOpen(true)}
          >
            {t('globalVideo.action.aiMix')}
          </Button>
          <Button
            size="small"
            onClick={() => setSelectedVideoIds(new Set())}
          >
            {t('globalVideo.action.clearSelection')}
          </Button>
        </div>
      )}

      <div className="space-y-2">
        {loading ? (
          <div className="text-yc-text-tertiary">{t('globalVideo.message.loading')}</div>
        ) : (
          videos.map((video) => {
            const hasAnalyzed = video.has_analysis || !!analysisStatusOverride[video.id]?.has_analysis;
            const analyzedAt = analysisStatusOverride[video.id]?.analyzed_at ?? null;
            const watchUrl = buildYouTubeWatchUrl(video.yt_video_id);
            const openYouTube = (e: MouseEvent) => {
              e.stopPropagation();
              if (!watchUrl) {
                message.warning(t('globalVideo.message.noValidVideoId'));
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
                        aria-label={t("youtube:globalVideo.message.openVideo")}
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
                      {video.channel_title && <div className="text-xs text-yc-text-tertiary mt-0.5 truncate">{t('globalVideo.message.channelLabel')}{video.channel_title}</div>}
                      <Tag className="!border-yc-border !bg-yc-bg-card !text-yc-text-secondary">{video.definition.toUpperCase()}</Tag>
                      <Tag className="!border-yc-border !bg-yc-bg-card !text-yc-text-secondary">{video.privacy_status}</Tag>
                      {hasAnalyzed && (
                        <Tag
                          color="success"
                          icon={<CheckCircleOutlined />}
                          className="cursor-pointer"
                          onClick={(e) => { e.stopPropagation(); void handleViewAnalysis(video.id); }}
                        >
                          {t('globalVideo.message.analyzed')}{analyzedAt ? ` ${dayjs(analyzedAt).fromNow()}` : ''}
                        </Tag>
                      )}
                    </div>
                    <div className="text-yc-text-tertiary text-sm mt-2">
                      {t('globalVideo.message.publishedAt')} {video.published_at ? dayjs(video.published_at).format('YYYY-MM-DD HH:mm') : '-'} ·{' '}
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
                      <span className="text-yc-info flex items-center gap-1"><Eye className="h-4 w-4 shrink-0" aria-hidden />{t('globalVideo.message.viewsLabel')}{formatNumber(video.view_count)}</span>
                      <span className="text-yc-success flex items-center gap-1"><ThumbsUp className="h-4 w-4 shrink-0" aria-hidden />{t('globalVideo.message.likesLabel')}{formatNumber(video.like_count)}</span>
                      <span className="text-yc-warning flex items-center gap-1"><MessageCircle className="h-4 w-4 shrink-0" aria-hidden />{t('globalVideo.message.commentsLabel')}{formatNumber(video.comment_count)}</span>
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
                        {trackedChannelIds.has(video.yt_channel_id ?? "") ? t("youtube:globalVideo.action.tracked") : t("youtube:globalVideo.action.trackChannel")}
                      </Button>
                      <Button type="primary" size="small" onClick={() => openScrape(video.id)}>
                        {t('globalVideo.action.scrapeComments')}
                      </Button>
                      <Button
                        size="small"
                        icon={<ThunderboltOutlined />}
                        loading={Boolean(extractingHighlights[video.id])}
                        onClick={() => void handleExtractHighlights(video.id)}
                      >
                        {t('globalVideo.action.extractHighlights')}
                      </Button>
                      <Select
                        showSearch
                        placeholder={t("youtube:globalVideo.action.selectModel")}
                        style={{ minWidth: 160 }}
                        value={selectedModelByVideoId[video.id] ?? (modelOptions[0]?.value ?? undefined)}
                        options={modelOptions}
                        onChange={(v) => setSelectedModelByVideoId((prev) => ({ ...prev, [video.id]: String(v) }))}
                      />
                      <Select
                        allowClear
                        placeholder={t("youtube:globalVideo.action.selectAgent")}
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
                        {hasAnalyzed ? t("youtube:globalVideo.action.reanalyze") : t("youtube:globalVideo.action.oneClickAnalysis")}
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
                          {t('globalVideo.action.viewResult')}{analyzedAt ? `(${dayjs(analyzedAt).fromNow()})` : ''}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                {panelOpenVideoId === video.id ? (
                  <div className="mt-3 rounded-lg border border-yc-border bg-yc-bg-inset p-3">
                    {panelLoading[video.id] ? (
                      <div className="flex items-center gap-2 text-yc-text-secondary">
                        <Spin size="small" /> {t('globalVideo.message.analyzing')}
                      </div>
                    ) : panelContentByVideoId[video.id] ? (
                      <MarkdownPreview>{panelContentByVideoId[video.id]}</MarkdownPreview>
                    ) : (
                      <div className="text-yc-text-tertiary text-sm">
                        {hasAnalyzed
                          ? t("youtube:globalVideo.message.noCacheResult")
                          : t("youtube:globalVideo.message.noAnalysisResult")}
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
        title={t("youtube:globalVideo.modal.scrapeTitle")}
        open={scrapeOpen}
        onOk={() => void confirmScrape()}
        onCancel={() => setScrapeOpen(false)}
        confirmLoading={scrapeLoading}
        okText={t("youtube:globalVideo.modal.scrapeOk")}
      >
        <p className="text-sm text-yc-text-secondary mb-2">{t('globalVideo.modal.scrapeHint')}</p>
        <Input placeholder={t("youtube:globalVideo.modal.scrapePlaceholder")} value={scrapeKeyword} onChange={(e) => setScrapeKeyword(e.target.value)} />
      </Modal>

      <Modal
        title={t("youtube:globalVideo.action.aiMix")}
        open={mixModalOpen}
        onCancel={() => setMixModalOpen(false)}
        onOk={async () => {
          try {
            const res = await submitMix({
              video_ids: Array.from(selectedVideoIds),
              aspect_ratio: '9:16',
              use_highlights: true,
            });
            message.success(res.message || t('globalVideo.message.mixSubmitted'));
            setMixModalOpen(false);
            setSelectedVideoIds(new Set());
          } catch (err: unknown) {
            const d = err && typeof err === 'object' && 'response' in err
              ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
              : undefined;
            message.error(typeof d === 'string' ? d : t('globalVideo.message.mixFailed'));
          }
        }}
        okText={t('globalVideo.modal.mixOk')}
      >
        <div className="space-y-3">
          <p className="text-sm text-yc-text-secondary">
            {t('globalVideo.message.mixSelectedCount', { count: selectedVideoIds.size })}
          </p>
          <p className="text-xs text-yc-text-tertiary">
            {t('globalVideo.message.mixBackgroundHint')}
          </p>
        </div>
      </Modal>
    </div>
  );
}
