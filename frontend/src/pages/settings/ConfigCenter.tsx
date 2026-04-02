import { MinusCircleOutlined, PlusOutlined } from "@ant-design/icons";
import { Button, Card, Form, Input, Modal, Popconfirm, Radio, Space, Spin, Table, Tabs, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
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
  api_base_url: string;
  api_key?: string;
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
};

type VolcFormValues = {
  volcengine_api_key: string;
  volcengine_endpoint_id: string;
  volcengine_base_url: string;
  volcengine_model_gemini: string;
};

export default function ConfigCenter() {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<ActiveTabKey>("models");
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
  const [volcForm] = Form.useForm<VolcFormValues>();
  const [integrationMeta, setIntegrationMeta] = useState<IntegrationSettingsRead | null>(null);
  const [integrationLoading, setIntegrationLoading] = useState(false);
  const [integrationSaving, setIntegrationSaving] = useState(false);
  const [integrationSubTab, setIntegrationSubTab] = useState<"storage" | "youtube" | "volc">("storage");
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
      message.error(e?.response?.data?.detail ?? e?.message ?? "加载设置中心数据失败");
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
    youtubeForm.setFieldsValue({ youtube_api_key: "" });
    volcForm.setFieldsValue({
      volcengine_api_key: "",
      volcengine_endpoint_id: data.volcengine_endpoint_id || "",
      volcengine_base_url: data.volcengine_base_url || "",
      volcengine_model_gemini: data.volcengine_model_gemini || "",
    });
  }, [storageForm, youtubeForm, volcForm]);

  const loadIntegration = useCallback(async () => {
    setIntegrationLoading(true);
    try {
      const data = await getIntegrationSettingsApi();
      applyIntegrationReadToForms(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "加载集成配置失败");
    } finally {
      setIntegrationLoading(false);
    }
  }, [applyIntegrationReadToForms]);

  useEffect(() => {
    const queryTab = new URLSearchParams(location.search).get("tab");
    if (
      queryTab === "models" ||
      queryTab === "prompts" ||
      queryTab === "styles" ||
      queryTab === "integration"
    ) {
      setActiveTab(queryTab);
    }
  }, [location.search]);

  useEffect(() => {
    if (activeTab === "integration") void loadIntegration();
  }, [activeTab, loadIntegration]);

  const openCreateModel = () => {
    setModelMode("create");
    setEditingModel(null);
    modelForm.resetFields();
    modelForm.setFieldsValue({ supported_models: [] });
    setModelOpen(true);
  };

  const openEditModel = (row: ModelItem) => {
    setModelMode("edit");
    setEditingModel(row);
    modelForm.setFieldsValue({
      name: row.name,
      api_base_url: row.api_base_url,
      supported_models: parseSupportedModels(row.supported_models_json),
      api_key: "",
    });
    setModelOpen(true);
  };

  const submitModel = async () => {
    try {
      const values = await modelForm.validateFields();
      setSaving(true);
      const payload: {
        name?: string;
        api_base_url?: string;
        api_key?: string;
        supported_models_json?: string | null;
      } = {
        name: values.name.trim(),
        api_base_url: values.api_base_url.trim(),
      };
      const supportedModels = (values.supported_models ?? []).map((x) => ({
        label: String(x?.label ?? "").trim(),
        value: String(x?.value ?? "").trim(),
      }));
      const hasPartial = supportedModels.some((x) => (x.label && !x.value) || (!x.label && x.value));
      if (hasPartial) {
        message.warning("模型名称和模型 ID 需要成对填写");
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
        message.success("模型创建成功");
      } else if (editingModel) {
        await updateModelApi(editingModel.id, payload);
        message.success("模型更新成功");
      }
      setModelOpen(false);
      await loadAll();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? "保存模型失败");
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
          message.success("智能体创建成功");
        } else if (editingTextId != null) {
          await updatePromptApi(editingTextId, payload);
          message.success("智能体更新成功");
        }
      } else {
        if (textMode === "create") {
          await createStyleApi(payload);
          message.success("风格创建成功");
        } else if (editingTextId != null) {
          await updateStyleApi(editingTextId, payload);
          message.success("风格更新成功");
        }
      }
      setTextOpen(false);
      await loadAll();
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const modelColumns: ColumnsType<ModelItem> = useMemo(
    () => [
      { title: "名称", dataIndex: "name", key: "name" },
      { title: "URL", dataIndex: "api_base_url", key: "api_base_url" },
      {
        title: "Key",
        key: "key",
        render: (_, row) => (row.has_api_key ? "********" : "未设置"),
      },
      {
        title: "支持模型",
        dataIndex: "supported_models_json",
        key: "supported_models_json",
        render: (v: string | null) => {
          const items = parseSupportedModels(v);
          if (!items.length) return "-";
          return (
            <Space size={[6, 6]} wrap>
              {items.map((item) => (
                <Tag key={`${item.value}-${item.label}`}>
                  {item.label}（{item.value}）
                </Tag>
              ))}
            </Space>
          );
        },
      },
      {
        title: "操作",
        key: "op",
        render: (_, row) => (
          <Space>
            <Button size="small" onClick={() => openEditModel(row)}>
              编辑
            </Button>
            <Popconfirm
              title="确认删除该模型配置？"
              onConfirm={async () => {
                await deleteModelApi(row.id);
                message.success("删除成功");
                await loadAll();
              }}
            >
              <Button size="small" danger>
                删除
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
      { title: "名称", dataIndex: "title", key: "title" },
      { title: "系统提示词规则", dataIndex: "content", key: "content", ellipsis: true },
      {
        title: "操作",
        key: "op",
        render: (_, row) => (
          <Space>
            <Button size="small" onClick={() => navigate(`/config/agent/edit/${row.id}`)}>
              编辑
            </Button>
            <Popconfirm
              title="确认删除该智能体？"
              onConfirm={async () => {
                await deletePromptApi(row.id);
                message.success("删除成功");
                await loadAll();
              }}
            >
              <Button size="small" danger>
                删除
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
      message.success("云存储配置已保存（仅提交本页字段，组织内成员共享）");
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? "保存失败");
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
      const updated = await updateIntegrationSettingsApi(payload);
      applyIntegrationReadToForms(updated);
      message.success("YouTube 配置已保存");
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? "保存失败");
    } finally {
      setIntegrationSaving(false);
    }
  };

  const submitVolcSettings = async () => {
    try {
      const values = await volcForm.validateFields();
      setIntegrationSaving(true);
      const payload: IntegrationSettingsUpdatePayload = {
        volcengine_endpoint_id: trimOrNull(values.volcengine_endpoint_id),
        volcengine_base_url: trimOrNull(values.volcengine_base_url),
        volcengine_model_gemini: trimOrNull(values.volcengine_model_gemini),
      };
      const vk = (values.volcengine_api_key ?? "").trim();
      if (vk && !looksLikeMaskedSecret(vk)) payload.volcengine_api_key = vk;
      const updated = await updateIntegrationSettingsApi(payload);
      applyIntegrationReadToForms(updated);
      message.success("火山引擎配置已保存");
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? "保存失败");
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
      message.error(e?.response?.data?.detail ?? e?.message ?? "测试失败");
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
      message.error(e?.response?.data?.detail ?? e?.message ?? "测试失败");
    } finally {
      setTestStorageLoading(false);
    }
  };

  const runValidateStorageDomain = async (platform: "aliyun" | "tencent") => {
    const field = platform === "aliyun" ? "aliyun_custom_domain" : "tencent_custom_domain";
    const domain = ((storageForm.getFieldValue(field) as string | undefined) ?? "").trim();
    if (!domain) {
      message.warning("请先填写自定义访问域名（须含 https:// 或 http://）");
      return;
    }
    setDomainCheckLoading(platform);
    try {
      const r = await validateStorageCustomDomainApi({ platform, domain });
      if (r.ok) message.success(r.message);
      else message.error(r.message);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "校验失败");
    } finally {
      setDomainCheckLoading(null);
    }
  };

  const styleColumns: ColumnsType<StyleItem> = useMemo(
    () => [
      { title: "名称", dataIndex: "title", key: "title" },
      { title: "风格描述/附加提示词", dataIndex: "content", key: "content", ellipsis: true },
      {
        title: "操作",
        key: "op",
        render: (_, row) => (
          <Space>
            <Button size="small" onClick={() => openEditText(row.id, row.title, row.content)}>
              编辑
            </Button>
            <Popconfirm
              title="确认删除该风格？"
              onConfirm={async () => {
                await deleteStyleApi(row.id);
                message.success("删除成功");
                await loadAll();
              }}
            >
              <Button size="small" danger>
                删除
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
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
          <Tabs
            activeKey={activeTab}
            onChange={(k) => {
              const tab = k as ActiveTabKey;
              setActiveTab(tab);
              navigate(`/config-center?tab=${tab}`, { replace: true });
            }}
            items={[
              {
                key: "models",
                label: "模型管理",
                children: (
                  <>
                    <div className="mb-3">
                      <Button type="primary" onClick={openCreateModel}>
                        新增模型
                      </Button>
                    </div>
                    <Table rowKey="id" columns={modelColumns} dataSource={models} pagination={{ pageSize: 10 }} />
                  </>
                ),
              },
              {
                key: "prompts",
                label: "智能体管理",
                children: (
                  <>
                    <div className="mb-3">
                      <Button type="primary" onClick={openCreateText}>
                        新增智能体
                      </Button>
                    </div>
                    <Table rowKey="id" columns={promptColumns} dataSource={prompts} pagination={{ pageSize: 10 }} />
                  </>
                ),
              },
              {
                key: "styles",
                label: "风格管理",
                children: (
                  <>
                    <div className="mb-3">
                      <Button type="primary" onClick={openCreateText}>
                        新增风格
                      </Button>
                    </div>
                    <Table rowKey="id" columns={styleColumns} dataSource={styles} pagination={{ pageSize: 10 }} />
                  </>
                ),
              },
              {
                key: "integration",
                label: "云存储与外部 API",
                children: (
                  <Spin spinning={integrationLoading}>
                    <p className="text-slate-600 text-sm mb-3">
                      配置归属组织：<strong>{integrationMeta?.org_name || "—"}</strong>
                      （org_id: {integrationMeta?.org_id ?? "—"}）。<strong>组织库内配置优先于环境变量</strong>
                      ；同组织成员共享。每页仅提交当前 Tab 的字段（增量合并）。请勿将接口返回的{" "}
                      <code className="text-xs">{SECRET_MASK}</code> 当作新密钥填写。
                    </p>
                    <div className="mb-3 flex flex-wrap gap-2">
                      <Popconfirm
                        title="确认清除本组织在库内的全部集成覆盖？"
                        description="清除后本组织将完全依赖环境变量默认值。"
                        onConfirm={async () => {
                          try {
                            await deleteIntegrationSettingsApi();
                            message.success("已清除");
                            await loadIntegration();
                          } catch (e: any) {
                            message.error(e?.response?.data?.detail ?? e?.message ?? "清除失败");
                          }
                        }}
                      >
                        <Button danger>清除本组织覆盖</Button>
                      </Popconfirm>
                    </div>
                    <Tabs
                      activeKey={integrationSubTab}
                      onChange={(k) => setIntegrationSubTab(k as "storage" | "youtube" | "volc")}
                      items={[
                        {
                          key: "storage",
                          label: "云存储",
                          children: (
                            <div className="pt-2">
                              <div className="mb-3 flex flex-wrap gap-2">
                                <Button type="primary" loading={integrationSaving} onClick={() => void submitStorageSettings()}>
                                  保存云存储配置
                                </Button>
                                <Button loading={testStorageLoading} onClick={() => void runTestStorage()}>
                                  测试连接
                                </Button>
                              </div>
                              <Form form={storageForm} layout="vertical" disabled={integrationLoading}>
                                <Card size="small" title="存储平台（新上传默认）" className="mb-4">
                                  <Form.Item
                                    name="active_storage_provider"
                                    label="默认提供商"
                                    rules={[{ required: true, message: "请选择存储平台" }]}
                                  >
                                    <Radio.Group>
                                      <Radio value="ALIYUN">阿里云 OSS</Radio>
                                      <Radio value="TENCENT">腾讯云 COS</Radio>
                                    </Radio.Group>
                                  </Form.Item>
                                </Card>
                                <Card size="small" title="阿里云 OSS" className="mb-4">
                                  <Form.Item name="aliyun_access_key_id" label="AccessKey ID">
                                    <Input autoComplete="off" />
                                  </Form.Item>
                                  <Form.Item
                                    name="aliyun_access_key_secret"
                                    label="AccessKey Secret"
                                    extra={
                                      integrationMeta?.has_aliyun_access_key_secret
                                        ? `已配置（展示为 ${SECRET_MASK}），留空不修改`
                                        : undefined
                                    }
                                  >
                                    <Input.Password
                                      placeholder={
                                        integrationMeta?.has_aliyun_access_key_secret
                                          ? "留空不修改"
                                          : "填写后写入组织配置"
                                      }
                                      autoComplete="new-password"
                                    />
                                  </Form.Item>
                                  <Form.Item name="aliyun_role_arn" label="Role ARN（STS）">
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
                                    label="自定义访问域名 (Custom Domain)"
                                    extra="对外展示与签名链接的 Host 将使用该域名（须与阿里云/CDN 绑定一致）。示例：https://cdn.example.com"
                                  >
                                    <Space.Compact className="w-full max-w-xl">
                                      <Form.Item name="aliyun_custom_domain" noStyle>
                                        <Input placeholder="https://cdn.example.com" allowClear />
                                      </Form.Item>
                                      <Button
                                        loading={domainCheckLoading === "aliyun"}
                                        onClick={() => void runValidateStorageDomain("aliyun")}
                                      >
                                        检查
                                      </Button>
                                    </Space.Compact>
                                  </Form.Item>
                                </Card>
                                <Card size="small" title="腾讯云 COS">
                                  <Form.Item name="tencent_cos_secret_id" label="SecretId">
                                    <Input autoComplete="off" />
                                  </Form.Item>
                                  <Form.Item
                                    name="tencent_cos_secret_key"
                                    label="SecretKey"
                                    extra={
                                      integrationMeta?.has_tencent_cos_secret_key
                                        ? `已配置（${SECRET_MASK}），留空不修改`
                                        : undefined
                                    }
                                  >
                                    <Input.Password placeholder="留空不修改" autoComplete="new-password" />
                                  </Form.Item>
                                  <Form.Item name="tencent_cos_region" label="Region">
                                    <Input placeholder="ap-guangzhou" />
                                  </Form.Item>
                                  <Form.Item name="tencent_cos_bucket" label="Bucket">
                                    <Input />
                                  </Form.Item>
                                  <Form.Item
                                    label="自定义访问域名 (Custom Domain)"
                                    extra="对外展示与签名链接的 Host 将使用该域名（须与 COS 自定义域名/CDN 一致）。示例：https://cdn.example.com"
                                  >
                                    <Space.Compact className="w-full max-w-xl">
                                      <Form.Item name="tencent_custom_domain" noStyle>
                                        <Input placeholder="https://cdn.example.com" allowClear />
                                      </Form.Item>
                                      <Button
                                        loading={domainCheckLoading === "tencent"}
                                        onClick={() => void runValidateStorageDomain("tencent")}
                                      >
                                        检查
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
                          label: "YouTube Data API",
                          children: (
                            <div className="pt-2 max-w-xl">
                              <div className="mb-3 flex flex-wrap gap-2">
                                <Button type="primary" loading={integrationSaving} onClick={() => void submitYoutubeSettings()}>
                                  保存 YouTube 配置
                                </Button>
                                <Button loading={testYoutubeLoading} onClick={() => void runTestYoutube()}>
                                  测试连接
                                </Button>
                              </div>
                              <Form form={youtubeForm} layout="vertical" disabled={integrationLoading}>
                                <Form.Item
                                  name="youtube_api_key"
                                  label="YOUTUBE_API_KEY"
                                  extra={
                                    integrationMeta?.has_youtube_api_key
                                      ? `已配置（${SECRET_MASK}），留空不修改；定时任务按组织使用该 Key`
                                      : "未配置时使用环境变量"
                                  }
                                >
                                  <Input.Password placeholder="粘贴新 Key 以覆盖组织配置" autoComplete="new-password" />
                                </Form.Item>
                              </Form>
                            </div>
                          ),
                        },
                        {
                          key: "volc",
                          label: "火山引擎（LLM）",
                          children: (
                            <div className="pt-2 max-w-xl">
                              <div className="mb-3">
                                <Button type="primary" loading={integrationSaving} onClick={() => void submitVolcSettings()}>
                                  保存火山配置
                                </Button>
                              </div>
                              <Form form={volcForm} layout="vertical" disabled={integrationLoading}>
                                <Form.Item
                                  name="volcengine_api_key"
                                  label="API Key"
                                  extra={
                                    integrationMeta?.has_volcengine_api_key
                                      ? `已配置（${SECRET_MASK}），留空不修改`
                                      : undefined
                                  }
                                >
                                  <Input.Password placeholder="留空不修改" autoComplete="new-password" />
                                </Form.Item>
                                <Form.Item name="volcengine_endpoint_id" label="Endpoint / 默认模型 ID">
                                  <Input />
                                </Form.Item>
                                <Form.Item name="volcengine_base_url" label="Base URL">
                                  <Input placeholder="https://ark.../v3" />
                                </Form.Item>
                                <Form.Item
                                  name="volcengine_model_gemini"
                                  label="Gemini 别名（gemini-1.5-pro）"
                                  tooltip="Claude 别名使用 Endpoint ID"
                                >
                                  <Input />
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
            ]}
          />
        </div>
      </Spin>

      <Modal
        title={modelMode === "create" ? "新增模型" : "编辑模型"}
        open={modelOpen}
        onOk={submitModel}
        onCancel={() => setModelOpen(false)}
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={modelForm} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="api_base_url" label="URL" rules={[{ required: true, message: "请输入 URL" }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="api_key"
            label="Key"
            tooltip={modelMode === "edit" ? "留空表示不更新 Key" : undefined}
          >
            <Input.Password
              placeholder={modelMode === "edit" && editingModel?.has_api_key ? "********（留空不修改）" : "输入后将加密保存"}
              autoComplete="new-password"
            />
          </Form.Item>
          <Form.Item label="支持的模型列表">
            <Form.List name="supported_models">
              {(fields, { add, remove }) => (
                <div className="space-y-2">
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} align="baseline" className="w-full">
                      <Form.Item
                        {...restField}
                        name={[name, "label"]}
                        className="!mb-0"
                        rules={[{ max: 128, message: "模型名称过长" }]}
                      >
                        <Input placeholder="模型名称（label）" className="w-48" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, "value"]}
                        className="!mb-0"
                        rules={[{ max: 128, message: "模型 ID 过长" }]}
                      >
                        <Input placeholder="模型 ID（value）" className="w-56" />
                      </Form.Item>
                      <Button
                        type="text"
                        danger
                        icon={<MinusCircleOutlined />}
                        onClick={() => remove(name)}
                        aria-label="删除模型"
                      />
                    </Space>
                  ))}
                  <Button type="dashed" onClick={() => add({ label: "", value: "" })} block icon={<PlusOutlined />}>
                    添加模型
                  </Button>
                </div>
              )}
            </Form.List>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`${activeTab === "prompts" ? "智能体" : "风格"}${textMode === "create" ? "新增" : "编辑"}`}
        open={textOpen}
        onOk={submitText}
        onCancel={() => setTextOpen(false)}
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={textForm} layout="vertical">
          <Form.Item name="title" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="content"
            label={activeTab === "prompts" ? "系统提示词规则(Prompt)" : "风格描述/附加提示词"}
            rules={[{ required: true, message: "请输入内容" }]}
          >
            <Input.TextArea rows={8} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
