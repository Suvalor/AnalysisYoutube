import {
  Button,
  Card,
  Checkbox,
  Col,
  DatePicker,
  Empty,
  Input,
  Modal,
  Pagination,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import {
  DownloadOutlined,
  EyeOutlined,
  FileImageOutlined,
  MergeOutlined,
  SoundOutlined,
  VideoCameraOutlined,
} from "@ant-design/icons";
import { type Dayjs } from "dayjs";
import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  deleteAssetApi,
  listModelsApi,
  listAssetsApi,
  uploadAssetWithProcessApi,
  type AssetItem,
  type ModelItem,
} from "@/services/libraryApi";
import useModelPreference from "@/hooks/useModelPreference";
import MixConfigModal from "@/components/MixConfigModal";
import {
  listMixTasks,
  downloadMixResult,
  type MixTask,
  type MixTaskStatus,
} from "@/services/downloadApi";

const { Text } = Typography;

type TypeFilter = "all" | "image" | "video" | "audio";
type NormalizedFileType = "image" | "video" | "audio" | "unknown";

/** 防止接口返回异常 file_type 导致渲染分支异常或非预期 DOM */
function normalizeAssetFileType(ft: unknown): NormalizedFileType {
  if (ft === "image" || ft === "video" || ft === "audio") return ft;
  return "unknown";
}
type SortPreset = "time_desc" | "time_asc" | "size_desc" | "size_asc";

function sortPresetToApi(preset: SortPreset): { sort_by: "created_at" | "file_size"; sort_order: "asc" | "desc" } {
  switch (preset) {
    case "time_desc":
      return { sort_by: "created_at", sort_order: "desc" };
    case "time_asc":
      return { sort_by: "created_at", sort_order: "asc" };
    case "size_desc":
      return { sort_by: "file_size", sort_order: "desc" };
    case "size_asc":
      return { sort_by: "file_size", sort_order: "asc" };
    default:
      return { sort_by: "created_at", sort_order: "desc" };
  }
}

function inferType(file: File) {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("audio/")) return "audio";
  return null;
}

