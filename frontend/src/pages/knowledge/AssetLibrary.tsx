import {
  Button,
  Card,
  Checkbox,
  DatePicker,
  Modal,
  Select,
  Typography,
  Upload,
  message,
} from "antd";
import { DownloadOutlined, EyeOutlined, FileImageOutlined, VideoCameraOutlined } from "@ant-design/icons";
import { type Dayjs } from "dayjs";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import {
  createAssetApi,
  deleteAssetApi,
  listAssetsApi,
  uploadAssetWithProcessApi,
  type AssetItem,
} from "@/services/libraryApi";

const { Text } = Typography;
const { RangePicker } = DatePicker;
const { Dragger } = Upload;

const MOCK_ASSETS: AssetItem[] = [
  {
    id: -1,
    user_id: 0,
    title: "示例图片素材",
    file_type: "image",
    file_url: "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1600&q=80",
    created_at: dayjs().subtract(1, "day").toISOString(),
    updated_at: dayjs().subtract(1, "day").toISOString(),
  },
  {
    id: -2,
    user_id: 0,
    title: "示例视频素材",
    file_type: "video",
    file_url: "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    created_at: dayjs().subtract(3, "day").toISOString(),
    updated_at: dayjs().subtract(3, "day").toISOString(),
  },
];

function inferType(file: File) {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("audio/")) return "audio";
  return null;
}

export default function AssetLibraryPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [removeWatermark, setRemoveWatermark] = useState(false);
  const [typeFilter, setTypeFilter] = useState<"all" | "image" | "video">("all");
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [previewAsset, setPreviewAsset] = useState<AssetItem | null>(null);

  const loadAssets = async () => {
    const data = await listAssetsApi();
    setAssets(data);
  };

  useEffect(() => {
    void loadAssets();
  }, []);

  const displayAssets = useMemo(() => (assets.length > 0 ? assets : MOCK_ASSETS), [assets]);

  const filteredAssets = useMemo(() => {
    return displayAssets.filter((asset) => {
      if (typeFilter !== "all" && asset.file_type !== typeFilter) return false;
      if (dateRange) {
        const createdAt = dayjs(asset.created_at);
        if (createdAt.isBefore(dateRange[0], "day") || createdAt.isAfter(dateRange[1], "day")) {
          return false;
        }
      }
      return true;
    });
  }, [displayAssets, typeFilter, dateRange]);

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
      const uploadRes = await uploadAssetWithProcessApi({
        file: selectedFile,
        remove_watermark: removeWatermark,
      });
      if (uploadRes.file_url) {
        await createAssetApi({
          title: uploadRes.title || selectedFile.name,
          file_type: uploadRes.file_type || type,
          file_url: uploadRes.file_url,
        });
      }
      await loadAssets();
      message.success("上传成功");
      setUploadModalOpen(false);
      setSelectedFile(null);
      setRemoveWatermark(false);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.message || "上传失败，请稍后重试");
    } finally {
      setUploading(false);
    }
  };

  const onDelete = async (id: number) => {
    await deleteAssetApi(id);
    setAssets((prev) => prev.filter((x) => x.id !== id));
    message.success("删除成功");
  };

  const onDownload = (asset: AssetItem) => {
    const a = document.createElement("a");
    a.href = asset.file_url;
    a.download = asset.title;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-5">
        <Card className="!bg-slate-900/80 !border-slate-800 shadow-2xl">
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            <Button type="primary" onClick={() => setUploadModalOpen(true)} loading={uploading}>
              上传素材
            </Button>
            <div className="w-full md:w-44">
              <Select
                className="w-full"
                value={typeFilter}
                onChange={setTypeFilter}
                options={[
                  { label: "全部", value: "all" },
                  { label: "图片", value: "image" },
                  { label: "视频", value: "video" },
                ]}
              />
            </div>
            <RangePicker
              className="w-full md:w-[320px]"
              value={dateRange}
              onChange={(v) => setDateRange((v as [Dayjs, Dayjs] | null) ?? null)}
            />
          </div>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAssets.map((asset) => (
            <Card key={asset.id} className="!bg-slate-900/80 !border-slate-800 shadow-xl overflow-hidden">
              <div className="mb-3 relative group">
                {asset.file_type === "image" && (
                  <img src={asset.file_url} alt={asset.title} className="w-full h-52 rounded-lg object-cover" />
                )}
                {asset.file_type === "video" && (
                  <video src={asset.file_url} className="w-full h-52 rounded-lg bg-black object-cover" />
                )}
                {asset.file_type === "audio" && (
                  <div className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                    <audio src={asset.file_url} controls className="w-full" />
                  </div>
                )}
                {(asset.file_type === "image" || asset.file_type === "video") && (
                  <div className="absolute inset-0 bg-black/50 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <Button
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => setPreviewAsset(asset)}
                    >
                      预览
                    </Button>
                    <Button size="small" icon={<DownloadOutlined />} onClick={() => onDownload(asset)}>
                      下载
                    </Button>
                  </div>
                )}
              </div>
              <h3 className="font-medium mb-1 line-clamp-1">{asset.title}</h3>
              <div className="text-xs text-slate-400 mb-2 flex items-center gap-2">
                {asset.file_type === "image" ? (
                  <FileImageOutlined className="text-cyan-400" />
                ) : asset.file_type === "video" ? (
                  <VideoCameraOutlined className="text-violet-400" />
                ) : null}
                <Text style={{ color: "#94a3b8" }}>{dayjs(asset.created_at).format("YYYY-MM-DD HH:mm")}</Text>
              </div>
              <div className="flex gap-2 justify-end">
                <Button danger size="small" onClick={() => onDelete(asset.id)}>
                  删除
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>

      <Modal
        title="上传素材"
        open={uploadModalOpen}
        onCancel={() => {
          if (uploading) return;
          setUploadModalOpen(false);
          setSelectedFile(null);
          setRemoveWatermark(false);
        }}
        onOk={onConfirmUpload}
        confirmLoading={uploading}
        okText="确定上传"
        cancelText="取消"
      >
        <div className="space-y-4">
          <Dragger
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
            <p className="ant-upload-hint">支持图片、视频文件。上传前可选择 AI 去水印处理。</p>
          </Dragger>
          <Checkbox checked={removeWatermark} onChange={(e) => setRemoveWatermark(e.target.checked)}>
            一键去水印（AI 智能处理）
          </Checkbox>
          {uploading && <Text style={{ color: "#94a3b8" }}>上传处理中，请稍候...</Text>}
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
          {previewAsset?.file_type === "image" && (
            <img src={previewAsset.file_url} alt={previewAsset.title} className="max-h-[78vh] max-w-full object-contain" />
          )}
          {previewAsset?.file_type === "video" && (
            <video src={previewAsset.file_url} controls autoPlay className="max-h-[78vh] max-w-full" />
          )}
        </div>
      </Modal>
    </div>
  );
}

