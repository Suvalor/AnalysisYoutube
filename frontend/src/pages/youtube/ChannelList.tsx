import { Button, Input, Modal, Popover, Select, Spin, Table, Tag, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  analyzeYouTubeBatchApi,
  batchUpdateChannelsApi,
  deleteYouTubeChannelApi,
  getYouTubeQuotaDashboardApi,
  listYouTubeChannelsApi,
  type YouTubeAnalyzeResponse,
} from "@/services/authApi";
import { formatNumber } from "@/utils/format";
import { useTabStore } from "@/store/useTabStore";

type Row = {
  pool_id: number;
  group_name: string;
  added_at: string;
  channel: YouTubeAnalyzeResponse["channel"];
};

export default function ChannelList() {
  const navigate = useNavigate();
  const openTab = useTabStore((s) => s.openTab);
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [sortBy, setSortBy] = useState<string>("subscriber_desc");
  const [urls, setUrls] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [updating, setUpdating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listYouTubeChannelsApi({ sort_by: sortBy });
      setRows(data.map((x) => ({ pool_id: x.pool_id, group_name: x.group_name, added_at: x.added_at, channel: x.channel })));
    } catch {
      message.error("加载频道列表失败");
    } finally {
      setLoading(false);
    }
  }, [sortBy]);

  useEffect(() => {
    void load();
  }, [load]);

  const onRowClick = (record: Row) => {
    const id = record.channel.id;
    openTab({
      id: `channel-detail-${id}`,
      title: record.channel.title || "博主详情",
      path: `/youtube/channel/${id}`,
      type: "channel-detail",
      channelId: id,
    });
    navigate(`/youtube/channel/${id}`);
  };

  const onBatchAdd = async () => {
    if (!urls.trim()) {
      message.warning("请输入 YouTube 频道链接");
      return;
    }
    setAnalyzing(true);
    message.loading({ content: "正在拉取频道与视频数据，并进行 AI 标签分析，请稍候…", key: "yt-add", duration: 0 });
    try {
      const res = await analyzeYouTubeBatchApi({ urls: urls.trim() });
      message.success({
        content: `成功分析 ${res.channels_count} 个频道，共获取 ${res.videos_count} 个视频。本次消耗 API 额度 ${res.quota_used} 点。`,
        key: "yt-add",
      });
      setUrls("");
      await load();
      void getYouTubeQuotaDashboardApi();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error({
        content: typeof err.response?.data?.detail === "string" ? err.response.data.detail : "添加失败",
        key: "yt-add",
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const onBatchUpdate = async () => {
    const q = await getYouTubeQuotaDashboardApi();
    const n = rows.length;
    const estimated = n === 0 ? 0 : Math.floor((n + 49) / 50) + 2 * n;
    Modal.confirm({
      title: "确认一键更新",
      content: `本次预计消耗 API 额度: ${estimated} 点，今日剩余额度: ${q.today_remaining} 点，是否继续？`,
      okText: "继续",
      cancelText: "取消",
      onOk: async () => {
        setUpdating(true);
        message.loading({
          content: "正在同步 YouTube 数据，并对缺少标签的频道执行 AI 补全，请稍候…",
          key: "yt-batch",
          duration: 0,
        });
        try {
          const res = await batchUpdateChannelsApi();
          const aiPart =
            res.ai_enriched != null || res.ai_failed != null
              ? ` AI 补全成功 ${res.ai_enriched ?? 0} 个${(res.ai_failed ?? 0) > 0 ? `，失败 ${res.ai_failed} 个` : ""}。`
              : "";
          message.success({
            content: `更新完成：频道 ${res.updated_channels}，视频 ${res.updated_videos}。消耗 API ${res.quota_used} 点。${aiPart}`,
            key: "yt-batch",
          });
          await load();
          void getYouTubeQuotaDashboardApi();
        } catch (e: unknown) {
          const err = e as { response?: { data?: { detail?: string } } };
          message.error({ content: err.response?.data?.detail ?? "更新失败", key: "yt-batch" });
        } finally {
          setUpdating(false);
        }
      },
    });
  };

  const columns: ColumnsType<Row> = [
    {
      title: "博主",
      key: "title",
      render: (_, r) => (
        <div className="flex items-center gap-2">
          <img src={r.channel.thumbnail_url || ""} alt="" className="w-9 h-9 rounded-full border border-slate-200" />
          <div className="min-w-0">
            <div className="font-medium text-slate-900 truncate">{r.channel.title}</div>
            {r.channel.description?.trim() ? (
              <Popover
                title="频道简介"
                content={
                  <Typography.Paragraph className="!mb-0 max-w-sm whitespace-pre-wrap text-slate-700 text-xs">
                    {r.channel.description}
                  </Typography.Paragraph>
                }
                trigger="click"
              >
                <button
                  type="button"
                  className="text-xs text-blue-600 hover:text-blue-500 truncate max-w-[200px] block text-left"
                  onClick={(e) => e.stopPropagation()}
                >
                  简介预览
                </button>
              </Popover>
            ) : (
              <span className="text-xs text-slate-400">暂无简介</span>
            )}
          </div>
        </div>
      ),
    },
    {
      title: "标签 / 擅长",
      key: "tags_expertise",
      width: 260,
      render: (_, r) => {
        const tags = r.channel.ai_tags ?? [];
        const exp = r.channel.ai_expertise?.trim();
        return (
          <div className="space-y-1" onClick={(e) => e.stopPropagation()}>
            <div className="flex flex-wrap gap-1">
              {tags.length ? (
                tags.map((tag, idx) => (
                  <Tag key={`${tag}-${idx}`} color={["blue", "geekblue", "cyan", "purple", "magenta"][idx % 5]} className="!m-0">
                    {tag}
                  </Tag>
                ))
              ) : (
                <span className="text-xs text-slate-400">待 AI 分析</span>
              )}
            </div>
            {exp ? <div className="text-xs text-slate-600 line-clamp-2 leading-snug">{exp}</div> : null}
          </div>
        );
      },
    },
    {
      title: "订阅数",
      dataIndex: ["channel", "subscriber_count"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: "总播放量",
      dataIndex: ["channel", "total_views"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: "视频数",
      dataIndex: ["channel", "video_count"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: "操作",
      key: "op",
      render: (_, r) => (
        <Button
          size="small"
          danger
          onClick={async (e) => {
            e.stopPropagation();
            await deleteYouTubeChannelApi(r.pool_id);
            message.success("已移除");
            await load();
          }}
        >
          移除
        </Button>
      ),
    },
  ];

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm space-y-2">
        <div className="text-sm text-slate-600">批量录入（分号或换行分隔多个链接）</div>
        <div className="flex flex-col md:flex-row gap-2 md:items-start">
          <Input.TextArea
            rows={3}
            className="max-w-xl"
            placeholder="请输入 YouTube 频道主页链接，支持输入多个，请使用分号 (;) 或换行分隔。例如：https://youtube.com/@a; https://youtube.com/channel/b"
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
          />
          <div className="flex gap-2">
            <Button type="primary" loading={analyzing} onClick={() => void onBatchAdd()}>
              添加关注
            </Button>
            <Button type="primary" loading={updating} onClick={() => void onBatchUpdate()}>
              一键更新数据
            </Button>
          </div>
        </div>
      </div>

      <Spin spinning={loading}>
        <div className="bg-white border border-slate-200 rounded-lg p-2 shadow-sm space-y-2">
          <div className="flex justify-end px-2 pt-1">
            <span className="text-sm text-slate-600 mr-2 self-center">排序</span>
            <Select
              style={{ width: 220 }}
              value={sortBy}
              onChange={(v) => setSortBy(v)}
              options={[
                { value: "added_desc", label: "最近添加" },
                { value: "subscriber_desc", label: "订阅数 ↓" },
                { value: "subscriber_asc", label: "订阅数 ↑" },
                { value: "total_views_desc", label: "总播放量 ↓" },
                { value: "total_views_asc", label: "总播放量 ↑" },
                { value: "video_count_desc", label: "视频数 ↓" },
                { value: "video_count_asc", label: "视频数 ↑" },
              ]}
            />
          </div>
          <Table<Row>
            rowKey="pool_id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            pagination={{ pageSize: 10 }}
            onRow={(record) => ({
              onClick: () => onRowClick(record),
              className: "cursor-pointer hover:bg-slate-50",
            })}
          />
        </div>
      </Spin>
    </div>
  );
}
