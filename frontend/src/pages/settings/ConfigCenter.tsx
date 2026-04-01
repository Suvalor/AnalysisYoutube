import { MinusCircleOutlined, PlusOutlined } from "@ant-design/icons";
import { Button, Form, Input, Modal, Popconfirm, Space, Spin, Table, Tabs, Tag, message } from "antd";
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

type EditorMode = "create" | "edit";
type ActiveTabKey = "models" | "prompts" | "styles";

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
      message.error(e?.response?.data?.detail ?? e?.message ?? "加载配置中心数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    const queryTab = new URLSearchParams(location.search).get("tab");
    if (queryTab === "models" || queryTab === "prompts" || queryTab === "styles") {
      setActiveTab(queryTab);
    }
  }, [location.search]);

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
