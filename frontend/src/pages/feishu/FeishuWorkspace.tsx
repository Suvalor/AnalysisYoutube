import { useEffect, useState } from "react";
import { Alert, Button, Input, message, Spin } from "antd";
import { getUserSettingsApi, updateUserSettingsApi } from "@/services/userApi";

export default function FeishuWorkspace() {
  const [feishuUrl, setFeishuUrl] = useState("");
  const [savedUrl, setSavedUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await getUserSettingsApi();
        if (!mounted) return;
        setSavedUrl(data.feishu_doc_url);
        setFeishuUrl(data.feishu_doc_url ?? "");
      } catch (e: any) {
        if (!mounted) return;
        const msg =
          e?.response?.data?.detail ??
          e?.message ??
          "加载飞书云文档设置失败，请稍后重试";
        setError(String(msg));
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const trimmed = feishuUrl.trim() || null;
      const data = await updateUserSettingsApi({ feishu_doc_url: trimmed });
      setSavedUrl(data.feishu_doc_url);
      setFeishuUrl(data.feishu_doc_url ?? "");
      message.success("飞书链接已保存");
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ??
        e?.message ??
        "保存飞书云文档链接失败，请稍后重试";
      setError(String(msg));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Spin />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-slate-200 bg-white px-4 py-3 flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
        <div className="flex-1">
          <Input
            placeholder="请输入飞书云文档的分享链接"
            value={feishuUrl}
            onChange={(e) => setFeishuUrl(e.target.value)}
          />
        </div>
        <Button type="primary" onClick={handleSave} loading={saving}>
          保存链接
        </Button>
      </div>

      {error && (
        <div className="px-4 pt-3">
          <Alert type="error" message={error} showIcon />
        </div>
      )}

      <div className="flex-1 bg-slate-50">
        {savedUrl ? (
          <iframe
            src={savedUrl}
            className="w-full h-[calc(100vh-100px)] border-0"
            allow="fullscreen"
          />
        ) : (
          <div className="h-full flex items-center justify-center px-6">
            <div className="max-w-xl text-center text-slate-600 space-y-3">
              <h2 className="text-lg font-semibold text-slate-800">
                配置你的飞书云文档工作台
              </h2>
              <p>
                请输入飞书云文档的分享链接（请确保文档权限已开启「获得链接的人可阅读/编辑」）以嵌入工作台。
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

