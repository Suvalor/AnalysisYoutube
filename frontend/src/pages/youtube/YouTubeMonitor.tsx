import { Button, DatePicker, Input, InputNumber, Modal, Pagination, Select, Table, Tag, message } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useEffect, useMemo, useState } from "react";
import {
  analyzeYouTubeApi,
  batchUpdateChannelsApi,
  deleteYouTubeChannelApi,
  getYouTubeQuotaDashboardApi,
  listYouTubeChannelsApi,
  listYouTubeVideosApi,
  type YouTubeAnalyzeResponse,
} from "@/services/authApi";

dayjs.extend(relativeTime);

function formatNumber(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

export default function YouTubeMonitor() {
  const [tableLoading, setTableLoading] = useState(false);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [updating, setUpdating] = useState(false);
  const [pool, setPool] = useState<Array<{ pool_id: number; group_name: string; channel: YouTubeAnalyzeResponse["channel"] }>>([]);
  const [videos, setVideos] = useState<YouTubeAnalyzeResponse["videos"]>([]);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoTotal, setVideoTotal] = useState(0);
  const [videoPage, setVideoPage] = useState(1);
  const [videoPageSize, setVideoPageSize] = useState(20);
  const [quota, setQuota] = useState<{ today_remaining: number } | null>(null);
  const [filters, setFilters] = useState({
    keyword: "",
    dateRange: null as [dayjs.Dayjs, dayjs.Dayjs] | null,
    min_duration: undefined as number | undefined,
    max_duration: undefined as number | undefined,
    channel_id: undefined as number | undefined,
    definition: undefined as string | undefined,
    privacy_status: undefined as string | undefined,
    sort_by: "publish_time_desc",
  });

  const loadPool = async () => {
    try {
      setTableLoading(true);
      const data = await listYouTubeChannelsApi();
      setPool(data.map((x) => ({ pool_id: x.pool_id, group_name: x.group_name, channel: x.channel })));
    } catch {
      message.error("加载关注列表失败");
    } finally {
      setTableLoading(false);
    }
  };

  const loadQuota = async () => {
    const d = await getYouTubeQuotaDashboardApi();
    setQuota({ today_remaining: d.today_remaining });
    return d;
  };

  const loadVideos = async (nextFilters = filters, page = videoPage, pageSize = videoPageSize) => {
    setVideoLoading(true);
    try {
      const data = await listYouTubeVideosApi({
        keyword: nextFilters.keyword || undefined,
        start_date: nextFilters.dateRange?.[0]?.format("YYYY-MM-DD"),
        end_date: nextFilters.dateRange?.[1]?.format("YYYY-MM-DD"),
        min_duration: nextFilters.min_duration,
        max_duration: nextFilters.max_duration,
        channel_id: nextFilters.channel_id,
        definition: nextFilters.definition,
        privacy_status: nextFilters.privacy_status,
        sort_by: nextFilters.sort_by,
        page,
        page_size: pageSize,
      });
      setVideos(data.items);
      setVideoTotal(data.total);
      setVideoPage(data.page);
      setVideoPageSize(data.page_size);
    } catch {
      message.error("加载视频列表失败");
    } finally {
      setVideoLoading(false);
    }
  };

  useEffect(() => {
    void loadPool();
    void loadVideos();
    void loadQuota();
  }, []);

  const onAddChannel = async () => {
    if (!youtubeUrl.trim()) {
      message.warning("请输入 YouTube 频道链接");
      return;
    }
    try {
      await analyzeYouTubeApi({ youtube_url: youtubeUrl.trim() });
      message.success("添加并抓取成功");
      setYoutubeUrl("");
      await loadPool();
      await loadVideos();
      await loadQuota();
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "添加失败");
    }
  };

  const onBatchUpdate = async () => {
    const q = await loadQuota();
    const estimated = pool.length * 102;
    Modal.confirm({
      title: "确认一键更新",
      content: `本次预计消耗 API 额度: ${estimated} 点，今日剩余额度: ${q.today_remaining} 点，是否继续？`,
      okText: "继续",
      cancelText: "取消",
      onOk: async () => {
        setUpdating(true);
        try {
          const res = await batchUpdateChannelsApi();
          message.success(`更新完成：频道 ${res.updated_channels}，视频 ${res.updated_videos}`);
          await loadPool();
          await loadVideos();
          await loadQuota();
        } catch (e: any) {
          message.error(e?.response?.data?.detail ?? "更新失败");
        } finally {
          setUpdating(false);
        }
      },
    });
  };

  const columns = useMemo(
    () => [
      {
        title: "博主信息",
        key: "info",
        render: (_: unknown, row: (typeof pool)[number]) => (
          <div className="flex items-center gap-3">
            <img src={row.channel.thumbnail_url || ""} className="w-10 h-10 rounded-full border border-slate-200" />
            <div className="text-slate-900 font-medium">{row.channel.title}</div>
          </div>
        ),
      },
      { title: "订阅数", dataIndex: ["channel", "subscriber_count"], render: (v: number) => formatNumber(v) },
      { title: "总播放量", dataIndex: ["channel", "total_views"], render: (v: number) => formatNumber(v) },
      { title: "已收录视频数", dataIndex: ["channel", "video_count"], render: (v: number) => formatNumber(v) },
      {
        title: "操作",
        key: "action",
        render: (_: unknown, row: (typeof pool)[number]) => (
          <div className="flex gap-2">
            <Button size="small" onClick={() => loadVideos({ ...filters, channel_id: row.channel.id }, 1, videoPageSize)}>
              查看分析
            </Button>
            <Button
              size="small"
              danger
              onClick={async () => {
                await deleteYouTubeChannelApi(row.pool_id);
                message.success("删除成功");
                await loadPool();
                await loadVideos();
              }}
            >
              删除
            </Button>
          </div>
        ),
      },
    ],
    [pool, filters]
  );

  return (
    <div className="min-h-screen bg-[#F8F9FA] p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <div className="flex flex-col md:flex-row gap-2 md:items-center md:justify-end">
            <Input
              className="max-w-[420px]"
              placeholder="输入 YouTube 频道链接"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
            />
            <Button type="primary" onClick={onAddChannel}>
              添加关注
            </Button>
            <Button type="primary" loading={updating} onClick={onBatchUpdate}>
              一键更新数据
            </Button>
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <Table
            rowKey="pool_id"
            loading={tableLoading}
            dataSource={pool}
            columns={columns}
            pagination={{ pageSize: 8 }}
          />
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm">
          <div className="grid grid-cols-1 md:grid-cols-8 gap-2">
            <Input
              placeholder="搜索标题关键词"
              value={filters.keyword}
              onChange={(e) => setFilters((s) => ({ ...s, keyword: e.target.value }))}
            />
            <DatePicker.RangePicker
              value={filters.dateRange as any}
              onChange={(v) => setFilters((s) => ({ ...s, dateRange: v as any }))}
            />
            <InputNumber
              className="w-full"
              placeholder="最小时长(秒)"
              value={filters.min_duration}
              onChange={(v) => setFilters((s) => ({ ...s, min_duration: Number(v) || undefined }))}
            />
            <InputNumber
              className="w-full"
              placeholder="最大时长(秒)"
              value={filters.max_duration}
              onChange={(v) => setFilters((s) => ({ ...s, max_duration: Number(v) || undefined }))}
            />
            <Select
              allowClear
              placeholder="按频道过滤"
              value={filters.channel_id}
              onChange={(v) => setFilters((s) => ({ ...s, channel_id: v }))}
              options={pool.map((x) => ({ label: x.channel.title, value: x.channel.id }))}
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
              placeholder="隐私状态"
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
              onChange={(v) => setFilters((s) => ({ ...s, sort_by: v }))}
              options={[
                { label: "发布时间倒序", value: "publish_time_desc" },
                { label: "发布时间正序", value: "publish_time_asc" },
                { label: "播放量倒序", value: "view_count_desc" },
              ]}
            />
            <div className="flex gap-2">
              <Button
                type="primary"
                onClick={() => {
                  setVideoPage(1);
                  void loadVideos(filters, 1, videoPageSize);
                }}
              >
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
                    sort_by: "publish_time_desc",
                  };
                  setFilters(reset);
                  setVideoPage(1);
                  void loadVideos(reset, 1, videoPageSize);
                }}
              >
                重置
              </Button>
            </div>
          </div>
        </div>
        <div className="space-y-2">
          {videoLoading ? (
            <div className="text-slate-500 text-sm">加载中...</div>
          ) : (
            videos.map((video) => (
              <div key={video.id} className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm flex gap-4">
                <div className="relative w-64 shrink-0">
                  <img src={video.thumbnail_url || ""} className="w-full h-36 object-cover rounded" />
                  <div className="absolute right-2 bottom-2 text-xs px-2 py-0.5 rounded bg-black/60 text-white">{video.duration_str}</div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-slate-900 truncate">{video.title}</div>
                  <div className="mt-2 flex gap-2">
                    <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.definition.toUpperCase()}</Tag>
                    <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.privacy_status}</Tag>
                    <Tag className="!border-slate-200 !bg-white !text-slate-700">{video.category_id || "N/A"}</Tag>
                  </div>
                  <div className="text-slate-500 text-sm mt-3">
                    发布于 {video.published_at ? dayjs(video.published_at).format("YYYY-MM-DD HH:mm") : "-"} 数据更新：
                    {video.published_at ? dayjs(video.published_at).fromNow() : "-"}
                  </div>
                </div>
                <div className="w-56 border border-slate-200 rounded-md p-2 text-sm">
                  <div className="text-blue-600">播放量：{formatNumber(video.view_count)}</div>
                  <div className="text-emerald-600">点赞数：{formatNumber(video.like_count)}</div>
                  <div className="text-orange-500">评论数：{formatNumber(video.comment_count)}</div>
                </div>
                <div className="text-slate-500">⋯</div>
              </div>
            ))
          )}
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm flex justify-end">
          <Pagination
            current={videoPage}
            pageSize={videoPageSize}
            total={videoTotal}
            showSizeChanger
            onChange={(p, ps) => {
              void loadVideos(filters, p, ps);
            }}
          />
        </div>
      </div>
    </div>
  );
}

