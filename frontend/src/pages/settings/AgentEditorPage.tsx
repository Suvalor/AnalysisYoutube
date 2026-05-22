import { ArrowLeftOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import { Button, Form, Input, message, Modal, Spin } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { getPromptApi, updatePromptApi } from "@/services/libraryApi";

type AgentFormValues = {
  title: string;
  content: string;
};

type AgentEditorPageProps = {
  /** 来自标签页 store 的 promptId */
  promptId?: number;
};

/** 智能体编辑页面：编辑系统提示词规则，保存后立即生效 */
export default function AgentEditorPage({ promptId: promptIdFromTab }: AgentEditorPageProps) {
  const { t } = useTranslation("settings");
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm<AgentFormValues>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const initialRef = useRef<AgentFormValues | null>(null);
  const [invalidId, setInvalidId] = useState(false);

  /** 解析 promptId：优先 Tab 传入 > 路由动态段 */
  const promptId = useMemo(() => {
    if (typeof promptIdFromTab === "number" && Number.isFinite(promptIdFromTab) && promptIdFromTab > 0) {
      return promptIdFromTab;
    }
    const raw = (id || "").trim();
    if (!raw) return 0;
    const num = Number(raw);
    return Number.isFinite(num) && num > 0 ? num : 0;
  }, [id, promptIdFromTab]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!promptId) {
        setInvalidId(true);
        return;
      }
      setInvalidId(false);
      setLoading(true);
      try {
        const row = await getPromptApi(promptId);
        if (!mounted) return;
        const initial = { title: row.title, content: row.content };
        initialRef.current = initial;
        form.setFieldsValue(initial);
      } catch (e: unknown) {
        if (!mounted) return;
        const err = e as { response?: { data?: { detail?: string } }; message?: string };
        message.error(err?.response?.data?.detail ?? err?.message ?? t("agent.loadFailed"));
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [form, navigate, promptId, t]);

  /** 检查表单是否有未保存修改 */
  const isDirty = () => {
    const init = initialRef.current;
    if (!init) return false;
    const current = form.getFieldsValue();
    return current.title !== init.title || current.content !== init.content;
  };

  /** 返回智能体管理列表 */
  const goBack = () => {
    navigate("/config-center?tab=prompts");
  };

  /** 处理返回按钮点击，有未保存修改时弹确认 */
  const handleBack = () => {
    if (!isDirty()) {
      goBack();
      return;
    }
    Modal.confirm({
      title: t("agent.confirmBackTitle"),
      icon: <ExclamationCircleOutlined />,
      content: t("agent.unsavedBackDesc"),
      okText: t("agent.backButton"),
      cancelText: t("agent.cancel"),
      onOk: goBack,
    });
  };

  /** 保存智能体编辑 */
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = {
        title: values.title.trim(),
        content: values.content.trim(),
      };
      const row = await updatePromptApi(promptId, payload);
      const latest = { title: row.title, content: row.content };
      initialRef.current = latest;
      form.setFieldsValue(latest);
      message.success(t("agent.saveSuccess"));
    } catch (e: unknown) {
      if ((e as { errorFields?: unknown })?.errorFields) return;
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      message.error(err?.response?.data?.detail ?? err?.message ?? t("agent.saveFailed"));
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

  if (invalidId) {
    return (
      <div className="p-6 text-center text-yc-text-secondary">
        <p>{t("agent.invalidIdDesc")}</p>
        <Button type="primary" onClick={goBack}>
          {t("agent.backToAgentList")}
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-yc-bg-layout p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-4 flex items-center gap-2">
          <button
            className="inline-flex items-center gap-1 text-yc-text-secondary hover:text-yc-primary transition-colors"
            onClick={handleBack}
          >
            <ArrowLeftOutlined /> {t("agent.backButton")}
          </button>
        </div>
        <div className="bg-yc-bg-card border border-yc-border rounded-lg p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-yc-text-primary">{t("agent.title")}</h2>
              <p className="text-yc-text-secondary mt-1">{t("agent.description")}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={handleBack}>{t("agent.backButton")}</Button>
              <Button type="primary" loading={saving} onClick={handleSave}>
                {t("agent.save")}
              </Button>
            </div>
          </div>

          <Form form={form} layout="vertical">
            <Form.Item name="title" label={t("agent.nameLabel")} rules={[{ required: true, message: t("agent.nameRequired") }]}>
              <Input placeholder={t("agent.namePlaceholder")} />
            </Form.Item>
            <Form.Item
              name="content"
              label={t("agent.systemPromptLabel")}
              rules={[{ required: true, message: t("agent.systemPromptRequired") }]}
            >
              <Input.TextArea
                placeholder={t("agent.systemPromptPlaceholder")}
                autoSize={{ minRows: 20, maxRows: 36 }}
              />
            </Form.Item>
          </Form>

          <div className="mt-4 flex gap-2">
            <Button onClick={handleBack}>{t("agent.backButton")}</Button>
            <Button type="primary" loading={saving} onClick={handleSave}>
              {t("agent.save")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
