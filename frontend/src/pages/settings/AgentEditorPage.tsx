import { Button, Form, Input, Popconfirm, message } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getPromptApi, updatePromptApi } from "@/services/libraryApi";

type AgentFormValues = {
  title: string;
  content: string;
};

type AgentEditorPageProps = {
  promptId?: number;
};

export default function AgentEditorPage({ promptId: promptIdFromTab }: AgentEditorPageProps) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm<AgentFormValues>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const initialRef = useRef<AgentFormValues | null>(null);
  const [invalidId, setInvalidId] = useState(false);

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
      } catch (e: any) {
        if (!mounted) return;
        message.error(e?.response?.data?.detail ?? e?.message ?? "加载智能体详情失败");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [form, navigate, promptId]);

  const isDirty = () => {
    const init = initialRef.current;
    if (!init) return false;
    const current = form.getFieldsValue();
    return current.title !== init.title || current.content !== init.content;
  };

  const goBack = () => {
    navigate("/config-center?tab=prompts");
  };

  const handleBack = () => {
    if (!isDirty()) {
      goBack();
      return;
    }
    // 使用浏览器 confirm，保证轻量且不引入额外状态
    const ok = window.confirm("当前有未保存修改，确认返回吗？");
    if (ok) goBack();
  };

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
      message.success("保存成功");
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error(e?.response?.data?.detail ?? e?.message ?? "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-4 md:p-6">
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">智能体编辑</h2>
            <p className="text-slate-500 mt-1">可在此编辑复杂系统提示词规则，保存后立即生效。</p>
          </div>
          <div className="flex items-center gap-2">
            <Popconfirm
              title="确认返回配置中心？"
              description={isDirty() ? "存在未保存修改，返回将丢失本次编辑。" : "将返回到智能体管理列表。"}
              okText="返回"
              cancelText="取消"
              onConfirm={goBack}
            >
              <Button>返回</Button>
            </Popconfirm>
            <Button type="primary" loading={saving} onClick={handleSave}>
              保存
            </Button>
          </div>
        </div>

        {invalidId ? (
          <div className="py-10 text-center">
            <p className="text-slate-600 mb-4">当前智能体 ID 无效，请返回智能体列表重新选择。</p>
            <Button type="primary" onClick={goBack}>
              返回智能体管理
            </Button>
          </div>
        ) : (
          <Form form={form} layout="vertical" disabled={loading}>
          <Form.Item name="title" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="例如：短视频脚本智能体" />
          </Form.Item>
          <Form.Item
            name="content"
            label="系统提示词规则 (Prompt)"
            rules={[{ required: true, message: "请输入系统提示词规则" }]}
          >
            <Input.TextArea
              placeholder="请输入完整系统提示词规则..."
              autoSize={{ minRows: 20, maxRows: 36 }}
            />
          </Form.Item>
          </Form>
        )}

        <div className="mt-4 flex gap-2">
          <Button onClick={handleBack}>返回</Button>
          <Button type="primary" loading={saving} onClick={handleSave} disabled={invalidId}>
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}
