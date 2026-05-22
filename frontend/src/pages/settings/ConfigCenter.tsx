import { MinusCircleOutlined, PlusOutlined } from "@ant-design/icons";
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Radio,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/store/authStore";
import { hasRole } from "@/config/features";
import { UserRole } from "@/types/auth";
import {
  createModelApi,
  createPromptApi,
  createStyleApi,
  deleteModelApi,
  deletePromptApi,
  deleteStyleApi,
  listModelsApi,
  listPromptsApi,
  listStylesApi,
  updateModelApi,
  updatePromptApi,
  updateStyleApi,
  type ModelItem,
  type PromptItem,
  type StyleItem,
} from "@/services/libraryApi";
import {
  deleteIntegrationSettingsApi,
  getIntegrationSettingsApi,
  testStorageIntegrationApi,
  testYoutubeIntegrationApi,
  updateIntegrationSettingsApi,
  validateStorageCustomDomainApi,
  type IntegrationSettingsRead,
  type IntegrationSettingsUpdatePayload,
} from "@/services/userApi";

const SECRET_MASK = "********";

/** 与后端 is_secret_placeholder 对齐：勿把占位符当新密钥提交 */
function looksLikeMaskedSecret(s: string | undefined): boolean {
  const t = (s ?? "").trim();
  if (!t) return false;
  if (t === SECRET_MASK) return true;
  return /^[*•.·]+$/.test(t) && t.length >= 4;
}

function normStorageProviderRadio(raw: string | undefined): "ALIYUN" | "TENCENT" {
  const u = (raw ?? "").trim().toUpperCase();
  if (u === "ALIYUN" || u === "OSS" || u === "ALIYUN_OSS") return "ALIYUN";
  return "TENCENT";
}

type EditorMode = "create" | "edit";
type ActiveTabKey = "models" | "prompts" | "styles" | "integration";

type ModelFormValues = {
  name: string;
  library_kind?: string;
  api_base_url: string;
  api_key?: string;
  protocol?: string;
  supported_models?: Array<{ label: string; value: string }>;
};

type TextFormValues = {
  title: string;
  content: string;
};

type StorageFormValues = {
  active_storage_provider: "ALIYUN" | "TENCENT";
  aliyun_access_key_id: string;
  aliyun_access_key_secret: string;
  aliyun_role_arn: string;
  aliyun_region_id: string;
  aliyun_oss_bucket_name: string;
  aliyun_oss_endpoint: string;
  aliyun_custom_domain: string;
  tencent_cos_secret_id: string;
  tencent_cos_secret_key: string;
  tencent_cos_region: string;
  tencent_cos_bucket: string;
  tencent_custom_domain: string;
};

type YoutubeFormValues = {
  youtube_api_key: string;
  google_oauth_client_id: string;
  google_oauth_client_secret: string;
  google_oauth_redirect_uri: string;
};

type CVFormValues = {
  volc_cv_access_key_id: string;
  volc_cv_secret_access_key: string;
  volc_cv_region: string;
  volc_cv_host: string;
  volc_cv_inpaint_req_key: string;
  watermark_video_ai_max_frames: number;
  watermark_inpaint_prompt: string;
};

