import { Button, DatePicker, Input, InputNumber, Pagination, Select, Tag, message } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import {
  ArrowLeft,
  BarChart3,
  Eye,
  MessageCircle,
  MoreHorizontal,
  Play,
  Sparkles,
  Star,
  ThumbsUp,
  Users,
  Youtube,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  analyzeYouTubeChannelAiApi,
  getYouTubeChannelDetailApi,
  listYouTubeVideosApi,
  type VideoListItem,
} from "@/services/authApi";
import { formatNumber } from "@/utils/format";
import { useTabStore } from "@/store/useTabStore";

dayjs.extend(relativeTime);

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
  const [filters, setFilters] = useState({
    keyword: "",
    dateRange: null as [dayjs.Dayjs, dayjs.Dayjs] | null,
    min_duration: undefined as number | undefined,
    max_duration: undefined as number | undefined,
    definition: undefined as string | undefined,
    privacy_status: undefined as string | undefined,
    sort_by: "publish_time_desc",
  });

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
      setTotal(data.total);
      setPage(data.page);
      setPageSize(data.page_size);
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
        const c = await getYouTubeChannelDetailApi(channelId);
        if (cancelled) return;
        setChannel(c);
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

  const backToList = () => {
    openTab({ id: "channel-list", title: "频道管理", path: "/youtube/channels", type: "channel-list" });
    setActiveTab("channel-list");
    navigate("/youtube/channels");
  };

  const hoursAgo = channel?.updated_at
    ? dayjs().diff(dayjs(channel.updated_at), "hour")
    : null;
  const aiTags = channel?.ai_tags ?? [];
  const hasAiInsight = aiTags.length > 0 || Boolean(channel?.ai_audience_age) || Boolean(channel?.ai_summary);

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
        {!hasAiInsight ? (
          <div className="rounded-lg border border-dashed border-violet-300 bg-violet-50 p-6 text-center">
            <Button
              type="primary"
              size="large"
              loading={aiAnalyzing}
              className="!bg-violet-600 !border-violet-600 hover:!bg-violet-500 hover:!border-violet-500"
              onClick={async () => {
                setAiAnalyzing(true);
                try {
                  const ai = await analyzeYouTubeChannelAiApi(channelId);
                  setChannel((prev) =>
                    prev
                      ? {
                          ...prev,
                          ai_tags: ai.tags,
                          ai_audience_age: ai.age_group,
                          ai_summary: ai.summary,
                        }
                      : prev
                  );
                  message.success("AI 深度分析完成");
                } catch {
                  message.error("AI 深度分析失败");
                } finally {
                  setAiAnalyzing(false);
                }
              }}
            >
              ✨ 运行 AI 深度分析
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
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
            <div className="rounded-lg border border-slate-200 p-3 bg-indigo-50/60">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
                <Users size={16} className="text-indigo-600" />
                受众画像
              </div>
              <div className="text-slate-800 text-sm leading-6">
                👥 受众推断：{channel?.ai_audience_age || "暂无推断结果"}
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 bg-slate-50">
              <div className="text-sm font-medium text-slate-700 mb-2">内容定位与套路</div>
              <div className="text-sm text-slate-700 leading-6">{channel?.ai_summary || "暂无分析总结"}</div>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-2">
        {loading && !videos.length ? (
          <div className="text-slate-500">加载中...</div>
        ) : (
          videos.map((video) => (
            <div key={video.id} className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm flex flex-col md:flex-row gap-4">
              <div className="relative w-full md:w-64 shrink-0">
                <img src={video.thumbnail_url || ""} alt="" className="w-full h-36 object-cover rounded" />
                <div className="absolute right-2 bottom-2 text-xs px-2 py-0.5 rounded bg-black/60 text-white">{video.duration_str}</div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-slate-900 truncate">{video.title}</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.definition.toUpperCase()}</Tag>
                  <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.privacy_status}</Tag>
                </div>
                <div className="text-slate-500 text-sm mt-2">
                  发布于 {video.published_at ? dayjs(video.published_at).format("YYYY-MM-DD HH:mm") : "-"} ·{" "}
                  {video.published_at ? dayjs(video.published_at).fromNow() : ""}
                </div>
              </div>
              <div className="flex flex-row md:flex-col justify-between md:w-56 gap-3 shrink-0">
                <div className="border border-slate-200 rounded-md p-2 text-sm space-y-1 flex-1">
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
                <div className="flex gap-1 text-slate-400 justify-end">
                  <Star size={18} className="cursor-pointer hover:text-amber-500" />
                  <Play size={18} className="cursor-pointer hover:text-blue-600" />
                  <BarChart3 size={18} className="cursor-pointer hover:text-slate-700" />
                  <MoreHorizontal size={18} className="cursor-pointer" />
                </div>
              </div>
            </div>
          ))
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
