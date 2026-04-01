import { useEffect, useState } from "react";
import { Alert, Button, Form, Input, message, Spin } from "antd";
import { getUserSettingsApi, updateUserSettingsApi } from "@/services/userApi";

const { TextArea } = Input;

const MODEL_JSON_PLACEHOLDER = `示例（JSON 数组）：
[
  { "value": "gpt-4o", "label": "GPT-4o" },
  { "value": "my-endpoint-id", "label": "火山/自建模型 ID" }
]`;

const PROMPT_JSON_PLACEHOLDER = `示例（JSON 对象，value 需与创作页选项一致）：
{
  "prompts": [
    { "value": "short-video", "label": "短视频脚本", "template": "你是专业编剧，请输出带分镜的脚本…" },
    { "value": "talking-head", "label": "口播稿", "template": "单人出镜、信息密集…" }
  ],
  "styles": [
    { "value": "humor", "label": "幽默搞笑", "hint": "轻松诙谐" },
    { "value": "professional", "label": "专业权威", "hint": "数据与逻辑清晰" }
  ]
}`;

type FormValues = {
  ai_api_base_url?: string;
  ai_api_key?: string;
  ai_models_json?: string;
  ai_prompt_config_json?: string;
};

export default function AiModelSettings() {
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasKey, setHasKey] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await getUserSettingsApi();
        if (!mounted) return;
        setHasKey(Boolean(data.has_ai_api_key));
        form.setFieldsValue({
          ai_api_base_url: data.ai_api_base_url ?? "",
          ai_models_json: data.ai_models_json ?? "",
          ai_prompt_config_json: data.ai_prompt_config_json ?? "",
          ai_api_key: "",
        });
      } catch (e: any) {
        if (!mounted) return;
        const msg =
          e?.response?.data?.detail ?? e?.message ?? "加载模型设置失败，请稍后重试";
        setError(String(msg));
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [form]);

  const onFinish = async (values: FormValues) => {
    setSaving(true);
    setError(null);
    try {
      const payload: Record<string, string | null | undefined> = {
        ai_api_base_url: values.ai_api_base_url?.trim() || null,
        ai_models_json: values.ai_models_json?.trim() || null,
        ai_prompt_config_json: values.ai_prompt_config_json?.trim() || null,
      };
      const keyTrim = values.ai_api_key?.trim();
      if (keyTrim) {
        payload.ai_api_key = keyTrim;
      }
      const data = await updateUserSettingsApi(payload as any);
      setHasKey(Boolean(data.has_ai_api_key));
      form.setFieldValue("ai_api_key", "");
      message.success("模型设置已保存");
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ?? e?.message ?? "保存失败，请检查 JSON 格式与网络";
      setError(String(msg));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#F8F9FA]">
        <Spin />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-[#F8F9FA] p-4 md:p-8">
      <div className="max-w-3xl mx-auto bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 mb-1">模型与 API 配置</h2>
        <p className="text-sm text-slate-600 mb-6">
          API Key 仅通过 HTTPS 提交，服务端加密后写入数据库；列表页永不回显明文。留空密钥表示不修改已保存的密钥。
        </p>

        {error && (
          <Alert type="error" message={error} showIcon className="mb-4" />
        )}

        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item
            label="API 根地址（OpenAI 兼容）"
            name="ai_api_base_url"
            rules={[{ max: 512, message: "过长" }]}
          >
            <Input placeholder="例如：https://ark.cn-beijing.volcesapi.com/api/v3" allowClear />
          </Form.Item>

          <Form.Item label="API Key" name="ai_api_key">
            <Input.Password
              placeholder={hasKey ? "已保存密钥，留空不修改；填写则覆盖" : "填写后保存即加密存储"}
              autoComplete="new-password"
            />
          </Form.Item>

          <Form.Item
            label="支持的模型（JSON）"
            name="ai_models_json"
            rules={[{ max: 100_000, message: "内容过长" }]}
          >
            <TextArea rows={8} placeholder={MODEL_JSON_PLACEHOLDER} />
          </Form.Item>

          <Form.Item
            label="提示词与风格（JSON）"
            name="ai_prompt_config_json"
            rules={[{ max: 100_000, message: "内容过长" }]}
          >
            <TextArea rows={12} placeholder={PROMPT_JSON_PLACEHOLDER} />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>
              保存设置
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}