export default function ConfigCenter() {
  const { t } = useTranslation("settings");
  const navigate = useNavigate();
  const location = useLocation();
  const { role } = useAuth();
  const isAdmin = hasRole(role, UserRole.ADMIN);
  const [activeTab, setActiveTab] = useState<ActiveTabKey>(() =>
    hasRole(role, UserRole.ADMIN) ? "models" : "prompts"
  );
  const [loading, setLoading] = useState(false);

  const [models, setModels] = useState<ModelItem[]>([]);
  const [prompts, setPrompts] = useState<PromptItem[]>([]);
  const [styles, setStyles] = useState<StyleItem[]>([]);

  const [modelOpen, setModelOpen] = useState(false);
  const [textOpen, setTextOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [modelMode, setModelMode] = useState<EditorMode>("create");
  const [textMode, setTextMode] = useState<EditorMode>("create");
  const [editingModel, setEditingModel] = useState<ModelItem | null>(null);
  const [editingTextId, setEditingTextId] = useState<number | null>(null);

  const [modelForm] = Form.useForm<ModelFormValues>();
  const [textForm] = Form.useForm<TextFormValues>();
  const [storageForm] = Form.useForm<StorageFormValues>();
  const [youtubeForm] = Form.useForm<YoutubeFormValues>();
  const [cvForm] = Form.useForm<CVFormValues>();
  const [integrationMeta, setIntegrationMeta] = useState<IntegrationSettingsRead | null>(null);
  const [integrationLoading, setIntegrationLoading] = useState(false);
  const [integrationSaving, setIntegrationSaving] = useState(false);
  const [integrationSubTab, setIntegrationSubTab] = useState<"storage" | "youtube" | "cv">("storage");
  const [testYoutubeLoading, setTestYoutubeLoading] = useState(false);
  const [testStorageLoading, setTestStorageLoading] = useState(false);
  const [domainCheckLoading, setDomainCheckLoading] = useState<null | "aliyun" | "tencent">(null);

  const parseSupportedModels = (raw: string | null | undefined): Array<{ label: string; value: string }> => {
    if (!raw || !raw.trim()) return [];
    try {
      const data = JSON.parse(raw) as Array<string | { label?: string; value?: string }>;
      if (!Array.isArray(data)) return [];
      return data
        .map((item) => {
          if (typeof item === "string") {
            const v = item.trim();
            return v ? { label: v, value: v } : null;
          }
          if (!item || typeof item !== "object") return null;
          const label = String(item.label ?? "").trim();
          const value = String(item.value ?? "").trim();
          if (!label && !value) return null;
          return { label: label || value, value: value || label };
        })
        .filter((x): x is { label: string; value: string } => Boolean(x));
    } catch {
      return [];
    }
  };

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [modelList, promptList, styleList] = await Promise.all([
        listModelsApi(),
        listPromptsApi(),
        listStylesApi(),
      ]);
      setModels(modelList);
      setPrompts(promptList);
      setStyles(styleList);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const applyIntegrationReadToForms = useCallback((data: IntegrationSettingsRead) => {
    setIntegrationMeta(data);
    storageForm.setFieldsValue({
      active_storage_provider: normStorageProviderRadio(data.active_storage_provider),
      aliyun_access_key_id: data.aliyun_access_key_id || "",
      aliyun_access_key_secret: "",
      aliyun_role_arn: data.aliyun_role_arn || "",
      aliyun_region_id: data.aliyun_region_id || "",
      aliyun_oss_bucket_name: data.aliyun_oss_bucket_name || "",
      aliyun_oss_endpoint: data.aliyun_oss_endpoint || "",
      aliyun_custom_domain: data.aliyun_custom_domain || "",
      tencent_cos_secret_id: data.tencent_cos_secret_id || "",
      tencent_cos_secret_key: "",
      tencent_cos_region: data.tencent_cos_region || "",
      tencent_cos_bucket: data.tencent_cos_bucket || "",
      tencent_custom_domain: data.tencent_custom_domain || "",
    });
    youtubeForm.setFieldsValue({
      youtube_api_key: "",
      google_oauth_client_id: data.google_oauth_client_id || "",
      google_oauth_client_secret: "",
      google_oauth_redirect_uri: data.google_oauth_redirect_uri || "",
    });
    cvForm.setFieldsValue({
      volc_cv_access_key_id: data.volc_cv_access_key_id || "",
      volc_cv_secret_access_key: "",
      volc_cv_region: data.volc_cv_region || "",
      volc_cv_host: data.volc_cv_host || "",
      volc_cv_inpaint_req_key: data.volc_cv_inpaint_req_key || "",
      watermark_video_ai_max_frames: data.watermark_video_ai_max_frames ?? 180,
      watermark_inpaint_prompt: data.watermark_inpaint_prompt || "",
    });
  }, [storageForm, youtubeForm, cvForm]);

  const loadIntegration = useCallback(async () => {
    setIntegrationLoading(true);
    try {
      const data = await getIntegrationSettingsApi();
      applyIntegrationReadToForms(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.loadFailed"));
    } finally {
      setIntegrationLoading(false);
    }
  }, [applyIntegrationReadToForms]);

  useEffect(() => {
    const queryTab = new URLSearchParams(location.search).get("tab");
    const adminTabs = new Set<ActiveTabKey>(["models", "integration"]);
    if (
      queryTab === "models" ||
      queryTab === "prompts" ||
      queryTab === "styles" ||
      queryTab === "integration"
    ) {
      // Non-admins cannot access admin-only tabs via URL params
      if (adminTabs.has(queryTab as ActiveTabKey) && !isAdmin) return;
      setActiveTab(queryTab);
    }
  }, [location.search, isAdmin]);

  /** 当角色变化导致当前 activeTab 不再可见时，自动切换到第一个可见 Tab。
   * 使用 useRef 追踪上一次 isAdmin，仅在 isAdmin 真正从 true 变为 false 时执行重置，
   * 避免每次 activeTab 变化都触发 effect。 */
  const prevIsAdminRef = useRef(isAdmin);
  useEffect(() => {
    if (prevIsAdminRef.current && !isAdmin) {
      const adminOnlyTabs: Set<ActiveTabKey> = new Set(["models", "integration"]);
      if (adminOnlyTabs.has(activeTab)) {
        setActiveTab("prompts");
      }
    }
    prevIsAdminRef.current = isAdmin;
  }, [isAdmin, activeTab]);

  useEffect(() => {
    if (activeTab === "integration" && isAdmin) void loadIntegration();
  }, [activeTab, loadIntegration, isAdmin]);

  const openCreateModel = () => {
    setModelMode("create");
    setEditingModel(null);
    modelForm.resetFields();
    modelForm.setFieldsValue({ supported_models: [], library_kind: "chat", protocol: "anthropic" });
    setModelOpen(true);
  };

  const openEditModel = (row: ModelItem) => {
    setModelMode("edit");
    setEditingModel(row);
    modelForm.setFieldsValue({
      name: row.name,
      library_kind: row.library_kind ?? "chat",
      api_base_url: row.api_base_url,
      protocol: row.protocol ?? "anthropic",
      supported_models: parseSupportedModels(row.supported_models_json),
      api_key: "",
    });
    setModelOpen(true);
  };

  const submitModel = async () => {
    try {
      const values = await modelForm.validateFields();
      const libKind = (values.library_kind ?? "chat").trim();
      setSaving(true);
      const payload: {
        name?: string;
        api_base_url?: string;
        api_key?: string;
        supported_models_json?: string | null;
        library_kind?: string;
        protocol?: string;
      } = {
        name: values.name.trim(),
        api_base_url: values.api_base_url.trim(),
        library_kind: libKind,
        protocol: (values.protocol ?? "anthropic").trim(),
      };
      const supportedModels = (values.supported_models ?? []).map((x) => ({
        label: String(x?.label ?? "").trim(),
        value: String(x?.value ?? "").trim(),
      }));
      const hasPartial = supportedModels.some((x) => (x.label && !x.value) || (!x.label && x.value));
      if (hasPartial) {
        message.warning(t("configCenter.modelLabelPair"));
        setSaving(false);
        return;
      }
      const normalizedModels = supportedModels
        .filter((x) => x.label && x.value)
        .map((x) => ({ label: x.label, value: x.value }));
      payload.supported_models_json = normalizedModels.length ? JSON.stringify(normalizedModels) : null;
      if (values.api_key?.trim()) {
        payload.api_key = values.api_key.trim();
      }
      if (modelMode === "create") {
        await createModelApi(payload as Required<Pick<typeof payload, "name" | "api_base_url">> & typeof payload);
        message.success(t("configCenter.modelCreateSuccess"));
      } else if (editingModel) {
        await updateModelApi(editingModel.id, payload);
        message.success(t("configCenter.modelUpdateSuccess"));
      }
      setModelOpen(false);
      await loadAll();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.saveModelFailed"));
    } finally {
      setSaving(false);
    }
  };

  const openCreateText = () => {
    setTextMode("create");
    setEditingTextId(null);
    textForm.resetFields();
    setTextOpen(true);
  };

  const openEditText = (id: number, title: string, content: string) => {
    setTextMode("edit");
    setEditingTextId(id);
    textForm.setFieldsValue({ title, content });
    setTextOpen(true);
  };

  const submitText = async () => {
    try {
      const values = await textForm.validateFields();
      setSaving(true);
      const payload = { title: values.title.trim(), content: values.content.trim() };
      if (activeTab === "prompts") {
        if (textMode === "create") {
          await createPromptApi(payload);
          message.success(t("configCenter.promptCreateSuccess"));
        } else if (editingTextId != null) {
          await updatePromptApi(editingTextId, payload);
          message.success(t("configCenter.promptUpdateSuccess"));
        }
      } else {
        if (textMode === "create") {
          await createStyleApi(payload);
          message.success(t("configCenter.styleCreateSuccess"));
        } else if (editingTextId != null) {
          await updateStyleApi(editingTextId, payload);
          message.success(t("configCenter.styleUpdateSuccess"));
        }
      }
      setTextOpen(false);
      await loadAll();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const modelColumns: ColumnsType<ModelItem> = useMemo(
    () => [
      { title: t("configCenter.modelName"), dataIndex: "name", key: "name" },
      {
        title: t("configCenter.modelKind"),
        key: "library_kind",
        width: 120,
        render: (_: unknown, row: ModelItem) =>
          row.library_kind === "image_inpaint" ? (
            <Tag color="purple">{t("configCenter.modelKindInpaint")}</Tag>
          ) : (
            <Tag>{t("configCenter.modelKindChat")}</Tag>
          ),
      },
      { title: t("configCenter.modelUrl"), dataIndex: "api_base_url", key: "api_base_url" },
      {
        title: t("configCenter.modelKey"),
        key: "key",
        render: (_, row) => (row.has_api_key ? "********" : t("configCenter.keyPlaceholder")),
      },
      {
        title: t("configCenter.supportedModels"),
        dataIndex: "supported_models_json",
        key: "supported_models_json",
        render: (v: string | null) => {
          const items = parseSupportedModels(v);
          if (!items.length) return "-";
          return (
            <Space size={[6, 6]} wrap>
              {items.map((item) => (
                <Tag key={`${item.value}-${item.label}`}>
                  {t("configCenter.supportedModelTag", { label: item.label, value: item.value })}
                </Tag>
              ))}
            </Space>
          );
        },
      },
      {
        title: t("action.edit"),
        key: "op",
        render: (_, row) => (
          <Space>
            <Button size="small" onClick={() => openEditModel(row)}>
              {t("action.edit")}
            </Button>
            <Popconfirm
              title={t("configCenter.deleteModel")}
              onConfirm={async () => {
                await deleteModelApi(row.id);
                message.success(t("message.deleteSuccess"));
                await loadAll();
              }}
            >
              <Button size="small" danger>
                {t("action.delete")}
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [loadAll]
  );

  const promptColumns: ColumnsType<PromptItem> = useMemo(
    () => [
      { title: t("configCenter.modelName"), dataIndex: "title", key: "title" },
      { title: t("configCenter.promptContent"), dataIndex: "content", key: "content", ellipsis: true },
      {
        title: t("configCenter.editPrompt"),
        key: "op",
        render: (_, row) => (
          <Space>
            <Button size="small" onClick={() => navigate(`/config/agent/edit/${row.id}`)}>
              {t("configCenter.editPrompt")}
            </Button>
            <Popconfirm
              title={t("configCenter.deletePrompt")}
              onConfirm={async () => {
                await deletePromptApi(row.id);
                message.success(t("message.deleteSuccess"));
                await loadAll();
              }}
            >
              <Button size="small" danger>
                {t("action.delete")}
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [loadAll, navigate]
  );

  const trimOrNull = (s: string | undefined) => {
    const t = (s ?? "").trim();
    return t.length ? t : null;
  };

  const submitStorageSettings = async () => {
    try {
      const values = await storageForm.validateFields();
      setIntegrationSaving(true);
      const payload: IntegrationSettingsUpdatePayload = {
        active_storage_provider: values.active_storage_provider,
        aliyun_access_key_id: trimOrNull(values.aliyun_access_key_id),
        aliyun_role_arn: trimOrNull(values.aliyun_role_arn),
        aliyun_region_id: trimOrNull(values.aliyun_region_id),
        aliyun_oss_bucket_name: trimOrNull(values.aliyun_oss_bucket_name),
        aliyun_oss_endpoint: trimOrNull(values.aliyun_oss_endpoint),
        aliyun_custom_domain: trimOrNull(values.aliyun_custom_domain),
        tencent_cos_secret_id: trimOrNull(values.tencent_cos_secret_id),
        tencent_cos_region: trimOrNull(values.tencent_cos_region),
        tencent_cos_bucket: trimOrNull(values.tencent_cos_bucket),
        tencent_custom_domain: trimOrNull(values.tencent_custom_domain),
      };
      const asec = (values.aliyun_access_key_secret ?? "").trim();
      if (asec && !looksLikeMaskedSecret(asec)) payload.aliyun_access_key_secret = asec;
      const tsec = (values.tencent_cos_secret_key ?? "").trim();
      if (tsec && !looksLikeMaskedSecret(tsec)) payload.tencent_cos_secret_key = tsec;

      const updated = await updateIntegrationSettingsApi(payload);
      applyIntegrationReadToForms(updated);
      message.success(t("configCenter.storageSaveSuccess"));
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.saveFailed"));
    } finally {
      setIntegrationSaving(false);
    }
  };

  const submitYoutubeSettings = async () => {
    try {
      const values = await youtubeForm.validateFields();
      setIntegrationSaving(true);
      const payload: IntegrationSettingsUpdatePayload = {};
      const y = (values.youtube_api_key ?? "").trim();
      if (y && !looksLikeMaskedSecret(y)) payload.youtube_api_key = y;
      const gcid = (values.google_oauth_client_id ?? "").trim();
      if (gcid) payload.google_oauth_client_id = gcid;
      const gcsec = (values.google_oauth_client_secret ?? "").trim();
      if (gcsec && !looksLikeMaskedSecret(gcsec)) payload.google_oauth_client_secret = gcsec;
      const guri = (values.google_oauth_redirect_uri ?? "").trim();
      if (guri) payload.google_oauth_redirect_uri = guri;
      const updated = await updateIntegrationSettingsApi(payload);
      applyIntegrationReadToForms(updated);
      message.success(t("configCenter.youtubeSaveSuccess"));
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.saveFailed"));
    } finally {
      setIntegrationSaving(false);
    }
  };

  const submitCVSettings = async () => {
    try {
      const values = await cvForm.validateFields();
      setIntegrationSaving(true);
      const payload: IntegrationSettingsUpdatePayload = {
        volc_cv_access_key_id: trimOrNull(values.volc_cv_access_key_id),
        volc_cv_region: trimOrNull(values.volc_cv_region),
        volc_cv_host: trimOrNull(values.volc_cv_host),
        volc_cv_inpaint_req_key: trimOrNull(values.volc_cv_inpaint_req_key),
      };
      const wm = values.watermark_video_ai_max_frames;
      if (wm != null && !Number.isNaN(Number(wm))) {
        payload.watermark_video_ai_max_frames = Math.max(1, Math.min(10000, Number(wm)));
      } else {
        payload.watermark_video_ai_max_frames = null;
      }
      const wp = (values.watermark_inpaint_prompt ?? "").trim();
      payload.watermark_inpaint_prompt = wp.length ? wp : null;
      const vcsk = (values.volc_cv_secret_access_key ?? "").trim();
      if (vcsk && !looksLikeMaskedSecret(vcsk)) payload.volc_cv_secret_access_key = vcsk;
      const updated = await updateIntegrationSettingsApi(payload);
      applyIntegrationReadToForms(updated);
      message.success(t("configCenter.cvSaveSuccess"));
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.saveFailed"));
    } finally {
      setIntegrationSaving(false);
    }
  };

  const runTestYoutube = async () => {
    setTestYoutubeLoading(true);
    try {
      const r = await testYoutubeIntegrationApi();
      if (r.ok) message.success(r.message);
      else message.error(r.message);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.testFailed"));
    } finally {
      setTestYoutubeLoading(false);
    }
  };

  const runTestStorage = async () => {
    setTestStorageLoading(true);
    try {
      const r = await testStorageIntegrationApi();
      if (r.ok) message.success(r.message);
      else message.error(r.message);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.testFailed"));
    } finally {
      setTestStorageLoading(false);
    }
  };

  const runValidateStorageDomain = async (platform: "aliyun" | "tencent") => {
    const field = platform === "aliyun" ? "aliyun_custom_domain" : "tencent_custom_domain";
    const domain = ((storageForm.getFieldValue(field) as string | undefined) ?? "").trim();
    if (!domain) {
      message.warning(t("configCenter.domainCheckWarning"));
      return;
    }
    setDomainCheckLoading(platform);
    try {
      const r = await validateStorageCustomDomainApi({ platform, domain });
      if (r.ok) message.success(r.message);
      else message.error(r.message);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.domainCheckFailed"));
    } finally {
      setDomainCheckLoading(null);
    }
  };

  const styleColumns: ColumnsType<StyleItem> = useMemo(
    () => [
      { title: t("configCenter.modelName"), dataIndex: "title", key: "title" },
      { title: t("configCenter.styleContent"), dataIndex: "content", key: "content", ellipsis: true },
      {
        title: t("configCenter.editStyle"),
        key: "op",
        render: (_, row) => (
          <Space>
            <Button size="small" onClick={() => openEditText(row.id, row.title, row.content)}>
              {t("configCenter.editStyle")}
            </Button>
            <Popconfirm
              title={t("configCenter.deleteStyle")}
              onConfirm={async () => {
                await deleteStyleApi(row.id);
                message.success(t("configCenter.styleDeleteSuccess"));
                await loadAll();
              }}
            >
              <Button size="small" danger>
                {t("configCenter.deleteStyle")}
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [loadAll]
  );

  return (
    <div className="p-4 md:p-6">
      <Spin spinning={loading}>
        <div className="bg-yc-bg-card border border-yc-border rounded-lg p-4 shadow-sm">
          <Tabs
            activeKey={activeTab}
            onChange={(k) => {
              const tab = k as ActiveTabKey;
              setActiveTab(tab);
              // 仅在当前路径为 config-center 时同步 URL，避免跳转到 agent-edit 时被拉回
              if (location.pathname === "/config-center") {
                navigate(`/config-center?tab=${tab}`, { replace: true });
              }
            }}
            items={([
              {
                key: "models",
                label: t("configCenter.models"),
                children: (
                  <>
                    <div className="mb-3">
                      <Button type="primary" onClick={openCreateModel}>
                        {t("configCenter.addModel")}
                      </Button>
                    </div>
                    <Table rowKey="id" columns={modelColumns} dataSource={models} pagination={{ pageSize: 10 }} />
                  </>
                ),
              },
              {
                key: "prompts",
                label: t("configCenter.prompts"),
                children: (
                  <>
                    <div className="mb-3">
                      <Button type="primary" onClick={openCreateText}>
                        {t("configCenter.addPrompt")}
                      </Button>
                    </div>
                    <Table rowKey="id" columns={promptColumns} dataSource={prompts} pagination={{ pageSize: 10 }} />
                  </>
                ),
              },
              {
                key: "styles",
                label: t("configCenter.styles"),
                children: (
                  <>
                    <div className="mb-3">
                      <Button type="primary" onClick={openCreateText}>
                        {t("configCenter.addStyle")}
                      </Button>
                    </div>
                    <Table rowKey="id" columns={styleColumns} dataSource={styles} pagination={{ pageSize: 10 }} />
                  </>
                ),
              },
              {
                key: "integration",
                label: t("configCenter.integration"),
                children: (
                  <Spin spinning={integrationLoading}>
                    <p className="text-yc-text-secondary text-sm mb-3">
                      {t("configCenter.orgInfo")}<strong>{integrationMeta?.org_name || "—"}</strong>
                      {t("configCenter.orgId")}{integrationMeta?.org_id ?? "—"}{t("configCenter.orgIdClose")}<strong>{t("configCenter.orgPriority")}</strong>
                      {t("configCenter.orgShared")}{t("configCenter.secretMaskPrefix")}{" "}
                      <code className="text-xs">{SECRET_MASK}</code> {t("configCenter.secretMaskSuffix")}
                    </p>
                    <div className="mb-3 flex flex-wrap gap-2">
                      <Popconfirm
                        title={t("configCenter.clearOrgConfirm")}
                        description={t("configCenter.clearOrgDesc")}
                        onConfirm={async () => {
                          try {
                            await deleteIntegrationSettingsApi();
                            message.success(t("configCenter.clearSuccess"));
                            await loadIntegration();
                          } catch (e: any) {
                            message.error(e?.response?.data?.detail ?? e?.message ?? t("configCenter.clearFailed"));
                          }
                        }}
                      >
                        <Button danger>{t("configCenter.clearOrg")}</Button>
                      </Popconfirm>
                    </div>
                    <Tabs
                      activeKey={integrationSubTab}
                      onChange={(k) => setIntegrationSubTab(k as "storage" | "youtube" | "cv")}
                      items={[
                        {
                          key: "storage",
                          label: t("configCenter.storage.title"),
                          children: (
                            <div className="pt-2">
                              <div className="mb-3 flex flex-wrap gap-2">
                                <Button type="primary" loading={integrationSaving} onClick={() => void submitStorageSettings()}>
                                  {t("configCenter.storage.save")}
                                </Button>
                                <Button loading={testStorageLoading} onClick={() => void runTestStorage()}>
                                  {t("configCenter.storage.test")}
                                </Button>
                              </div>
                              <Form form={storageForm} layout="vertical" disabled={integrationLoading}>
                                <Card size="small" title={t("configCenter.storage.title")} className="mb-4">
                                  <Form.Item
                                    name="active_storage_provider"
                                    label={t("configCenter.storage.provider")}
                                    rules={[{ required: true, message: t("configCenter.selectProvider") }]}
                                  >
                                    <Radio.Group>
                                      <Radio value="ALIYUN">{t("configCenter.storage.aliyun")}</Radio>
                                      <Radio value="TENCENT">{t("configCenter.storage.tencent")}</Radio>
                                    </Radio.Group>
                                  </Form.Item>
                                </Card>
                                <Card size="small" title={t("configCenter.storage.aliyun")} className="mb-4">
                                  <Form.Item name="aliyun_access_key_id" label="AccessKey ID">
                                    <Input autoComplete="off" />
                                  </Form.Item>
                                  <Form.Item
                                    name="aliyun_access_key_secret"
                                    label="AccessKey Secret"
                                    extra={
                                      integrationMeta?.has_aliyun_access_key_secret
                                        ? t("configCenter.keyHasValue")
                                        : undefined
                                    }
                                  >
                                    <Input.Password
                                      placeholder={
                                        integrationMeta?.has_aliyun_access_key_secret
                                          ? t("configCenter.keyPlaceholder")
                                          : t("configCenter.keyCreatePlaceholder")
                                      }
                                      autoComplete="new-password"
                                    />
                                  </Form.Item>
                                  <Form.Item name="aliyun_role_arn" label={t("configCenter.roleArnLabel")}>
                                    <Input placeholder="acs:ram::..." />
                                  </Form.Item>
                                  <Form.Item name="aliyun_region_id" label="Region ID">
                                    <Input placeholder="cn-hangzhou" />
                                  </Form.Item>
                                  <Form.Item name="aliyun_oss_bucket_name" label="Bucket">
                                    <Input />
                                  </Form.Item>
                                  <Form.Item name="aliyun_oss_endpoint" label="Endpoint">
                                    <Input placeholder="oss-cn-xxx.aliyuncs.com" />
                                  </Form.Item>
                                  <Form.Item
                                    label={t("configCenter.storage.customDomain")}
                                    extra={t("configCenter.storage.customDomainExtra")}
                                  >
                                    <Space.Compact className="w-full max-w-xl">
                                      <Form.Item name="aliyun_custom_domain" noStyle>
                                        <Input placeholder="https://cdn.example.com" allowClear />
                                      </Form.Item>
                                      <Button
                                        loading={domainCheckLoading === "aliyun"}
                                        onClick={() => void runValidateStorageDomain("aliyun")}
                                      >
                                        {t("configCenter.storage.checkDomain")}
                                      </Button>
                                    </Space.Compact>
                                  </Form.Item>
                                </Card>
                                <Card size="small" title={t("configCenter.storage.tencent")}>
                                  <Form.Item name="tencent_cos_secret_id" label="SecretId">
                                    <Input autoComplete="off" />
                                  </Form.Item>
                                  <Form.Item
                                    name="tencent_cos_secret_key"
                                    label="SecretKey"
                                    extra={
                                      integrationMeta?.has_tencent_cos_secret_key
                                        ? t("configCenter.keyHasValue")
                                        : undefined
                                    }
                                  >
                                    <Input.Password placeholder={t("configCenter.keyPlaceholder")} autoComplete="new-password" />
                                  </Form.Item>
                                  <Form.Item name="tencent_cos_region" label="Region">
                                    <Input placeholder="ap-guangzhou" />
                                  </Form.Item>
                                  <Form.Item name="tencent_cos_bucket" label="Bucket">
                                    <Input />
                                  </Form.Item>
                                  <Form.Item
                                    label={t("configCenter.storage.customDomain")}
                                    extra={t("configCenter.storage.customDomainExtraTencent")}
                                  >
                                    <Space.Compact className="w-full max-w-xl">
                                      <Form.Item name="tencent_custom_domain" noStyle>
                                        <Input placeholder="https://cdn.example.com" allowClear />
                                      </Form.Item>
                                      <Button
                                        loading={domainCheckLoading === "tencent"}
                                        onClick={() => void runValidateStorageDomain("tencent")}
                                      >
                                        {t("configCenter.storage.checkDomain")}
                                      </Button>
                                    </Space.Compact>
                                  </Form.Item>
                                </Card>
                              </Form>
                            </div>
                          ),
                        },
                        {
                          key: "youtube",
                          label: t("configCenter.youtube.title"),
                          children: (
                            <div className="pt-2 max-w-xl">
                              <div className="mb-3 flex flex-wrap gap-2">
                                <Button type="primary" loading={integrationSaving} onClick={() => void submitYoutubeSettings()}>
                                  {t("configCenter.youtube.save")}
                                </Button>
                                <Button loading={testYoutubeLoading} onClick={() => void runTestYoutube()}>
                                  {t("configCenter.youtube.test")}
                                </Button>
                              </div>
                              <Form form={youtubeForm} layout="vertical" disabled={integrationLoading}>
                                <Form.Item
                                  name="youtube_api_key"
                                  label={t("configCenter.youtube.keyLabel")}
                                  extra={
                                    integrationMeta?.has_youtube_api_key
                                      ? t("configCenter.youtube.keyExtra")
                                      : t("configCenter.youtube.keyExtraNoConfig")
                                  }
                                >
                                  <Input.Password placeholder={t("configCenter.youtube.keyPlaceholder")} autoComplete="new-password" />
                                </Form.Item>
                                <div className="text-yc-text-secondary text-sm font-medium mt-4 mb-2">{t("configCenter.youtube.oauthTitle")}</div>
                                <p className="text-yc-text-tertiary text-xs mb-2">
                                  {t("configCenter.youtube.oauthDesc")}
                                </p>
                                <Form.Item
                                  name="google_oauth_client_id"
                                  label={t("configCenter.youtube.clientId")}
                                >
                                  <Input placeholder="xxx.apps.googleusercontent.com" autoComplete="off" />
                                </Form.Item>
                                <Form.Item
                                  name="google_oauth_client_secret"
                                  label={t("configCenter.youtube.clientSecret")}
                                  extra={
                                    integrationMeta?.has_google_oauth_client_secret
                                      ? t("configCenter.keyHasValue")
                                      : undefined
                                  }
                                >
                                  <Input.Password placeholder={t("configCenter.keyPlaceholder")} autoComplete="new-password" />
                                </Form.Item>
                                <Form.Item
                                  name="google_oauth_redirect_uri"
                                  label={t("configCenter.youtube.redirectUri")}
                                  extra={t("configCenter.youtube.redirectUriExtra")}
                                >
                                  <Input placeholder="https://your-domain.com/api/youtube/oauth/callback" autoComplete="off" />
                                </Form.Item>
                              </Form>
                            </div>
                          ),
                        },
                        {
                          key: "cv",
                          label: t("configCenter.volc.cvTitle"),
                          children: (
                            <div className="pt-2 max-w-xl">
                              <div className="mb-3">
                                <Button type="primary" loading={integrationSaving} onClick={() => void submitCVSettings()}>
                                  {t("configCenter.volc.save")}
                                </Button>
                              </div>
                              <Form form={cvForm} layout="vertical" disabled={integrationLoading}>
                                <div className="text-yc-text-secondary text-sm font-medium mb-2">
                                  {t("configCenter.volc.cvTitle")}
                                </div>
                                <p className="text-yc-text-tertiary text-xs mb-2">
                                  {t("configCenter.volc.cvDesc")}
                                </p>
                                <Form.Item name="volc_cv_access_key_id" label={t("configCenter.volc.cvAccessKeyId")}>
                                  <Input placeholder={t("configCenter.volc.cvAccessKeyPlaceholder")} autoComplete="off" />
                                </Form.Item>
                                <Form.Item
                                  name="volc_cv_secret_access_key"
                                  label={t("configCenter.volc.cvSecretAccessKey")}
                                  extra={
                                    integrationMeta?.has_volc_cv_secret_access_key
                                      ? t("configCenter.volc.cvSecretExtra")
                                      : undefined
                                  }
                                >
                                  <Input.Password placeholder="SK" autoComplete="new-password" />
                                </Form.Item>
                                <Form.Item
                                  name="volc_cv_region"
                                  label={t("configCenter.volc.cvRegion")}
                                  extra={t("configCenter.volc.cvRegionExtra")}
                                >
                                  <Input placeholder="cn-north-1" />
                                </Form.Item>
                                <Form.Item
                                  name="volc_cv_host"
                                  label={t("configCenter.volc.cvHost")}
                                  extra={t("configCenter.volc.cvHostExtra")}
                                >
                                  <Input placeholder={t("configCenter.volc.cvHostPlaceholder")} />
                                </Form.Item>
                                <Form.Item
                                  name="volc_cv_inpaint_req_key"
                                  label={t("configCenter.volc.cvInpaintReqKey")}
                                  extra={t("configCenter.volc.cvInpaintExtra")}
                                >
                                  <Input placeholder="i2i_inpainting" />
                                </Form.Item>
                                <div className="text-yc-text-secondary text-sm font-medium mt-4 mb-2">{t("configCenter.volc.watermarkTitle")}</div>
                                <p className="text-yc-text-tertiary text-xs mb-2">
                                  {t("configCenter.volc.watermarkDesc")}
                                </p>
                                <Form.Item
                                  name="watermark_video_ai_max_frames"
                                  label={t("configCenter.volc.maxFrames")}
                                  extra={t("configCenter.volc.maxFramesExtra")}
                                >
                                  <InputNumber min={1} max={10000} className="w-full" />
                                </Form.Item>
                                <Form.Item
                                  name="watermark_inpaint_prompt"
                                  label={t("configCenter.volc.inpaintPrompt")}
                                >
                                  <Input.TextArea rows={3} placeholder={t("configCenter.volc.inpaintPlaceholder")} />
                                </Form.Item>
                              </Form>
                            </div>
                          ),
                        },
                      ]}
                    />
                  </Spin>
                ),
              },
            ]).filter(
              (item) => isAdmin || (item.key !== "models" && item.key !== "integration")
            )}
          />
        </div>
      </Spin>

      <Modal
        title={modelMode === "create" ? t("configCenter.addModel") : t("configCenter.editModel")}
        open={modelOpen}
        onOk={submitModel}
        onCancel={() => setModelOpen(false)}
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={modelForm} layout="vertical" initialValues={{ library_kind: "chat", protocol: "anthropic" }}>
          <Form.Item name="name" label={t("configCenter.modelName")} rules={[{ required: true, message: t("configCenter.nameRequired") }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="library_kind"
            label={t("configCenter.modelKind")}
            rules={[{ required: true, message: t("configCenter.kindRequired") }]}
            extra={t("configCenter.kindExtra")}
          >
            <Select
              options={[
                { value: "chat", label: t("configCenter.kindChat") },
                { value: "image_inpaint", label: t("configCenter.kindInpaint") },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="api_base_url"
            label={t("configCenter.baseUrlLabel")}
            rules={[{ required: true, message: t("configCenter.baseUrlRequired") }]}
            extra={t("configCenter.baseUrlExtra")}
          >
            <Input placeholder={t("configCenter.baseUrlPlaceholder")} />
          </Form.Item>
          <Form.Item
            name="protocol"
            label={t("configCenter.protocolLabel")}
            extra={t("configCenter.protocolExtra")}
          >
            <Select
              options={[
                { value: "anthropic", label: t("configCenter.protocolAnthropic") },
                { value: "openai", label: t("configCenter.protocolOpenai") },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="api_key"
            label={t("configCenter.modelKey")}
            tooltip={modelMode === "edit" ? t("configCenter.keyTooltip") : undefined}
          >
            <Input.Password
              placeholder={modelMode === "edit" && editingModel?.has_api_key ? t("configCenter.keyEditPlaceholder") : t("configCenter.keyCreatePlaceholder")}
              autoComplete="new-password"
            />
          </Form.Item>
          <Form.Item label={t("configCenter.supportedModels")}>
            <Form.List name="supported_models">
              {(fields, { add, remove }) => (
                <div className="space-y-2">
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} align="baseline" className="w-full">
                      <Form.Item
                        {...restField}
                        name={[name, "label"]}
                        className="!mb-0"
                        rules={[{ max: 128, message: t("configCenter.modelLabelTooLong") }]}
                      >
                        <Input placeholder={t("configCenter.modelLabelPlaceholder")} className="w-48" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, "value"]}
                        className="!mb-0"
                        rules={[{ max: 128, message: t("configCenter.modelValueTooLong") }]}
                      >
                        <Input
                          placeholder={t("configCenter.modelValuePlaceholder")}
                          className="w-56"
                        />
                      </Form.Item>
                      <Button
                        type="text"
                        danger
                        icon={<MinusCircleOutlined />}
                        onClick={() => remove(name)}
                        aria-label={t("configCenter.deleteModelAriaLabel")}
                      />
                    </Space>
                  ))}
                  <Button type="dashed" onClick={() => add({ label: "", value: "" })} block icon={<PlusOutlined />}>
                    {t("configCenter.addModelButton")}
                  </Button>
                </div>
              )}
            </Form.List>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`${activeTab === "prompts" ? t("configCenter.prompts") : t("configCenter.styles")}${textMode === "create" ? t("action.add") : t("configCenter.editModel")}`}
        open={textOpen}
        onOk={submitText}
        onCancel={() => setTextOpen(false)}
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={textForm} layout="vertical">
          <Form.Item name="title" label={t("configCenter.modelName")} rules={[{ required: true, message: t("configCenter.nameRequired") }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="content"
            label={activeTab === "prompts" ? t("configCenter.promptContent") : t("configCenter.styleContent")}
            rules={[{ required: true, message: t("configCenter.nameRequired") }]}
          >
            <Input.TextArea rows={8} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
