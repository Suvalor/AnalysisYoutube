import { Button, Input, Modal, Select, Spin, Table, message } from "antd";
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
    try {
      const res = await analyzeYouTubeBatchApi({ urls: urls.trim() });
      message.success(
        `成功分析 ${res.channels_count} 个频道，共获取 ${res.videos_count} 个视频。本次消耗 API 额度 ${res.quota_used} 点。`
      );
      setUrls("");
      await load();
      void getYouTubeQuotaDashboardApi();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error(typeof err.response?.data?.detail === "string" ? err.response.data.detail : "添加失败");
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
        try {
          const res = await batchUpdateChannelsApi();
          message.success(
            `更新完成：频道 ${res.updated_channels}，视频 ${res.updated_videos}。本次消耗 API 额度 ${res.quota_used} 点。`
          );
          await load();
          void getYouTubeQuotaDashboardApi();
        } catch (e: unknown) {
          const err = e as { response?: { data?: { detail?: string } } };
          message.error(err.response?.data?.detail ?? "更新失败");
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
          <span className="font-medium text-slate-900">{r.channel.title}</span>
        </div>
      ),
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