function formatBytes(n: number | null | undefined): string {
  if (n == null || n < 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/** 展示与下载统一走 access_url（后端签名 + 自定义域名），避免私有桶直链 file_url 失效 */
function mediaSrc(a: AssetItem): string {
  return (a.file_url || a.access_url || "").trim();
}

export default function AssetLibraryPage() {
  const [items, setItems] = useState<AssetItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [listLoading, setListLoading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [removeWatermark, setRemoveWatermark] = useState(false);
  const [watermarkModels, setWatermarkModels] = useState<ModelItem[]>([]);
  const [loadingWatermarkModels, setLoadingWatermarkModels] = useState(false);
  const [selectedWatermarkModelId, setSelectedWatermarkModelId] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [keyword, setKeyword] = useState("");
  const [searchText, setSearchText] = useState("");
  const [sortPreset, setSortPreset] = useState<SortPreset>("time_desc");
  const [previewAsset, setPreviewAsset] = useState<AssetItem | null>(null);
  const [thumbErrorIds, setThumbErrorIds] = useState<Record<number, boolean>>({});
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [mixModalOpen, setMixModalOpen] = useState(false);
  const [mixTasks, setMixTasks] = useState<MixTask[]>([]);
  const [mixTasksLoading, setMixTasksLoading] = useState(false);
  const [downloadingTaskId, setDownloadingTaskId] = useState<number | null>(null);

  const loadMixTasks = useCallback(async () => {
    setMixTasksLoading(true);
    try {
      const resp = await listMixTasks({ limit: 20 });
      setMixTasks(resp.items ?? []);
    } catch {
      message.error("加载混剪任务列表失败");
    } finally {
      setMixTasksLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMixTasks();
  }, [loadMixTasks]);

  const handleDownloadMixResult = useCallback(async (taskId: number) => {
    setDownloadingTaskId(taskId);
    try {
      await downloadMixResult(taskId);
      message.success("下载已开始");
    } catch {
      message.error("下载混剪结果失败");
    } finally {
      setDownloadingTaskId(null);
    }
  }, []);

  const MIX_TASK_STATUS_MAP: Record<MixTaskStatus, { color: string; label: string }> = {
    PENDING: { color: "default", label: "等待中" },
    PROCESSING: { color: "processing", label: "处理中" },
    COMPLETED: { color: "success", label: "已完成" },
    FAILED: { color: "error", label: "失败" },
  };

  const sortApi = useMemo(() => sortPresetToApi(sortPreset), [sortPreset]);
  const { value: watermarkPrefModelId, setValue: setWatermarkPrefModelId } =
    useModelPreference("watermark_removal");
  /** 与 page 无关的强制刷新（例如上传成功但仍在第 1 页） */
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setListLoading(true);
      try {
        const res = await listAssetsApi({
          page,
          page_size: pageSize,
          file_type: typeFilter === "all" ? undefined : typeFilter,
          date_start: dateRange?.[0]?.format("YYYY-MM-DD"),
          date_end: dateRange?.[1]?.format("YYYY-MM-DD"),
          q: searchText.trim() || undefined,
          sort_by: sortApi.sort_by,
          sort_order: sortApi.sort_order,
        });
        if (!cancelled) {
          setItems(res.items);
          setTotal(res.total);
          setThumbErrorIds({});
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const d =
            err && typeof err === "object" && "response" in err
              ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
              : undefined;
          message.error(typeof d === "string" ? d : "加载素材列表失败");
          setItems([]);
          setTotal(0);
        }
      } finally {
        if (!cancelled) setListLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    page,
    pageSize,
    typeFilter,
    dateRange,
    searchText,
    sortApi.sort_by,
    sortApi.sort_order,
    reloadToken,
  ]);

  useEffect(() => {
    if (!uploadModalOpen || !removeWatermark) return;
    let cancelled = false;
    (async () => {
      setLoadingWatermarkModels(true);
      try {
        const rows = await listModelsApi();
        if (cancelled) return;
        const available = rows.filter((m) => m.library_kind === "image_inpaint" && m.has_api_key);
        setWatermarkModels(available);
        const fallback = available[0]?.id ? String(available[0].id) : "";
        const hit =
          watermarkPrefModelId &&
          available.some((m) => String(m.id) === watermarkPrefModelId)
            ? watermarkPrefModelId
            : fallback;
        setSelectedWatermarkModelId(hit);
        if (hit) setWatermarkPrefModelId(hit);
      } catch {
        if (!cancelled) {
          setWatermarkModels([]);
          message.error("加载去水印模型失败");
        }
      } finally {
        if (!cancelled) setLoadingWatermarkModels(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [removeWatermark, uploadModalOpen, setWatermarkPrefModelId, watermarkPrefModelId]);

  useEffect(() => {
    setPage(1);
    setSelectedIds(new Set());
  }, [typeFilter, dateRange, searchText, sortPreset]);

  const onConfirmUpload = async () => {
    if (!selectedFile) {
      message.warning("请先选择素材文件");
      return;
    }
    const type = inferType(selectedFile);
    if (!type) {
      message.error("仅支持图片、视频、音频文件");
      return;
    }
    try {
      setUploading(true);
      if (removeWatermark && !selectedWatermarkModelId) {
        message.warning("请先选择去水印模型");
        return;
      }
      const uploadRes = await uploadAssetWithProcessApi({
        file: selectedFile,
        remove_watermark: removeWatermark,
        watermark_model_id: removeWatermark ? Number(selectedWatermarkModelId) : undefined,
      });
      if (!uploadRes.access_url && !uploadRes.file_url) {
        message.error("上传未返回可访问地址");
        return;
      }
      setPage(1);
      setReloadToken((t) => t + 1);
      message.success("上传成功");
      setUploadModalOpen(false);
      setSelectedFile(null);
      setRemoveWatermark(false);
    } catch (err: unknown) {
      const d =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "上传失败，请稍后重试");
    } finally {
      setUploading(false);
    }
  };

  const onDelete = async (id: number) => {
    try {
      await deleteAssetApi(id);
      message.success("删除成功");
      const nextTotal = Math.max(0, total - 1);
      const maxPage = Math.max(1, Math.ceil(nextTotal / pageSize));
      if (page > maxPage) setPage(maxPage);
      setReloadToken((t) => t + 1);
    } catch (err: unknown) {
      const d =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "删除失败");
    }
  };

  const onDownload = (asset: AssetItem) => {
    const href = mediaSrc(asset);
    if (!href) {
      message.warning("无可下载地址");
      return;
    }
    const a = document.createElement("a");
    a.href = href;
    a.download = asset.title;
    a.target = "_blank";
    a.rel = "noreferrer";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const markThumbError = (id: number) => {
    setThumbErrorIds((prev) => ({ ...prev, [id]: true }));
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((a) => a.id)));
    }
  };

  const selectedAssets = useMemo(() => items.filter((a) => selectedIds.has(a.id)), [items, selectedIds]);

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-5">
        <Card className="!bg-slate-900/80 !border-slate-800 shadow-2xl">
          <Row gutter={[12, 12]} align="middle">
            <Col xs={24} sm={12} md={6} lg={5}>
              <Button type="primary" block onClick={() => setUploadModalOpen(true)} loading={uploading}>
                上传素材
              </Button>
            </Col>
            <Col xs={24} sm={12} md={6} lg={5}>
              <Select<TypeFilter>
                className="w-full"
                value={typeFilter}
                onChange={setTypeFilter}
                options={[
                  { label: "全部类型", value: "all" },
                  { label: "图片", value: "image" },
                  { label: "视频", value: "video" },
                  { label: "音频", value: "audio" },
                ]}
              />
            </Col>
            <Col xs={24} sm={24} md={12} lg={8}>
              <DatePicker.RangePicker
                className="w-full"
                value={dateRange}
                onChange={(v) => setDateRange((v as [Dayjs, Dayjs] | null) ?? null)}
              />
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Select<SortPreset>
                className="w-full"
                value={sortPreset}
                onChange={setSortPreset}
                options={[
                  { label: "上传时间 · 从新到旧", value: "time_desc" },
                  { label: "上传时间 · 从旧到新", value: "time_asc" },
                  { label: "文件大小 · 从大到小", value: "size_desc" },
                  { label: "文件大小 · 从小到大", value: "size_asc" },
                ]}
              />
            </Col>
            <Col xs={24} sm={24} md={24} lg={24}>
              <Space.Compact className="w-full">
                <Input
                  allowClear
                  className="flex-1 min-w-0"
                  placeholder="按素材名称搜索"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onPressEnter={() => setSearchText(keyword.trim())}
                />
                <Button type="primary" onClick={() => setSearchText(keyword.trim())}>
                  搜索
                </Button>
              </Space.Compact>
            </Col>
          </Row>
        </Card>

        {/* Batch action bar */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 shadow-sm">
            <span className="text-sm text-blue-700 font-medium">
              已选 {selectedIds.size} 项
            </span>
            <Button
              size="small"
              type="primary"
              icon={<MergeOutlined />}
              onClick={() => setMixModalOpen(true)}
            >
              一键 AI 混编
            </Button>
            <Button size="small" onClick={() => setSelectedIds(new Set())}>
              清除选择
            </Button>
          </div>
        )}

        <Spin spinning={listLoading}>
          {items.length === 0 && !listLoading ? (
            <Card className="!bg-slate-900/60 !border-slate-800">
              <Empty description="暂无素材，点击上传或调整筛选条件" />
            </Card>
          ) : (
            <Row gutter={[16, 16]}>
              {/* Select all row */}
              {items.length > 0 && (
                <Col span={24}>
                  <Checkbox
                    checked={selectedIds.size === items.length && items.length > 0}
                    indeterminate={selectedIds.size > 0 && selectedIds.size < items.length}
                    onChange={toggleSelectAll}
                  >
                    全选本页 ({items.length})
                  </Checkbox>
                </Col>
              )}
              {items.map((asset) => {
                const src = mediaSrc(asset);
                const broken = thumbErrorIds[asset.id];
                const ft = normalizeAssetFileType(asset.file_type);
                return (
                  <Col key={asset.id} xs={24} sm={12} lg={8} xl={6}>
                    <Card
                      className="h-full !bg-slate-900/80 !border-slate-800 shadow-xl overflow-hidden transition-all duration-200 hover:!border-slate-600 hover:shadow-2xl hover:-translate-y-0.5"
                      styles={{ body: { padding: 12 } }}
                    >
                      <div className="mb-3 relative group rounded-lg overflow-hidden bg-slate-950/80 min-h-[160px]">
                        <Checkbox
                          checked={selectedIds.has(asset.id)}
                          onChange={() => toggleSelect(asset.id)}
                          className="absolute top-2 left-2 z-10"
                          style={{ accentColor: 'var(--color-primary)' }}
                        />
                        {ft === "image" && (
                          <>
                            {!broken && src ? (
                              <img
                                src={src}
                                alt={asset.title}
                                loading="lazy"
                                decoding="async"
                                className="w-full h-52 object-cover"
                                onError={() => markThumbError(asset.id)}
                              />
                            ) : (
                              <div className="w-full h-52 flex items-center justify-center text-yc-text-secondary text-xs px-3 text-center">
                                图片无法加载。请确认 access_url 有效，或在 OSS/COS/CDN 配置 CORS 允许当前站点。
                              </div>
                            )}
                          </>
                        )}
                        {ft === "video" && (
                          <>
                            {src ? (
                              <video
                                src={src}
                                className="w-full h-52 bg-black object-cover"
                                preload="metadata"
                                muted
                                playsInline
                              />
                            ) : (
                              <div className="w-full h-52 flex items-center justify-center text-yc-text-secondary text-xs px-3 text-center">
                                暂无视频地址
                              </div>
                            )}
                          </>
                        )}
                        {ft === "audio" && (
                          <div className="rounded-lg border border-slate-700 bg-slate-950 p-3 min-h-[120px] flex flex-col justify-center">
                            {src ? (
                              <audio src={src} controls className="w-full" preload="metadata" />
                            ) : (
                              <div className="text-yc-text-secondary text-xs text-center px-2">暂无音频地址</div>
                            )}
                          </div>
                        )}
                        {ft === "unknown" && (
                          <div className="w-full h-52 flex items-center justify-center text-yc-text-secondary text-xs px-3 text-center">
                            无法识别的素材类型，请刷新列表或联系管理员。
                          </div>
                        )}
                        {(ft === "image" || ft === "video") && src && !broken && (
                          <div className="absolute inset-0 bg-black/55 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 pointer-events-none group-hover:pointer-events-auto">
                            <Button size="small" icon={<EyeOutlined />} onClick={() => setPreviewAsset(asset)}>
                              预览
                            </Button>
                            <Button size="small" icon={<DownloadOutlined />} onClick={() => onDownload(asset)}>
                              下载
                            </Button>
                          </div>
                        )}
                      </div>
                      <div className="space-y-1">
                        <h3 className="font-medium text-slate-100 text-sm line-clamp-2 min-h-[2.5rem]" title={asset.title}>
                          {asset.title}
                        </h3>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-yc-text-tertiary">
                          {ft === "image" ? (
                            <FileImageOutlined className="text-cyan-400" aria-hidden />
                          ) : ft === "video" ? (
                            <VideoCameraOutlined className="text-violet-400" aria-hidden />
                          ) : ft === "audio" ? (
                            <SoundOutlined className="text-amber-400" aria-hidden />
                          ) : (
                            <FileImageOutlined className="text-yc-text-secondary" aria-hidden />
                          )}
                          <span>
                            {ft === "image" ? "图片" : ft === "video" ? "视频" : ft === "audio" ? "音频" : "未知类型"}
                          </span>
                          <span>·</span>
                          <span>{dayjs(asset.created_at).format("YYYY-MM-DD HH:mm")}</span>
                          <span>·</span>
                          <span>{formatBytes(asset.file_size)}</span>
                        </div>
                        <div className="flex justify-end pt-2">
                          <Popconfirm
                            title="确认删除"
                            description="删除后无法恢复，确认继续？"
                            onConfirm={() => void onDelete(asset.id)}
                            okText="确认"
                            cancelText="取消"
                          >
                            <Button danger size="small">删除</Button>
                          </Popconfirm>
                        </div>
                      </div>
                    </Card>
                  </Col>
                );
              })}
            </Row>
          )}
        </Spin>

        {total > 0 ? (
          <div className="flex justify-end pt-2">
            <Pagination
              current={page}
              pageSize={pageSize}
              total={total}
              showSizeChanger
              showTotal={(t) => `共 ${t} 条`}
              pageSizeOptions={[12, 20, 40, 60]}
              onChange={(p, ps) => {
                setPage(p);
                setPageSize(ps);
                setSelectedIds(new Set());
              }}
            />
          </div>
        ) : null}
      </div>

      {/* 混剪任务列表 */}
      <Card
        title="混剪任务"
        size="small"
        style={{ marginTop: 16, maxWidth: 1280, marginLeft: "auto", marginRight: "auto" }}
        extra={
          <Button size="small" onClick={loadMixTasks} loading={mixTasksLoading}>
            刷新
          </Button>
        }
      >
        {mixTasks.length === 0 ? (
          <Empty description="暂无混剪任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {mixTasks.map((task) => {
              const statusInfo = MIX_TASK_STATUS_MAP[task.status];
              return (
                <div
                  key={task.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "8px 12px",
                    borderRadius: 6,
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <Space>
                    <span style={{ color: "var(--color-text-secondary)" }}>#{task.id}</span>
                    <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
                    <span style={{ color: "var(--color-text-tertiary)", fontSize: 12 }}>
                      {new Date(task.created_at).toLocaleString()}
                    </span>
                  </Space>
                  {task.status === "COMPLETED" && (
                    <Button
                      type="link"
                      size="small"
                      loading={downloadingTaskId === task.id}
                      onClick={() => handleDownloadMixResult(task.id)}
                    >
                      下载混剪结果
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <MixConfigModal
        open={mixModalOpen}
        onClose={() => setMixModalOpen(false)}
        selectedAssets={selectedAssets}
      />

      <Modal
        title="上传素材"
        open={uploadModalOpen}
        onCancel={() => {
          if (uploading) return;
          setUploadModalOpen(false);
          setSelectedFile(null);
          setRemoveWatermark(false);
          setSelectedWatermarkModelId("");
        }}
        onOk={() => void onConfirmUpload()}
        confirmLoading={uploading}
        okText="确定上传"
        cancelText="取消"
      >
        <div className="space-y-4">
          <Upload.Dragger
            maxCount={1}
            beforeUpload={(file) => {
              setSelectedFile(file);
              return false;
            }}
            fileList={
              selectedFile
                ? [
                    {
                      uid: "-1",
                      name: selectedFile.name,
                      status: "done",
                    },
                  ]
                : []
            }
            onRemove={() => {
              setSelectedFile(null);
            }}
          >
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">支持图片、视频、音频。上传前可选择 AI 去水印（仅对图片/视频尝试）。</p>
          </Upload.Dragger>
          <Checkbox checked={removeWatermark} onChange={(e) => setRemoveWatermark(e.target.checked)}>
            一键去水印（AI 智能处理）
          </Checkbox>
          {removeWatermark ? (
            <Select
              showSearch
              placeholder={loadingWatermarkModels ? "正在加载模型..." : "请选择去水印模型"}
              loading={loadingWatermarkModels}
              value={selectedWatermarkModelId || undefined}
              onChange={(v) => {
                setSelectedWatermarkModelId(v);
                setWatermarkPrefModelId(v);
              }}
              options={watermarkModels.map((m) => ({ value: String(m.id), label: m.name }))}
              notFoundContent={loadingWatermarkModels ? "加载中..." : "暂无可用图像去水印模型"}
            />
          ) : null}
          {uploading ? <Text style={{ color: "var(--color-text-tertiary)" }}>上传处理中，请稍候...</Text> : null}
        </div>
      </Modal>

      <Modal
        open={Boolean(previewAsset)}
        footer={null}
        onCancel={() => setPreviewAsset(null)}
        width="85vw"
        style={{ top: 20 }}
      >
        <div className="bg-black rounded-lg min-h-[70vh] flex items-center justify-center">
          {previewAsset && normalizeAssetFileType(previewAsset.file_type) === "image" && (
            <img
              src={mediaSrc(previewAsset)}
              alt={previewAsset.title}
              loading="lazy"
              decoding="async"
              className="max-h-[78vh] max-w-full object-contain"
            />
          )}
          {previewAsset && normalizeAssetFileType(previewAsset.file_type) === "video" && (
            <video src={mediaSrc(previewAsset)} controls autoPlay className="max-h-[78vh] max-w-full" />
          )}
          {previewAsset && normalizeAssetFileType(previewAsset.file_type) === "audio" && (
            <div className="w-full max-w-lg p-6">
              <audio src={mediaSrc(previewAsset)} controls className="w-full" preload="metadata" />
            </div>
          )}
          {previewAsset && normalizeAssetFileType(previewAsset.file_type) === "unknown" && (
            <p className="text-yc-text-tertiary text-sm px-4">该素材类型不支持预览。</p>
          )}
        </div>
      </Modal>
    </div>
  );
}
