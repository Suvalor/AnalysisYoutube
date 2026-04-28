import { CheckCircleOutlined, CloudDownloadOutlined } from "@ant-design/icons";
import { Button, DatePicker, Input, InputNumber, Pagination, Select, Space, Spin, Tag, message } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import {
  ArrowLeft,
  Eye,
  MessageCircle,
  Sparkles,
  ThumbsUp,
  Users,
  Youtube,
} from "lucide-react";
import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  analyzeYouTubeChannelAiApi,
  getYouTubeChannelDetailApi,
  listYouTubeVideosApi,
  batchCheckVideoAnalysisApi,
  type VideoListItem,
  type BatchAnalysisStatusItem,
} from "@/services/authApi";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";
import { analyzeYouTubeVideoApi, getYouTubeVideoAnalysisApi } from "@/services/videosApi";
import { submitDownload } from "@/services/downloadApi";
import { formatNumber } from "@/utils/format";
import { useTabStore } from "@/store/useTabStore";
import MarkdownPreview from "@/components/MarkdownPreview";
import { buildYouTubeWatchUrl } from "@/utils/youtubeLinks";

dayjs.extend(relativeTime);

/** 解析模型库中的 supported_models_json，得到可选的 LLM 模型名列表 */
function parseSupportedModels(json: string | null): string[] {
  if (!json?.trim()) return [];
  try {
    const data = JSON.parse(json) as unknown;
    if (!Array.isArray(data)) return [];
    const out: string[] = [];
    for (const item of data) {
      if (typeof item === "string" && item.trim()) out.push(item.trim());
      else if (item && typeof item === "object" && "value" in item) {
        const v = String((item as { value?: string }).value ?? "").trim();
        if (v) out.push(v);
      }
    }
    return out;
  } catch {
    return [];
  }
}

function axiosDetail(err: unknown): string {
  if (err && typeof err === "object" && "response" in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response;
    const d = r?.data?.detail;
    if (typeof d === "string") return d;
  }
  return "";
}

type Props = { channelId: number };

