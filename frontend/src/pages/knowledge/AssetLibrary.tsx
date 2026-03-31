import { Button, Card, Input, Progress, message } from "antd";
import { type ChangeEvent, useEffect, useRef, useState } from "react";
import { createAssetApi, deleteAssetApi, listAssetsApi, type AssetItem } from "@/services/libraryApi";
import { useOssUpload } from "@/hooks/useOssUpload";

function inferType(file: File) {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("audio/")) return "audio";
  return null;
}

export default function AssetLibraryPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [title, setTitle] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { uploading, progress, uploadFile } = useOssUpload();

  const loadAssets = async () => {
    const data = await listAssetsApi();
    setAssets(data);
  };

  useEffect(() => {
    void loadAssets();
  }, []);

  const onPickFile = () => fileInputRef.current?.click();

  const onFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const type = inferType(file);
    if (!type) {
      message.error("仅支持图片、视频、音频文件");
      return;
    }
    try {
      const uploadRes = await uploadFile(file);
      const finalTitle = (title || file.name).trim();
      await createAssetApi({
        title: finalTitle,
        file_type: type,
        file_url: uploadRes.url,
      });
      setTitle("");
      await loadAssets();
      message.success("上传并保存成功");
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.message || "上传失败");
    } finally {
      e.target.value = "";
    }
  };

  const onDelete = async (id: number) => {
    await deleteAssetApi(id);
    setAssets((prev) => prev.filter((x) => x.id !== id));
    message.success("删除成功");
  };

  const onCopy = async (url: string) => {
    await navigator.clipboard.writeText(url);
    message.success("链接已复制");
  };

  return (
    <div className="p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-5">
        <Card className="!bg-slate-900/80 !border-slate-800 shadow-2xl">
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            <Input
              placeholder="可选：上传后在素材库显示的标题（默认文件名）"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Button type="primary" onClick={onPickFile} loading={uploading}>
              上传素材
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,video/*,audio/*"
              className="hidden"
              onChange={onFileChange}
            />
          </div>
          {uploading && (
            <div className="mt-4">
              <Progress percent={progress} />
            </div>
          )}
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {assets.map((asset) => (
            <Card key={asset.id} className="!bg-slate-900/80 !border-slate-800 shadow-xl">
              <div className="mb-3">
                {asset.file_type === "image" && (
                  <img src={asset.file_url} alt={asset.title} className="w-full h-52 rounded-lg object-cover" />
                )}
                {asset.file_type === "video" && (
                  <video src={asset.file_url} controls className="w-full h-52 rounded-lg bg-black" />
                )}
                {asset.file_type === "audio" && (
                  <div className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                    <audio src={asset.file_url} controls className="w-full" />
                  </div>
                )}
              </div>
              <h3 className="font-medium mb-2">{asset.title}</h3>
              <div className="flex gap-2">
                <Button size="small" onClick={() => onCopy(asset.file_url)}>
                  复制链接
                </Button>
                <Button danger size="small" onClick={() => onDelete(asset.id)}>
                  删除
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

