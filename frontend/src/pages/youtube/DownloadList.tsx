import { CloudDownloadOutlined, DeleteOutlined, MergeOutlined, PlayCircleOutlined, RedoOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Modal, Popconfirm, Progress, Select, Space, Spin, Table, Tag, Tooltip, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  listDownloadTasks,
  requestPlayToken,
  getDownloadFileUrl,
  retryDownloadTaskApi,
  deleteDownloadTaskApi,
  submitMix,
  type DownloadTask,
  type DownloadStatus,
} from "@/services/downloadApi";
import { formatNumber } from "@/utils/format";

dayjs.extend(relativeTime);

/** 下载状态颜色映射（标签由 t() 动态获取） */
const STATUS_CONFIG: Record<DownloadStatus, { color: string; labelKey: string }> = {
  PENDING: { color: "default", labelKey: "download.status.pending" },
  DOWNLOADING: { color: "processing", labelKey: "download.status.downloading" },
  COMPLETED: { color: "success", labelKey: "download.status.completed" },
  FAILED: { color: "error", labelKey: "download.status.failed" },
};

function formatFileSize(bytes: number): string {
  if (bytes <= 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export default function DownloadList() {
  const { t } = useTranslation("video");
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
  const [selectedRowKeys, setSelectedRowKeys] = useState<Set<number>>(new Set());
  const [mixModalOpen, setMixModalOpen] = useState(false);
  const [mixSubmitting, setMixSubmitting] = useState(false);
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
      message.error(t("download.loadFailed"));
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
      message.success(t("download.retrySuccess"));
      await fetchTasks();
    } catch {
      message.error(t("download.retryFailed"));
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
      message.success(t("download.deleteSuccess"));
      await fetchTasks();
    } catch {
      message.error(t("download.deleteFailed"));
    }
  };

  const handlePlay = async (taskId: number) => {
    // M-02: guard against missing auth token
    const token = localStorage.getItem("access_token");
    if (!token) {
      message.error(t("download.message.tokenExpired"));
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
      message.error(t("download.loadFailed"));
    } finally {
      setLoadingPlayId(null);
    }
  };

  const handleClosePlayer = () => {
    setVideoUrl(null);
    setPlayingTaskId(null);
  };

  const handleMixSubmit = async () => {
    setMixSubmitting(true);
    try {
      const res = await submitMix({
        video_ids: Array.from(selectedRowKeys).map(String),
        aspect_ratio: "9:16",
        use_highlights: true,
      });
      message.success(res.message || t("download.message.mixSubmitted", { defaultValue: "Mix task submitted" }));
      setMixModalOpen(false);
      setSelectedRowKeys(new Set());
    } catch (err: unknown) {
      const d =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : t("download.message.mixFailed", { defaultValue: "Mix submission failed" }));
    } finally {
      setMixSubmitting(false);
    }
  };

  const completedTaskIds = new Set(
    tasks.filter((t) => t.status === "COMPLETED" && t.has_file).map((t) => t.id),
  );

  const columns: ColumnsType<DownloadTask> = [
    {
      title: t("download.title"),
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
            <div className="w-24 h-14 bg-yc-bg-secondary rounded shrink-0 flex items-center justify-center text-yc-text-tertiary text-xs">
              {t("download.noThumbnail", { defaultValue: "No thumbnail" })}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-yc-text-primary break-words" title={record.video_title ?? undefined}>
              {record.video_title || record.video_id}
            </div>
            <div className="text-xs text-yc-text-tertiary truncate">
              {record.video_channel_title ?? "--"}
            </div>
          </div>
        </div>
      ),
    },
    {
      title: t("table.publishedAt"),
      dataIndex: "video_published_at",
      key: "video_published_at",
      width: 110,
      render: (t: string | null) => t ? dayjs(t).format("YYYY-MM-DD") : "--",
    },
    {
      title: t("table.views"),
      dataIndex: "video_view_count",
      key: "video_view_count",
      width: 80,
      render: (v: number | null) => v != null ? formatNumber(v) : "--",
    },
    {
      title: t("table.likes"),
      dataIndex: "video_like_count",
      key: "video_like_count",
      width: 70,
      render: (v: number | null) => v != null ? formatNumber(v) : "--",
    },
    {
      title: t("table.comments"),
      dataIndex: "video_comment_count",
      key: "video_comment_count",
      width: 70,
      render: (v: number | null) => v != null ? formatNumber(v) : "--",
    },
    {
      title: t("download.status"),
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (status: DownloadStatus) => {
        const cfg = STATUS_CONFIG[status];
        return <Tag color={cfg.color}>{t(cfg.labelKey)}</Tag>;
      },
    },
    {
      title: t("download.progress", { defaultValue: "Progress" }),
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
      title: t("download.label.fileSize"),
      dataIndex: "file_size",
      key: "file_size",
      width: 90,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: t("download.createdAt"),
      dataIndex: "created_at",
      key: "created_at",
      width: 100,
      render: (t: string) => dayjs(t).fromNow(),
    },
    {
      title: t("download.action"),
      key: "actions",
      width: 120,
      render: (_: unknown, record: DownloadTask) => (
        <Space size="small">
          {record.status === "COMPLETED" && record.has_file && (
            <Tooltip title={t("download.playVideo", { defaultValue: "Play Video" })}>
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
              <Tooltip title={t("download.retryDownload", { defaultValue: "Retry Download" })}>
                <Button
                  type="text"
                  size="small"
                  icon={<RedoOutlined />}
                  loading={retryingIds.has(record.id)}
                  onClick={() => void handleRetry(record.id)}
                />
              </Tooltip>
              <Popconfirm
                title={t("download.confirmDeleteFailed", { defaultValue: "Confirm delete this failed task?" })}
                onConfirm={() => void handleDelete(record.id)}
                okText={t("download.delete")}
                cancelText={t("download.cancel", { defaultValue: "Cancel" })}
              >
                <Tooltip title={t("download.deleteTask", { defaultValue: "Delete Task" })}>
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                  />
                </Tooltip>
              </Popconfirm>
              <Tooltip title={record.error_message}>
                <Tag color="error" style={{ cursor: "help", maxWidth: 120 }} className="truncate">
                  {t("download.error", { defaultValue: "Error" })}
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
          {t("download.title")}
        </h2>
        <Space>
          <Select<DownloadStatus | undefined>
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            allowClear
            placeholder={t("download.status")}
            style={{ width: 140 }}
            options={[
              { value: "PENDING", label: t("download.status.pending") },
              { value: "DOWNLOADING", label: t("download.status.downloading") },
              { value: "COMPLETED", label: t("download.status.completed") },
              { value: "FAILED", label: t("download.status.failed") },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void fetchTasks()}>
            {t("action.refresh")}
          </Button>
        </Space>
      </div>

      {/* Batch action bar for selected tasks */}
      {selectedRowKeys.size > 0 && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
          <span className="text-sm text-blue-600">{t("download.selectedCompleted", { count: selectedRowKeys.size, defaultValue: `${selectedRowKeys.size} completed videos selected` })}</span>
          <Button
            type="primary"
            size="small"
            icon={<MergeOutlined />}
            onClick={() => setMixModalOpen(true)}
          >
            {t("download.aiMix", { defaultValue: "AI Mix" })}
          </Button>
          <Button
            size="small"
            onClick={() => setSelectedRowKeys(new Set())}
          >
            {t("download.clearSelection", { defaultValue: "Clear Selection" })}
          </Button>
        </div>
      )}

      {/* Table */}
      <Spin spinning={loading}>
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="id"
          size="small"
          rowSelection={{
            selectedRowKeys: Array.from(selectedRowKeys),
            onChange: (keys) => setSelectedRowKeys(new Set(keys as number[])),
            getCheckboxProps: (record) => ({
              disabled: !completedTaskIds.has(record.id),
              name: record.video_title ?? String(record.video_id),
            }),
          }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (total) => t("download.totalRecords", { total }),
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
        title={playingTask ? t("download.playVideoTitle", { title: playingTask.video_title ?? playingTask.video_id, defaultValue: `Play Video - ${playingTask.video_title ?? playingTask.video_id}` }) : t("download.playVideo", { defaultValue: "Play Video" })}
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

      {/* Mix confirmation modal */}
      <Modal
        title={t("download.aiMix")}
        open={mixModalOpen}
        onCancel={() => setMixModalOpen(false)}
        onOk={() => void handleMixSubmit()}
        okText={t("download.submitMix", { defaultValue: "Submit Mix" })}
        confirmLoading={mixSubmitting}
      >
        <div className="space-y-3">
          <p className="text-sm text-yc-text-secondary">
            {t("download.mixSelectedCount", { count: selectedRowKeys.size, defaultValue: `AI mix will be performed on ${selectedRowKeys.size} selected completed videos, using extracted highlights when available.` })}
          </p>
          <p className="text-xs text-yc-text-tertiary">
            {t("download.mixBackgroundHint", { defaultValue: "Mix is a background task. Check progress in Assets after submission." })}
          </p>
        </div>
      </Modal>
    </div>
  );
}