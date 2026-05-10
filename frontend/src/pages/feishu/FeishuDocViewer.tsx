import { Alert, Segmented, Spin } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { getFeishuDocApi } from "@/services/feishuDocsApi";

type PreviewSource = "original" | "archive";

type FeishuDocViewerProps = {
  /** 来自标签页 store（主路径：通配符路由下 useParams 无 :id） */
  docId?: number;
};

/**
 * 解析要请求后端的文档主键 id。
 * 优先级：Tab 传入 > 路由动态段 :id > 当前 path /feishu/view/<数字>
 */
function resolveDocId(docIdFromTab: number | undefined, params: { id?: string }, pathname: string): number {
  if (typeof docIdFromTab === "number" && Number.isFinite(docIdFromTab) && docIdFromTab > 0) {
    return docIdFromTab;
  }
  const fromParam = params.id != null && params.id !== "" ? Number(params.id) : NaN;
  if (Number.isFinite(fromParam) && fromParam > 0) {
    return fromParam;
  }
  const m = pathname.match(/^\/feishu\/view\/(\d+)$/);
  if (m) {
    const n = Number(m[1]);
    if (Number.isFinite(n) && n > 0) {
      return n;
    }
  }
  return NaN;
}

export default function FeishuDocViewer({ docId: docIdFromTab }: FeishuDocViewerProps) {
  const params = useParams();
  const location = useLocation();
  const docId = useMemo(
    () => resolveDocId(docIdFromTab, params, location.pathname),
    [docIdFromTab, params, location.pathname]
  );

  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState<string | null>(null);
  const [title, setTitle] = useState<string>("");
  const [archiveStatus, setArchiveStatus] = useState<string>("UNARCHIVED");
  const [archiveFileUrl, setArchiveFileUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewSource, setPreviewSource] = useState<PreviewSource>("original");

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
        setArchiveStatus(doc.archive_status ?? "UNARCHIVED");
        setArchiveFileUrl(doc.archive_file_url ?? null);
        if ((doc.archive_status ?? "") === "SUCCESS" && doc.archive_file_url) {
          setPreviewSource("original");
        }
      } catch (e: unknown) {
        if (!mounted) return;
        const err = e as { response?: { data?: { detail?: string } } };
        setError(err?.response?.data?.detail ?? "加载文档失败");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [docId]);

  const showArchiveToggle = archiveStatus === "SUCCESS" && Boolean(archiveFileUrl?.trim());
  const iframeSrc = useMemo(() => {
    if (showArchiveToggle && previewSource === "archive") {
      return archiveFileUrl!.trim();
    }
    return url;
  }, [showArchiveToggle, previewSource, archiveFileUrl, url]);

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

  if (!iframeSrc) {
    return (
      <div className="p-4">
        <Alert type="warning" showIcon message="文档链接为空" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-yc-border bg-yc-bg-card text-sm text-yc-text-primary flex flex-wrap items-center gap-3 min-h-[44px]">
        <span className="truncate flex-1 min-w-0">{title || "飞书云文档"}</span>
        {showArchiveToggle ? (
          <Segmented<PreviewSource>
            size="small"
            value={previewSource}
            onChange={setPreviewSource}
            options={[
              { label: "原链接预览", value: "original" },
              { label: "离线备份预览", value: "archive" },
            ]}
          />
        ) : null}
      </div>
      <div className="flex-1 bg-yc-bg-secondary">
        <iframe
          title={showArchiveToggle && previewSource === "archive" ? "离线归档预览" : "飞书原链预览"}
          src={iframeSrc}
          className="w-full h-[calc(100vh-120px)] border-0"
          sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          allow="fullscreen"
        />
      </div>
    </div>
  );
}