export default function ChannelDetail({ channelId }: Props) {
  const navigate = useNavigate();
  const openTab = useTabStore((s) => s.openTab);
  const setActiveTab = useTabStore((s) => s.setActiveTab);

  const [channel, setChannel] = useState<Awaited<ReturnType<typeof getYouTubeChannelDetailApi>> | null>(null);
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [libraryModels, setLibraryModels] = useState<ModelItem[]>([]);
  const [promptAgents, setPromptAgents] = useState<PromptItem[]>([]);
  const [selectedModelLibId, setSelectedModelLibId] = useState<number | undefined>(undefined);
  const [llmModelName, setLlmModelName] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState<number | undefined>(undefined);
  const [filters, setFilters] = useState({
    keyword: "",
    dateRange: null as [dayjs.Dayjs, dayjs.Dayjs] | null,
    min_duration: undefined as number | undefined,
    max_duration: undefined as number | undefined,
    definition: undefined as string | undefined,
    privacy_status: undefined as string | undefined,
    sort_by: "publish_time_desc",
  });

  // 视频维度 AI 分析折叠（同一时间仅允许展开一条）
  const [videoAnalysisPanelOpenId, setVideoAnalysisPanelOpenId] = useState<number | null>(null);
  const [videoAnalysisLoadingById, setVideoAnalysisLoadingById] = useState<Record<number, boolean>>({});
  const [videoAnalysisContentById, setVideoAnalysisContentById] = useState<Record<number, string>>({});
  /** 分析成功后立即标为已分析，与列表接口 has_analysis 合并 */
  const [videoAnalysisStatusOverride, setVideoAnalysisStatusOverride] = useState<Record<number, BatchAnalysisStatusItem>>({});
  const [selectedModelByVideoId, setSelectedModelByVideoId] = useState<Record<number, string>>({});
  const [selectedAgentByVideoId, setSelectedAgentByVideoId] = useState<Record<number, number | undefined>>({});
  const [downloadingVideoIds, setDownloadingVideoIds] = useState<Set<string>>(new Set());

  const handleDownloadVideo = async (ytVideoId: string) => {
    if (!ytVideoId?.trim()) {
      message.warning('该视频缺少有效的 YouTube 视频 ID');
      return;
    }
    if (downloadingVideoIds.has(ytVideoId)) return;
    setDownloadingVideoIds((prev) => new Set(prev).add(ytVideoId));
    try {
      const res = await submitDownload({ video_ids: [ytVideoId] });
      message.success(res.message || '下载任务已提交');
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : '下载提交失败');
    } finally {
      setDownloadingVideoIds((prev) => {
        const next = new Set(prev);
        next.delete(ytVideoId);
        return next;
      });
    }
  };

  const videoModelOptions = useMemo(() => {
    const dedup = new Map<string, { value: string; label: string }>();
    for (const m of libraryModels) {
      const values = parseSupportedModels(m.supported_models_json);
      for (const v of values) {
        dedup.set(v, { value: v, label: `${m.name} / ${v}` });
      }
    }
    return Array.from(dedup.values());
  }, [libraryModels]);

  const loadVideos = async (p: number, ps: number, f: typeof filters) => {
    setLoading(true);
    try {
      const data = await listYouTubeVideosApi({
        keyword: f.keyword || undefined,
        start_date: f.dateRange?.[0]?.format("YYYY-MM-DD"),
        end_date: f.dateRange?.[1]?.format("YYYY-MM-DD"),
        min_duration: f.min_duration,
        max_duration: f.max_duration,
        channel_id: channelId,
        definition: f.definition,
        privacy_status: f.privacy_status,
        sort_by: f.sort_by,
        page: p,
        page_size: ps,
      });
      setVideos(data.items);
      setVideoAnalysisStatusOverride({});
      setTotal(data.total);
      setPage(data.page);
      setPageSize(data.page_size);
      // Batch-check analysis status to ensure has_analysis is accurate
      const videoIds = data.items.map((v) => v.id);
      if (videoIds.length) {
        try {
          const statusMap = await batchCheckVideoAnalysisApi(videoIds);
          setVideoAnalysisStatusOverride(statusMap);
        } catch {
          // Non-critical: fallback to has_analysis from list API
        }
      }
    } catch {
      message.error("加载视频失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [c, models, prompts] = await Promise.all([
          getYouTubeChannelDetailApi(channelId),
          listModelsApi().catch(() => [] as ModelItem[]),
          listPromptsApi().catch(() => [] as PromptItem[]),
        ]);
        if (cancelled) return;
        setChannel(c);
        setLibraryModels(models);
        setPromptAgents(prompts);
        useTabStore.getState().openTab({
          id: `channel-detail-${channelId}`,
          title: c.title || "博主详情",
          path: `/youtube/channel/${channelId}`,
          type: "channel-detail",
          channelId,
        });
        await loadVideos(1, 20, filters);
      } catch {
        if (!cancelled) message.error("加载频道失败");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelId]);

  /** 详情接口若带有上次分析所用的模型与智能体，用于预填表单 */
  useEffect(() => {
    if (!channel) return;
    if (channel.ai_source_model_library_id) {
      setSelectedModelLibId(channel.ai_source_model_library_id);
      setLlmModelName(channel.ai_source_llm_model_name?.trim() ?? "");
      setSelectedAgentId(channel.ai_source_agent_id ?? undefined);
    }
  }, [
    channel?.id,
    channel?.ai_source_model_library_id,
    channel?.ai_source_llm_model_name,
    channel?.ai_source_agent_id,
  ]);

  /** 无历史溯源时，默认选中第一个已配置 Key 的模型库 */
  useEffect(() => {
    if (libraryModels.length === 0 || selectedModelLibId !== undefined) return;
    if (channel?.ai_source_model_library_id) return;
    const first = libraryModels.find((m) => m.has_api_key);
    if (first) {
      setSelectedModelLibId(first.id);
      const opts = parseSupportedModels(first.supported_models_json);
      if (opts.length) setLlmModelName(opts[0]!);
    }
  }, [libraryModels, channel?.ai_source_model_library_id, selectedModelLibId]);

  const selectedLib = useMemo(
    () => libraryModels.find((m) => m.id === selectedModelLibId),
    [libraryModels, selectedModelLibId]
  );
  const llmNameOptions = useMemo(
    () => parseSupportedModels(selectedLib?.supported_models_json ?? null),
    [selectedLib?.supported_models_json]
  );

  /** 切换模型库时，若当前模型名不在新列表中则自动切到列表首项 */
  useEffect(() => {
    if (!selectedModelLibId) return;
    if (llmNameOptions.length === 0) return;
    if (!llmNameOptions.includes(llmModelName)) {
      setLlmModelName(llmNameOptions[0]!);
    }
  }, [selectedModelLibId, llmNameOptions, llmModelName]);

  const runAiDeepAnalysis = async () => {
    if (selectedModelLibId === undefined) {
      message.warning("请选择模型配置（来自设置中心 - 模型管理）");
      return;
    }
    const name = llmModelName.trim();
    if (!name) {
      message.warning("请选择或填写要调用的 LLM 模型名称");
      return;
    }
    setAiAnalyzing(true);
    try {
      const ai = await analyzeYouTubeChannelAiApi(channelId, {
        model_library_id: selectedModelLibId,
        llm_model_name: name,
        agent_id: selectedAgentId ?? null,
      });
      setChannel((prev) =>
        prev
          ? {
              ...prev,
              ai_tags: ai.tags,
              ai_expertise: ai.expertise,
              ai_audience_age: ai.age_group,
              ai_summary: ai.summary,
              ai_analyzed_at: ai.analyzed_at ?? prev.ai_analyzed_at ?? null,
              ai_source_model_library_id: ai.model_library_id ?? prev.ai_source_model_library_id ?? null,
              ai_source_llm_model_name: ai.llm_model_name ?? prev.ai_source_llm_model_name ?? null,
              ai_source_agent_id: ai.agent_id ?? prev.ai_source_agent_id ?? null,
            }
          : prev
      );
      message.success("AI 深度分析完成并已保存");
    } catch (e) {
      message.error(axiosDetail(e) || "AI 深度分析失败");
    } finally {
      setAiAnalyzing(false);
    }
  };

  const handleViewVideoAnalysis = async (videoId: number) => {
    // Toggle: if panel is already open for this video, close it
    if (videoAnalysisPanelOpenId === videoId) {
      setVideoAnalysisPanelOpenId(null);
      return;
    }
    setVideoAnalysisPanelOpenId(videoId);
    // Skip fetch if content is already cached
    if (videoAnalysisContentById[videoId]) return;
    try {
      const res = await getYouTubeVideoAnalysisApi(videoId);
      setVideoAnalysisContentById((prev) => ({ ...prev, [videoId]: res.content }));
      setVideoAnalysisStatusOverride((prev) => ({ ...prev, [videoId]: { has_analysis: true, analyzed_at: res.updated_at } }));
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : "获取视频分析失败");
    }
  };

  const handleAnalyzeVideo = async (video: VideoListItem) => {
    const videoId = video.id;
    const defaultModelId = videoModelOptions[0]?.value ?? "";
    const modelId = selectedModelByVideoId[videoId] ?? defaultModelId;
    if (!modelId) {
      message.warning("请先在「设置中心 → 模型管理」维护可用模型，并为当前视频选择 Model ID");
      return;
    }

    const agentId = selectedAgentByVideoId[videoId] ?? selectedAgentId ?? promptAgents[0]?.id;
    setVideoAnalysisPanelOpenId(videoId);
    setVideoAnalysisLoadingById((prev) => ({ ...prev, [videoId]: true }));
    try {
      const res = await analyzeYouTubeVideoApi({
        video_id: videoId,
        model_id: modelId,
        agent_id: agentId ?? null,
      });
      setVideoAnalysisContentById((prev) => ({ ...prev, [videoId]: res.content }));
      setVideoAnalysisStatusOverride((prev) => ({ ...prev, [videoId]: { has_analysis: true, analyzed_at: res.updated_at } }));
    } catch (err: unknown) {
      const d = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      message.error(typeof d === 'string' ? d : "视频 AI 深度分析失败");
    } finally {
      setVideoAnalysisLoadingById((prev) => ({ ...prev, [videoId]: false }));
    }
  };

  const backToList = () => {
    openTab({ id: "channel-list", title: "频道管理", path: "/youtube/channels", type: "channel-list" });
    setActiveTab("channel-list");
    navigate("/youtube/channels");
  };

  const hoursAgo = channel?.updated_at
    ? dayjs().diff(dayjs(channel.updated_at), "hour")
    : null;
  const aiTags = channel?.ai_tags ?? [];
  const hasAiInsight =
    aiTags.length > 0 ||
    Boolean(channel?.ai_expertise?.trim()) ||
    Boolean(channel?.ai_audience_age) ||
    Boolean(channel?.ai_summary);

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex flex-col lg:flex-row lg:items-start gap-4">
        <div className="flex-1 space-y-3">
          <div className="flex items-center gap-3 flex-wrap">
            <Button icon={<ArrowLeft size={16} />} onClick={backToList}>
              返回频道列表
            </Button>
            <div className="flex items-center gap-2">
              <Youtube className="text-red-600" size={28} />
              <h2 className="text-xl font-bold text-slate-900">{channel?.title ?? "…"}</h2>
            </div>
          </div>

          <div className="border-2 border-red-500 rounded-lg p-4 bg-white shadow-sm max-w-3xl">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-xs text-slate-500">订阅数</div>
                <div className="text-xl font-semibold text-slate-900">{formatNumber(channel?.subscriber_count ?? 0)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">总视频数</div>
                <div className="text-xl font-semibold text-slate-900">{formatNumber(channel?.video_count ?? 0)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">总播放量</div>
                <div className="text-xl font-semibold text-slate-900">{formatNumber(channel?.total_views ?? 0)}</div>
              </div>
            </div>
            <div className="text-center text-xs text-slate-400 mt-3">
              数据更新：{hoursAgo !== null ? `${hoursAgo} 小时前` : "—"}
            </div>
          </div>
        </div>

        <div className="flex gap-2 shrink-0">
          <Button
            onClick={async () => {
              try {
                const c = await getYouTubeChannelDetailApi(channelId);
                setChannel(c);
                await loadVideos(page, pageSize, filters);
                message.success("已刷新");
              } catch {
                message.error("刷新失败");
              }
            }}
          >
            刷新
          </Button>
          <Button
            onClick={() => {
              message.info("导出功能开发中");
            }}
          >
            导出数据
          </Button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <Input
            placeholder="搜索标题"
            value={filters.keyword}
            onChange={(e) => setFilters((s) => ({ ...s, keyword: e.target.value }))}
          />
          <DatePicker.RangePicker value={filters.dateRange as any} onChange={(v) => setFilters((s) => ({ ...s, dateRange: v as any }))} />
          <InputNumber className="w-full" placeholder="最小时长(秒)" value={filters.min_duration} onChange={(v) => setFilters((s) => ({ ...s, min_duration: Number(v) || undefined }))} />
          <InputNumber className="w-full" placeholder="最大时长(秒)" value={filters.max_duration} onChange={(v) => setFilters((s) => ({ ...s, max_duration: Number(v) || undefined }))} />
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
          <Select
            value={filters.sort_by}
            onChange={(v) => {
              setFilters((s) => {
                const next = { ...s, sort_by: v };
                void loadVideos(1, pageSize, next);
                return next;
              });
            }}
            options={[
              { label: "发布时间 ↓", value: "publish_time_desc" },
              { label: "发布时间 ↑", value: "publish_time_asc" },
              { label: "播放量 ↓", value: "view_count_desc" },
              { label: "点赞 ↓", value: "like_count_desc" },
              { label: "评论 ↓", value: "comment_count_desc" },
            ]}
          />
          <Button type="primary" onClick={() => void loadVideos(1, pageSize, filters)}>
            筛选
          </Button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={18} className="text-violet-500" />
          <div className="text-base font-semibold text-slate-900">AI 深度洞察 (AI Insight)</div>
        </div>
        {channel?.ai_analyzed_at ? (
          <div className="text-xs text-slate-500 mb-3">
            最近分析时间：
            {dayjs(channel.ai_analyzed_at).format("YYYY-MM-DD HH:mm")}
            {channel.ai_source_llm_model_name ? ` · 模型：${channel.ai_source_llm_model_name}` : ""}
          </div>
        ) : null}

        {hasAiInsight ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
            <div className="rounded-lg border border-slate-200 p-3">
              <div className="text-sm font-medium text-slate-700 mb-2">核心标签</div>
              <div className="flex flex-wrap gap-2">
                {aiTags.length ? (
                  aiTags.map((tag, idx) => (
                    <Tag
                      key={`${tag}-${idx}`}
                      className="!rounded-full !px-3 !py-0.5 !m-0 !border-transparent !text-white"
                      color={["magenta", "purple", "blue", "cyan", "green"][idx % 5]}
                    >
                      {tag}
                    </Tag>
                  ))
                ) : (
                  <div className="text-slate-400 text-sm">暂无标签</div>
                )}
              </div>
            </div>
            <div className="rounded-lg border border-amber-200 p-3 bg-amber-50/70">
              <div className="text-sm font-medium text-slate-700 mb-2">擅长内容</div>
              <div className="text-sm text-slate-800 leading-6">{channel?.ai_expertise?.trim() || "暂无"}</div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 bg-indigo-50/60">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
                <Users size={16} className="text-indigo-600" />
                受众画像
              </div>
              <div className="text-slate-800 text-sm leading-6">
                受众推断：{channel?.ai_audience_age || "暂无推断结果"}
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 bg-slate-50">
              <div className="text-sm font-medium text-slate-700 mb-2">内容定位与套路</div>
              <div className="text-sm text-slate-700 leading-6">{channel?.ai_summary || "暂无分析总结"}</div>
            </div>
          </div>
        ) : null}

        <div
          className={
            hasAiInsight
              ? "rounded-lg border border-slate-200 bg-slate-50/80 p-4 space-y-3"
              : "rounded-lg border border-dashed border-violet-300 bg-violet-50 p-6"
          }
        >
          {!hasAiInsight ? (
            <div className="text-sm text-slate-600 text-center mb-2">选择模型与智能体后运行分析（结果会写入数据库并与频道列表同步）</div>
          ) : (
            <div className="text-sm font-medium text-slate-700">重新分析</div>
          )}
          <Space wrap className="w-full" size="middle">
            <Select
              placeholder="选择模型配置 (LLM)"
              allowClear={false}
              className="min-w-[200px]"
              value={selectedModelLibId}
              onChange={(v) => {
                setSelectedModelLibId(v);
                const row = libraryModels.find((m) => m.id === v);
                const opts = parseSupportedModels(row?.supported_models_json ?? null);
                setLlmModelName(opts.length ? opts[0]! : "");
              }}
              options={libraryModels.map((m) => ({
                value: m.id,
                label: m.has_api_key ? m.name : `${m.name}（未配置 API Key）`,
                disabled: !m.has_api_key,
              }))}
            />
            {llmNameOptions.length > 0 ? (
              <Select
                placeholder="选择具体模型名"
                className="min-w-[200px]"
                value={llmModelName || undefined}
                onChange={(v) => setLlmModelName(v)}
                options={llmNameOptions.map((v) => ({ value: v, label: v }))}
              />
            ) : (
              <Input
                placeholder="模型名称（JSON 未配置时在网关使用的 model 名）"
                className="min-w-[220px] max-w-xs"
                value={llmModelName}
                onChange={(e) => setLlmModelName(e.target.value)}
              />
            )}
            <Select
              allowClear
              placeholder="选择智能体 (Agent，可选)"
              className="min-w-[200px]"
              value={selectedAgentId}
              onChange={(v) => setSelectedAgentId(v)}
              options={promptAgents.map((p) => ({ value: p.id, label: p.title }))}
            />
            <Button
              type="primary"
              size="large"
              loading={aiAnalyzing}
              disabled={!libraryModels.some((m) => m.has_api_key)}
              className="!bg-violet-600 !border-violet-600 hover:!bg-violet-500 hover:!border-violet-500"
              onClick={() => void runAiDeepAnalysis()}
            >
              {hasAiInsight ? "重新运行 AI 深度分析" : "运行 AI 深度分析"}
            </Button>
          </Space>
          {!libraryModels.some((m) => m.has_api_key) ? (
            <div className="text-xs text-amber-700">请先在「设置中心 → 模型管理」添加至少一条带 API Key 的模型配置。</div>
          ) : null}
        </div>
      </div>

      <div className="space-y-2">
        {loading && !videos.length ? (
          <div className="text-slate-500">加载中...</div>
        ) : (
          videos.map((video) => {
            const hasAnalyzed = video.has_analysis || !!videoAnalysisStatusOverride[video.id]?.has_analysis;
            const analyzedAt = videoAnalysisStatusOverride[video.id]?.analyzed_at ?? null;
            const watchUrl = buildYouTubeWatchUrl(video.yt_video_id);
            const openYouTube = (e: MouseEvent) => {
              e.stopPropagation();
              if (!watchUrl) {
                message.warning("该视频缺少有效的 YouTube 视频 ID，无法跳转");
                return;
              }
              window.open(watchUrl, "_blank", "noopener,noreferrer");
            };

            const modelIdForVideo = selectedModelByVideoId[video.id] ?? videoModelOptions[0]?.value ?? "";
            const agentIdForVideo = selectedAgentByVideoId[video.id] ?? selectedAgentId ?? promptAgents[0]?.id;

            return (
              <div key={video.id} className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
                <div className="flex flex-col md:flex-row gap-4">
                  {/* 缩略图 */}
                  <div className="relative w-full md:w-64 shrink-0">
                    {watchUrl ? (
                      <button
                        type="button"
                        onClick={openYouTube}
                        className="block w-full p-0 border-0 bg-transparent cursor-pointer rounded overflow-hidden"
                        aria-label="在 YouTube 打开视频"
                      >
                        <img src={video.thumbnail_url || ""} alt="" className="w-full h-36 object-cover rounded" />
                      </button>
                    ) : (
                      <img src={video.thumbnail_url || ""} alt="" className="w-full h-36 object-cover rounded opacity-90" />
                    )}
                    <div className="absolute right-2 bottom-2 text-xs px-2 py-0.5 rounded bg-black/60 text-white">
                      {video.duration_str}
                    </div>
                  </div>
                  {/* 信息区 */}
                  <div className="flex-1 min-w-0">
                    {watchUrl ? (
                      <button
                        type="button"
                        onClick={openYouTube}
                        className="font-semibold text-slate-900 truncate w-full p-0 border-0 bg-transparent cursor-pointer hover:text-blue-700 transition-colors"
                      >
                        {video.title}
                      </button>
                    ) : (
                      <div className="font-semibold text-slate-900 truncate">{video.title}</div>
                    )}
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.definition.toUpperCase()}</Tag>
                      <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.privacy_status}</Tag>
                      {hasAnalyzed && (
                        <Tag
                          color="success"
                          icon={<CheckCircleOutlined />}
                          className="cursor-pointer"
                          onClick={(e) => { e.stopPropagation(); void handleViewVideoAnalysis(video.id); }}
                        >
                          已分析{analyzedAt ? ` ${dayjs(analyzedAt).fromNow()}` : ''}
                        </Tag>
                      )}
                    </div>
                    <div className="text-slate-500 text-sm mt-2">
                      发布于 {video.published_at ? dayjs(video.published_at).format("YYYY-MM-DD HH:mm") : "-"} ·{" "}
                      {video.published_at ? dayjs(video.published_at).fromNow() : ""}
                    </div>
                    {/* 统计数据 */}
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm">
                      <span className="text-blue-600 flex items-center gap-1"><Eye className="h-4 w-4 shrink-0" aria-hidden />播放量：{formatNumber(video.view_count)}</span>
                      <span className="text-emerald-600 flex items-center gap-1"><ThumbsUp className="h-4 w-4 shrink-0" aria-hidden />点赞：{formatNumber(video.like_count)}</span>
                      <span className="text-orange-500 flex items-center gap-1"><MessageCircle className="h-4 w-4 shrink-0" aria-hidden />评论：{formatNumber(video.comment_count)}</span>
                    </div>
                  </div>
                </div>

                {/* 操作按钮栏 */}
                <div className="mt-3 flex flex-wrap gap-2 items-center">
                  <Select
                    showSearch
                    placeholder="选择模型"
                    style={{ minWidth: 160 }}
                    value={modelIdForVideo || undefined}
                    options={videoModelOptions.map((o) => ({ value: o.value, label: o.label }))}
                    onChange={(v) => setSelectedModelByVideoId((prev) => ({ ...prev, [video.id]: String(v) }))}
                  />
                  <Select
                    allowClear
                    placeholder="选择智能体（可选）"
                    style={{ minWidth: 160 }}
                    value={agentIdForVideo ?? undefined}
                    options={promptAgents.map((p) => ({ value: p.id, label: p.title }))}
                    onChange={(v) =>
                      setSelectedAgentByVideoId((prev) => ({ ...prev, [video.id]: v === undefined ? undefined : Number(v) }))
                    }
                  />
                  <Button
                    type={hasAnalyzed ? "dashed" : "primary"}
                    size="small"
                    onClick={() => void handleAnalyzeVideo(video)}
                    loading={Boolean(videoAnalysisLoadingById[video.id])}
                  >
                    {hasAnalyzed ? "重新分析" : "一键 AI 深度分析"}
                  </Button>
                  <Button
                    size="small"
                    icon={<CloudDownloadOutlined />}
                    loading={downloadingVideoIds.has(video.yt_video_id)}
                    onClick={() => void handleDownloadVideo(video.yt_video_id)}
                  >
                    下载
                  </Button>
                  {hasAnalyzed && (
                    <Button
                      type="primary"
                      size="small"
                      icon={<CheckCircleOutlined />}
                      onClick={() => void handleViewVideoAnalysis(video.id)}
                      disabled={Boolean(videoAnalysisLoadingById[video.id])}
                      style={videoAnalysisPanelOpenId !== video.id ? { backgroundColor: '#52c41a', borderColor: '#52c41a' } : undefined}
                    >
                      查看结果{analyzedAt ? `(${dayjs(analyzedAt).fromNow()})` : ''}
                    </Button>
                  )}
                </div>

                {videoAnalysisPanelOpenId === video.id ? (
                  <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                    {videoAnalysisLoadingById[video.id] ? (
                      <div className="flex items-center gap-2 text-slate-600">
                        <Spin size="small" />
                        分析中…
                      </div>
                    ) : videoAnalysisContentById[video.id] ? (
                      <MarkdownPreview>{videoAnalysisContentById[video.id]}</MarkdownPreview>
                    ) : (
                      <div className="text-slate-500 text-sm">
                        {hasAnalyzed
                          ? "暂无缓存展示。请点击「查看结果」拉取已保存的分析内容。"
                          : "暂无分析结果。点击「一键 AI 深度分析」生成内容。"}
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            );
          })
        )}
      </div>

      <div className="flex justify-end">
        <Pagination
          current={page}
          pageSize={pageSize}
          total={total}
          showSizeChanger
          onChange={(p, ps) => void loadVideos(p, ps, filters)}
        />
      </div>
    </div>
  );
}
