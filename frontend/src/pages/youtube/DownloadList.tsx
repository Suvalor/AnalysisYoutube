import { CloudDownloadOutlined, DeleteOutlined, PlayCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Modal, Progress, Select, Space, Spin, Table, Tag, Tooltip, message } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useEffect, useRef, useState } from "react";
import {
  listDownloadTasks,
  getDownloadFileUrl,
  type DownloadTask,
  type DownloadStatus,
} from "@/services/downloadApi";

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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTasks = async () => {
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
  };

  useEffect(() => {
    void fetchTasks();
  }, [page, pageSize, statusFilter]);

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

  const columns = [
    {
      title: "视频 ID",
      dataIndex: "video_id",
      key: "video_id",
      width: 140,
      render: (vid: string) => (
        <a
          href={`https://www.youtube.com/watch?v=${vid}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "var(--color-primary)" }}
        >
          {vid}
        </a>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (status: DownloadStatus) => {
        const cfg = STATUS_CONFIG[status];
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "进度",
      dataIndex: "progress",
      key: "progress",
      width: 180,
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
      width: 110,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 140,
      render: (t: string) => dayjs(t).fromNow(),
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      render: (_: unknown, record: DownloadTask) => (
        <Space size="small">
          {record.has_file && record.status === "COMPLETED" && (
            <Tooltip title="播放视频">
              <Button
                type="text"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => setPlayingTaskId(record.id)}
              />
            </Tooltip>
          )}
          {record.status === "FAILED" && (
            <Tooltip title={record.error_message}>
              <Tag color="error" style={{ cursor: "help", maxWidth: 120 }} className="truncate">
                错误
              </Tag>
            </Tooltip>
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
        title={playingTask ? `播放视频 - ${playingTask.video_id}` : "播放视频"}
        onCancel={() => setPlayingTaskId(null)}
        footer={null}
        width={800}
        destroyOnClose
      >
        {playingTask && (
          <video
            src={getDownloadFileUrl(playingTask.id)}
            controls
            autoPlay
            style={{ width: "100%", maxHeight: "70vh", borderRadius: 8 }}
          />
        )}
      </Modal>
    </div>
  );
}
