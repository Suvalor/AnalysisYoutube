import { CloudDownloadOutlined, DeleteOutlined, PlayCircleOutlined, RedoOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Modal, Popconfirm, Progress, Select, Space, Spin, Table, Tag, Tooltip, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  listDownloadTasks,
  requestPlayToken,
  getDownloadFileUrl,
  retryDownloadTaskApi,
  deleteDownloadTaskApi,
  type DownloadTask,
  type DownloadStatus,
} from "@/services/downloadApi";
import { formatNumber } from "@/utils/format";

dayjs.extend(relativeTime);

const STATUS_CONFIG: Record<DownloadStatus, { color: string; label: string }> = {
  PENDING: { color: "default", label: "等待中" },
  DOWNLOADING: { color: "processing", label: "下载中" },
  COMPLETED: { color: "success", label: "已完成" },
  FAILED: { color: "error", label: "失败" },
};

function formatFileSize(bytes: number): string {
  if (bytes <= 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export default function DownloadList() {
  const [tasks, setTasks] = useState<DownloadTask[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<DownloadStatus | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [playingTaskId, setPlayingTaskId] = useState<number | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [retryingIds, setRetryingIds] = useState<Set<number>>(new Set());
  const [loadingPlayId, setLoadingPlayId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listDownloadTasks({
        status: statusFilter,
        offset: (page - 1) * pageSize,
        limit: pageSize,
      });
      setTasks(res.items);
      setTotal(res.total);
    } catch {
      message.error("获取下载列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter]);

  useEffect(() => {
    void fetchTasks();
  }, [fetchTasks]);

  // Auto-poll for downloading tasks (every 3s)
  useEffect(() => {
    const hasActive = tasks.some((t) => t.status === "DOWNLOADING" || t.status === "PENDING");
    if (hasActive) {
      if (!pollRef.current) {
        pollRef.current = setInterval(() => {
          void (async () => {
            try {
              const res = await listDownloadTasks({
                status: statusFilter,
                offset: (page - 1) * pageSize,
                limit: pageSize,
              });
              setTasks(res.items);
              setTotal(res.total);
            } catch {
              /* ignore */
            }
          })();
        }, 3000);
      }
    } else if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [tasks, statusFilter, page, pageSize]);

  const handleRetry = async (taskId: number) => {
    setRetryingIds((prev) => new Set(prev).add(taskId));
    try {
      await retryDownloadTaskApi(taskId);
      message.success("已重新开始下载");
      await fetchTasks();
    } catch {
      message.error("重试失败");
    } finally {
      setRetryingIds((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    }
  };

  const handleDelete = async (taskId: number) => {
    try {
      await deleteDownloadTaskApi(taskId);
      message.success("已删除");
      await fetchTasks();
    } catch {
      message.error("删除失败");
    }
  };

  const handlePlay = async (taskId: number) => {
    // M-02: guard against missing auth token
    const token = localStorage.getItem("access_token");
    if (!token) {
      message.error("登录已过期，请重新登录");
      return;
    }

    setLoadingPlayId(taskId);
    try {
      // C-01: request a short-lived play token instead of passing JWT in URL
      const { play_token } = await requestPlayToken(taskId);
      const url = `${getDownloadFileUrl(taskId)}?play_token=${encodeURIComponent(play_token)}`;
      setVideoUrl(url);
      setPlayingTaskId(taskId);
    } catch {
      message.error("获取播放令牌失败");
    } finally {
      setLoadingPlayId(null);
    }
  };

  const handleClosePlayer = () => {
    setVideoUrl(null);
    setPlayingTaskId(null);
  };

  const columns: ColumnsType<DownloadTask> = [
    {
      title: "视频",
      key: "video",
      width: 280,
      render: (_: unknown, record: DownloadTask) => (
        <div className="flex items-center gap-3">
          {record.thumbnail_url ? (
            <img
              src={record.thumbnail_url}
              alt=""
              className="w-24 h-14 object-cover rounded shrink-0"
            />
          ) : (
            <div className="w-24 h-14 bg-slate-100 rounded shrink-0 flex items-center justify-center text-slate-400 text-xs">
              无缩略图
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-slate-900 truncate" title={record.video_title ?? undefined}>
              {record.video_title || record.video_id}
            </div>
            <div className="text-xs text-slate-400 truncate">
              {record.video_channel_title ?? "--"}
            </div>
          </div>
        </div>
      ),
    },
    {
      title: "发布时间",
      dataIndex: "video_published_at",
      key: "video_published_at",
      width: 110,
      render: (t: string | null) => t ? dayjs(t).format("YYYY-MM-DD") : "--",
    },
    {
      title: "播放量",
      dataIndex: "video_view_count",
      key: "video_view_count",
      width: 80,
      render: (v: number | null) => v != null ? formatNumber(v) : "--",
    },
    {
      title: "点赞",
      dataIndex: "video_like_count",
      key: "video_like_count",
      width: 70,
      render: (v: number | null) => v != null ? formatNumber(v) : "--",
    },
    {
      title: "评论",
      dataIndex: "video_comment_count",
      key: "video_comment_count",
      width: 70,
      render: (v: number | null) => v != null ? formatNumber(v) : "--",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (status: DownloadStatus) => {
        const cfg = STATUS_CONFIG[status];
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "进度",
      dataIndex: "progress",
      key: "progress",
      width: 120,
      render: (progress: number, record: DownloadTask) => {
        if (record.status === "COMPLETED") return <Progress percent={100} size="small" />;
        if (record.status === "FAILED") return <Progress percent={progress} status="exception" size="small" />;
        if (record.status === "PENDING") return <Progress percent={0} size="small" />;
        return <Progress percent={Math.round(progress)} size="small" />;
      },
    },
    {
      title: "文件大小",
      dataIndex: "file_size",
      key: "file_size",
      width: 90,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: "下载时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 100,
      render: (t: string) => dayjs(t).fromNow(),
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      render: (_: unknown, record: DownloadTask) => (
        <Space size="small">
          {record.status === "COMPLETED" && record.has_file && (
            <Tooltip title="播放视频">
              <Button
                type="text"
                size="small"
                icon={<PlayCircleOutlined />}
                loading={loadingPlayId === record.id}
                disabled={loadingPlayId !== null}
                onClick={() => void handlePlay(record.id)}
              />
            </Tooltip>
          )}
          {record.status === "FAILED" && (
            <>
              <Tooltip title="重试下载">
                <Button
                  type="text"
                  size="small"
                  icon={<RedoOutlined />}
                  loading={retryingIds.has(record.id)}
                  onClick={() => void handleRetry(record.id)}
                />
              </Tooltip>
              <Popconfirm
                title="确定删除该失败任务？"
                onConfirm={() => void handleDelete(record.id)}
                okText="删除"
                cancelText="取消"
              >
                <Tooltip title="删除任务">
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                  />
                </Tooltip>
              </Popconfirm>
              <Tooltip title={record.error_message}>
                <Tag color="error" style={{ cursor: "help", maxWidth: 120 }} className="truncate">
                  错误
                </Tag>
              </Tooltip>
            </>
          )}
        </Space>
      ),
    },
  ];

  const playingTask = tasks.find((t) => t.id === playingTaskId);

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold" style={{ color: "var(--color-text-primary)" }}>
          <CloudDownloadOutlined className="mr-2" />
          下载管理
        </h2>
        <Space>
          <Select<DownloadStatus | undefined>
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            allowClear
            placeholder="筛选状态"
            style={{ width: 140 }}
            options={[
              { value: "PENDING", label: "等待中" },
              { value: "DOWNLOADING", label: "下载中" },
              { value: "COMPLETED", label: "已完成" },
              { value: "FAILED", label: "失败" },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void fetchTasks()}>
            刷新
          </Button>
        </Space>
      </div>

      {/* Table */}
      <Spin spinning={loading}>
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="id"
          size="small"
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          style={{ flex: 1 }}
        />
      </Spin>

      {/* Video Player Modal */}
      <Modal
        open={playingTaskId !== null}
        title={playingTask ? `播放视频 - ${playingTask.video_title ?? playingTask.video_id}` : "播放视频"}
        onCancel={handleClosePlayer}
        footer={null}
        width={800}
        destroyOnClose
      >
        {videoUrl && (
          <video
            src={videoUrl}
            controls
            autoPlay
            style={{ width: "100%", maxHeight: "70vh", borderRadius: 8 }}
          />
        )}
      </Modal>
    </div>
  );
}