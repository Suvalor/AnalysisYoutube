import { Button, DatePicker, Input, InputNumber, Modal, Pagination, Select, Spin, Tag, message } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { Eye, MessageCircle, ThumbsUp } from "lucide-react";
import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { listYouTubeChannelsApi, listYouTubeVideosAllApi, scrapeVideoCommentsApi, type VideoListItem } from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";
import { analyzeYouTubeVideoApi, getYouTubeVideoAnalysisApi, type YouTubeVideoAnalysisResponse } from "@/services/videosApi";
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
  const [selectedModelByVideoId, setSelectedModelByVideoId] = useState<Record<number, string>>({});
  const [selectedAgentByVideoId, setSelectedAgentByVideoId] = useState<Record<number, number | undefined>>({});

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
      setTotal(data.total);
      setPage(data.page);
      setPageSize(data.page_size);
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
    // 仅首次挂载拉取；后续由筛选按钮或分页触发
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

  const openVideoPanel = (videoId: number) => {
    setPanelOpenVideoId(videoId);
  };

  const handleViewAnalysis = async (videoId: number) => {
    openVideoPanel(videoId);
    try {
      const res = await getYouTubeVideoAnalysisApi(videoId);
      setPanelContentByVideoId((prev) => ({ ...prev, [videoId]: res.content }));
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "获取分析结果失败");
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
    openVideoPanel(videoId);
    setPanelLoading((prev) => ({ ...prev, [videoId]: true }));
    try {
      const res = await analyzeYouTubeVideoApi({
        video_id: videoId,
        model_id: modelId,
        agent_id: agentId ?? null,
      });
      setPanelContentByVideoId((prev) => ({ ...prev, [videoId]: res.content }));
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "视频分析失败");
    } finally {
      setPanelLoading((prev) => ({ ...prev, [videoId]: false }));
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
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
          <div className="col-span-1 md:col-span-4 lg:col-span-6 space-y-2 pt-1 border-t border-slate-100 mt-1">
            <p className="text-xs text-slate-400">
              以下四列可同时参与排序；数据库优先级为：发布时间 → 播放量 → 点赞数 → 评论数（先按第一列排，相同再按下一列）。
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2">
              {VIDEO_SORT_METRICS.map(({ field, stateKey, label, options }) => (
                <div key={field} className="flex flex-col gap-1 min-w-0">
                  <span className="text-xs text-slate-500">{label}</span>
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

      <div className="space-y-2">
        {loading ? (
          <div className="text-slate-500">加载中...</div>
        ) : (
          videos.map((video) => {
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
              <div key={video.id} className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
                <div className="flex flex-col md:flex-row gap-4">
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
                    <div className="absolute right-2 bottom-2 text-xs px-2 py-0.5 rounded bg-black/60 text-white pointer-events-none">
                      {video.duration_str}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    {watchUrl ? (
                      <button
                        type="button"
                        onClick={openYouTube}
                        className="font-semibold text-slate-900 truncate text-left w-full p-0 border-0 bg-transparent cursor-pointer hover:text-blue-700 transition-colors"
                      >
                        {video.title}
                      </button>
                    ) : (
                      <div className="font-semibold text-slate-900 truncate">{video.title}</div>
                    )}
                    {video.channel_title && <div className="text-xs text-slate-500 mt-0.5 truncate">频道：{video.channel_title}</div>}
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.definition.toUpperCase()}</Tag>
                      <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.privacy_status}</Tag>
                    </div>
                    <div className="text-slate-500 text-sm mt-2">
                      发布于 {video.published_at ? dayjs(video.published_at).format("YYYY-MM-DD HH:mm") : "-"} ·{" "}
                      {video.published_at ? dayjs(video.published_at).fromNow() : ""}
                    </div>
                  </div>
                  <div className="flex flex-col md:flex-col gap-3 md:w-52 shrink-0 justify-between">
                    <div className="border border-slate-200 rounded-md p-2 text-sm space-y-1">
                      <div className="text-blue-600 flex items-center gap-1.5">
                        <Eye className="h-4 w-4 shrink-0" aria-hidden />
                        <span>播放量：{formatNumber(video.view_count)}</span>
                      </div>
                      <div className="text-emerald-600 flex items-center gap-1.5">
                        <ThumbsUp className="h-4 w-4 shrink-0" aria-hidden />
                        <span>点赞：{formatNumber(video.like_count)}</span>
                      </div>
                      <div className="text-orange-500 flex items-center gap-1.5">
                        <MessageCircle className="h-4 w-4 shrink-0" aria-hidden />
                        <span>评论：{formatNumber(video.comment_count)}</span>
                      </div>
                    </div>

                    <Button type="primary" size="small" onClick={() => openScrape(video.id)}>
                      抓取评论
                    </Button>

                    <div className="space-y-2 w-full">
                      <Select
                        showSearch
                        placeholder="选择模型（Model）"
                        className="w-full"
                        value={selectedModelByVideoId[video.id] ?? (modelOptions[0]?.value ?? undefined)}
                        options={modelOptions}
                        onChange={(v) => setSelectedModelByVideoId((prev) => ({ ...prev, [video.id]: String(v) }))}
                      />
                      <Select
                        allowClear
                        placeholder="选择智能体（Agent，可选）"
                        className="w-full"
                        value={selectedAgentByVideoId[video.id] ?? undefined}
                        options={promptAgents.map((p) => ({ value: p.id, label: p.title }))}
                        onChange={(v) => setSelectedAgentByVideoId((prev) => ({ ...prev, [video.id]: v === undefined ? undefined : Number(v) }))}
                      />
                      <div className="flex gap-2 w-full">
                        <Button
                          type="primary"
                          size="small"
                          onClick={() => void handleAnalyzeVideo(video)}
                          loading={Boolean(panelLoading[video.id])}
                          className="!flex-1"
                        >
                          一键 AI 视频分析
                        </Button>
                        <Button
                          size="small"
                          onClick={() => void handleViewAnalysis(video.id)}
                          disabled={Boolean(panelLoading[video.id])}
                        >
                          查看结果
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>

                {panelOpenVideoId === video.id ? (
                  <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                    {panelLoading[video.id] ? (
                      <div className="flex items-center gap-2 text-slate-600">
                        <Spin size="small" /> 分析中…
                      </div>
                    ) : panelContentByVideoId[video.id] ? (
                      <MarkdownPreview>{panelContentByVideoId[video.id]}</MarkdownPreview>
                    ) : (
                      <div className="text-slate-500 text-sm">暂无分析结果。点击「一键 AI 视频分析」生成内容。</div>
                    )}
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>

      <div className="flex justify-end bg-white border border-slate-200 rounded-lg p-3">
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
        <p className="text-sm text-slate-600 mb-2">将使用 YouTube commentThreads 接口按关键字搜索评论（最多 100 条）。</p>
        <Input placeholder="搜索关键字" value={scrapeKeyword} onChange={(e) => setScrapeKeyword(e.target.value)} />
      </Modal>
    </div>
  );
}
