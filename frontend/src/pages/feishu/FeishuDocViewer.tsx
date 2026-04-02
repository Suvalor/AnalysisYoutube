import { Alert, Spin } from "antd";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getFeishuDocApi } from "@/services/feishuDocsApi";

export default function FeishuDocViewer() {
  const params = useParams();
  const docId = Number(params.id);
  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState<string | null>(null);
  const [title, setTitle] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!Number.isFinite(docId) || docId <= 0) {
        setError("文档 ID 不合法");
        setLoading(false);
        return;
      }
      try {
        const doc = await getFeishuDocApi(docId);
        if (!mounted) return;
        setTitle(doc.title);
        setUrl(doc.url);
      } catch (e: any) {
        if (!mounted) return;
        setError(e?.response?.data?.detail ?? "加载文档失败");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [docId]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Spin />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <Alert type="error" showIcon message={error} />
      </div>
    );
  }

  if (!url) {
    return (
      <div className="p-4">
        <Alert type="warning" showIcon message="文档链接为空" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-slate-200 bg-white text-sm text-slate-700 truncate">
        {title || "飞书云文档"}
      </div>
      <div className="flex-1 bg-slate-50">
        <iframe src={url} className="w-full h-[calc(100vh-120px)] border-0" allow="fullscreen" />
      </div>
    </div>
  );
}

