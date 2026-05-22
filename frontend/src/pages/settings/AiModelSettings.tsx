import { useEffect, useState } from "react";
import { Alert, Button, Form, Input, message, Spin } from "antd";
import { useTranslation } from "react-i18next";
import { getUserSettingsApi, updateUserSettingsApi } from "@/services/userApi";

const { TextArea } = Input;

type FormValues = {
  ai_api_base_url?: string;
  ai_api_key?: string;
  ai_models_json?: string;
  ai_prompt_config_json?: string;
};

/** AI 模型与 API 配置页面 */
export default function AiModelSettings() {
  const { t } = useTranslation("settings");
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
          e?.response?.data?.detail ?? e?.message ?? t("aiModel.loadFailed");
        setError(String(msg));
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [form, t]);

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
      message.success(t("aiModel.saveSuccess"));
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ?? e?.message ?? t("aiModel.saveFailed");
      setError(String(msg));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-yc-bg-layout">
        <Spin />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-yc-bg-layout p-4 md:p-8">
      <div className="max-w-3xl mx-auto bg-yc-bg-card border border-yc-border rounded-lg p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-yc-text-primary mb-1">{t("aiModel.title")}</h2>
        <p className="text-sm text-yc-text-secondary mb-6">
          {t("aiModel.subtitle")}
        </p>

        {error && (
          <Alert type="error" message={error} showIcon className="mb-4" />
        )}

        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item
            label={t("aiModel.baseUrl")}
            name="ai_api_base_url"
            rules={[{ max: 512, message: t("aiModel.tooLong") }]}
          >
            <Input placeholder="https://ark.cn-beijing.volcesapi.com/api/v3" allowClear />
          </Form.Item>

          <Form.Item label={t("aiModel.apiKey")} name="ai_api_key">
            <Input.Password
              placeholder={hasKey ? t("aiModel.keyHasSavedPlaceholder") : t("aiModel.keyNewPlaceholder")}
              autoComplete="new-password"
            />
          </Form.Item>

          <Form.Item
            label={t("aiModel.modelsJson")}
            name="ai_models_json"
            rules={[{ max: 100_000, message: t("aiModel.contentTooLong") }]}
          >
            <TextArea rows={8} placeholder={t("aiModel.modelJsonPlaceholder")} />
          </Form.Item>

          <Form.Item
            label={t("aiModel.promptConfigJson")}
            name="ai_prompt_config_json"
            rules={[{ max: 100_000, message: t("aiModel.contentTooLong") }]}
          >
            <TextArea rows={12} placeholder={t("aiModel.promptJsonPlaceholder")} />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>
              {t("aiModel.saveButton")}
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}