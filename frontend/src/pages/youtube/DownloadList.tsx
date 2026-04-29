import { CloudDownloadOutlined, PlayCircleOutlined, RedoOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Modal, Progress, Select, Space, Tag, Tooltip, message } from "antd";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  listDownloadTasks,
  getDownloadFileUrl,
  retryDownloadTaskApi,
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
  const [retryingIds, setRetryingIds] = useState<Set<number>>(new Set());
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

      {/* Card Grid */}
      <div className="flex-1 overflow-auto">
        {loading && tasks.length === 0 ? (
          <div className="flex items-center justify-center py-20 text-slate-400">加载中...</div>
        ) : tasks.length === 0 ? (
          <div className="flex items-center justify-center py-20 text-slate-400">暂无下载任务</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {tasks.map((task) => {
              const cfg = STATUS_CONFIG[task.status];
              return (
                <div
                  key={task.id}
                  className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden"
                >
                  {/* Thumbnail */}
                  <div className="relative aspect-video bg-slate-100">
                    {task.thumbnail_url ? (
                      <img
                        src={task.thumbnail_url}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
                        无缩略图
                      </div>
                    )}
                    {/* Status badge on thumbnail */}
                    <Tag color={cfg.color} className="absolute top-2 left-2 m-0">
                      {cfg.label}
                    </Tag>
                    {/* Play overlay for completed tasks */}
                    {task.status === "COMPLETED" && task.has_file && (
                      <button
                        className="absolute inset-0 flex items-center justify-center bg-black/0 hover:bg-black/30 transition-colors group"
                        onClick={() => setPlayingTaskId(task.id)}
                      >
                        <PlayCircleOutlined className="text-white text-3xl opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                      </button>
                    )}
                  </div>

                  {/* Info */}
                  <div className="p-3">
                    <div
                      className="text-sm font-medium text-slate-900 line-clamp-2 mb-2"
                      title={task.video_title ?? undefined}
                    >
                      {task.video_title || task.video_id}
                    </div>

                    {/* Progress bar */}
                    {task.status !== "COMPLETED" && (
                      <Progress
                        percent={task.status === "PENDING" ? 0 : Math.round(task.progress)}
                        status={task.status === "FAILED" ? "exception" : "active"}
                        size="small"
                        className="mb-2"
                      />
                    )}

                    {/* Meta row */}
                    <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                      <span>{formatFileSize(task.file_size)}</span>
                      <span>{dayjs(task.created_at).fromNow()}</span>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 flex-wrap">
                      {task.status === "COMPLETED" && task.has_file && (
                        <Tooltip title="播放视频">
                          <Button
                            type="text"
                            size="small"
                            icon={<PlayCircleOutlined />}
                            onClick={() => setPlayingTaskId(task.id)}
                          />
                        </Tooltip>
                      )}
                      {task.status === "FAILED" && (
                        <>
                          <Tooltip title="重试下载">
                            <Button
                              type="text"
                              size="small"
                              icon={<RedoOutlined />}
                              loading={retryingIds.has(task.id)}
                              onClick={() => void handleRetry(task.id)}
                            />
                          </Tooltip>
                          <Tooltip title={task.error_message}>
                            <Tag color="error" style={{ cursor: "help", maxWidth: 120 }} className="truncate text-xs">
                              错误
                            </Tag>
                          </Tooltip>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {total > 0 && (
          <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100">
            <span className="text-sm text-slate-400">共 {total} 条</span>
            <Space>
              <Button
                size="small"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                上一页
              </Button>
              <span className="text-sm text-slate-500">
                {page} / {Math.max(1, Math.ceil(total / pageSize))}
              </span>
              <Button
                size="small"
                disabled={page >= Math.ceil(total / pageSize)}
                onClick={() => setPage((p) => p + 1)}
              >
                下一页
              </Button>
              <Select
                size="small"
                value={pageSize}
                onChange={(v) => { setPageSize(v); setPage(1); }}
                options={[
                  { value: 12, label: "12 条/页" },
                  { value: 20, label: "20 条/页" },
                  { value: 40, label: "40 条/页" },
                ]}
                style={{ width: 110 }}
              />
            </Space>
          </div>
        )}
      </div>

      {/* Video Player Modal */}
      <Modal
        open={playingTaskId !== null}
        title={playingTask ? `播放视频 - ${playingTask.video_title ?? playingTask.video_id}` : "播放视频"}
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
