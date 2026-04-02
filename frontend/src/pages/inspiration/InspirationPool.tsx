import {
  Alert,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Modal,
  Popconfirm,
  Popover,
  Segmented,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import type { RcFile } from "antd/es/upload";
import dayjs from "dayjs";
import { Image as ImageIcon, Lightbulb, Trash2, UploadCloud } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  INSPIRATION_IMAGE_PLACEHOLDER,
  buildScriptOutlineFromInspiration,
  createInspirationApi,
  deleteInspirationApi,
  listInspirationsApi,
  updateInspirationApi,
  type InspirationItem,
} from "@/services/inspirationApi";
import { createScriptApi, uploadMaterialImageApi } from "@/services/libraryApi";
import { useTabStore } from "@/store/useTabStore";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

/** 根据 id 生成稳定的球体位置与大小（轻量布局，无需 D3） */
function bubbleLayout(id: number, weight: number) {
  const r1 = ((id * 7919) % 1000) / 1000;
  const r2 = ((id * 4177) % 1000) / 1000;
  const size = 40 + (weight % 48);
  return { leftPct: 3 + r1 * 82, topPct: 3 + r2 * 78, size };
}

function bubbleWeight(row: InspirationItem) {
  return Math.max((row.content || "").length, row.image_url ? 72 : 0);
}

function isPlotDone(row: InspirationItem) {
  return row.status === "已生成剧情" || (row.plot_id != null && row.plot_id > 0);
}

function isPlaceholderOnlyText(row: InspirationItem) {
  return (row.content || "").trim() === INSPIRATION_IMAGE_PLACEHOLDER && !!row.image_url?.trim();
}

export default function InspirationPool() {
  const navigate = useNavigate();
  const openTab = useTabStore((s) => s.openTab);
  const [view, setView] = useState<"bubble" | "list">("bubble");
  const [rows, setRows] = useState<InspirationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [draftImageUrl, setDraftImageUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<InspirationItem | null>(null);
  const [editForm] = Form.useForm();
  const [editImageUrl, setEditImageUrl] = useState<string | null>(null);
  const [editUploading, setEditUploading] = useState(false);

  const contentWatch = Form.useWatch("content", form) as string | undefined;
  const hasTextDraft = Boolean((contentWatch || "").trim());
  const editContentWatch = Form.useWatch("content", editForm) as string | undefined;
  const hasTextEdit = Boolean((editContentWatch || "").trim());

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listInspirationsApi();
      setRows(data);
    } catch (e: unknown) {
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "加载灵感列表失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const runImageUpload = async (file: File, mode: "create" | "edit") => {
    if (!file.type.startsWith("image/")) {
      message.error("仅支持上传图片文件");
      return;
    }
    const setBusy = mode === "create" ? setUploading : setEditUploading;
    setBusy(true);
    try {
      const res = await uploadMaterialImageApi(file, false);
      if (!res.file_url) {
        message.error("上传未返回图片地址");
        return;
      }
      if (mode === "create") {
        setDraftImageUrl(res.file_url);
        form.setFieldsValue({ content: "" });
      } else {
        setEditImageUrl(res.file_url);
        editForm.setFieldsValue({ content: "" });
      }
      message.success("图片已上传");
    } catch (e: unknown) {
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "图片上传失败");
    } finally {
      setBusy(false);
    }
  };

  const goToPlotWorkflow = async (row: InspirationItem) => {
    try {
      const outline = buildScriptOutlineFromInspiration(row);
      const script = await createScriptApi({
        title: `灵感 #${row.id}`,
        content: outline,
      });
      localStorage.setItem("sop_current_script_id", String(script.id));
      localStorage.setItem("sop_current_script_title", script.title);
      const sopPath = `/sop-workflow?inspirationId=${row.id}`;
      openTab({ id: "sop-workflow", title: "SOP 工作流", path: sopPath, type: "sop-workflow" });
      navigate(sopPath);
      message.success("已跳转剧情拆解，大纲已填入文字与图片链接");
    } catch (e: unknown) {
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "创建剧本并跳转失败");
    }
  };

  const onCreate = async () => {
    const text = String(form.getFieldValue("content") || "").trim();
    const hasImg = Boolean(draftImageUrl?.trim());
    if (!text && !hasImg) {
      message.warning("请填写文字灵感或上传图片（二选一）");
      return;
    }
    if (text && hasImg) {
      message.warning("请只选择一种：清空文字后再传图，或移除图片后再写文字");
      return;
    }
    try {
      const v = await form.validateFields(["source", "recorded_at"]);
      const recorded = v.recorded_at as dayjs.Dayjs | undefined;
      await createInspirationApi({
        content: hasImg ? "" : text,
        image_url: hasImg ? draftImageUrl : undefined,
        source: String(v.source || "").trim(),
        recorded_at: recorded ? recorded.toISOString() : undefined,
      });
      message.success("灵感已保存");
      form.resetFields();
      form.setFieldsValue({ recorded_at: dayjs() });
      setDraftImageUrl(null);
      await reload();
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return;
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "保存失败");
    }
  };

  const openEdit = (row: InspirationItem) => {
    setEditing(row);
    const isPh = isPlaceholderOnlyText(row);
    editForm.setFieldsValue({
      content: isPh ? "" : row.content,
      source: row.source,
      recorded_at: dayjs(row.recorded_at),
    });
    setEditImageUrl(row.image_url?.trim() || null);
    setEditOpen(true);
  };

  const submitEdit = async () => {
    if (!editing) return;
    const text = String(editForm.getFieldValue("content") || "").trim();
    const hasImg = Boolean(editImageUrl?.trim());
    if (!text && !hasImg) {
      message.warning("请填写文字灵感或保留/上传图片");
      return;
    }
    if (text && hasImg) {
      message.warning("请只选择一种：清空文字后再传图，或移除图片后再写文字");
      return;
    }
    try {
      const v = await editForm.validateFields(["source", "recorded_at"]);
      const recorded = v.recorded_at as dayjs.Dayjs | undefined;
      await updateInspirationApi(editing.id, {
        content: hasImg ? "" : text,
        image_url: hasImg ? editImageUrl : null,
        source: String(v.source || "").trim(),
        recorded_at: recorded ? recorded.toISOString() : undefined,
      });
      message.success("已更新");
      setEditOpen(false);
      setEditing(null);
      setEditImageUrl(null);
      await reload();
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return;
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "更新失败");
    }
  };

  const columns: ColumnsType<InspirationItem> = [
    {
      title: "预览",
      key: "preview",
      width: 72,
      render: (_, row) =>
        row.image_url ? (
          <img
            src={row.image_url}
            alt=""
            className="w-11 h-11 rounded-md object-cover border border-slate-200"
          />
        ) : (
          <div className="w-11 h-11 rounded-md bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 text-xs">
            文
          </div>
        ),
    },
    {
      title: "内容摘要",
      dataIndex: "content",
      key: "content",
      ellipsis: true,
      render: (_, row) => {
        const label = isPlaceholderOnlyText(row) ? "（图片灵感）" : row.content;
        return (
          <Text ellipsis={{ tooltip: label }} className="max-w-[240px]">
            {label}
          </Text>
        );
      },
    },
    { title: "来源", dataIndex: "source", key: "source", width: 120, ellipsis: true },
    {
      title: "记录时间",
      dataIndex: "recorded_at",
      key: "recorded_at",
      width: 160,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "状态",
      key: "status",
      width: 110,
      render: (_, row) => (
        <Tag color={isPlotDone(row) ? "default" : "processing"}>{row.status}</Tag>
      ),
    },
    {
      title: "剧情 ID",
      dataIndex: "plot_id",
      key: "plot_id",
      width: 80,
      render: (v: number | null) => v ?? "—",
    },
    {
      title: "操作",
      key: "op",
      width: 260,
      render: (_, row) => (
        <Space size={6} wrap>
          <Button type="primary" size="small" onClick={() => void goToPlotWorkflow(row)}>
            一键生成剧情
          </Button>
          <Button size="small" onClick={() => openEdit(row)}>
            编辑
          </Button>
          <Popconfirm title="确定删除该灵感？" onConfirm={() => void handleDelete(row.id)}>
            <Button danger size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleDelete = async (id: number) => {
    try {
      await deleteInspirationApi(id);
      message.success("已删除");
      await reload();
    } catch (e: unknown) {
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "删除失败");
    }
  };

  const bubbleContent = (row: InspirationItem) => (
    <div className="max-w-sm">
      {row.image_url ? (
        <div className="mb-2">
          <img
            src={row.image_url}
            alt=""
            className="max-h-48 w-full rounded-lg object-contain bg-slate-100 border border-slate-200"
          />
        </div>
      ) : null}
      {!isPlaceholderOnlyText(row) ? (
        <Paragraph className="!mb-2 whitespace-pre-wrap">{row.content}</Paragraph>
      ) : null}
      <Text type="secondary" className="text-xs">
        来源：{row.source || "未填写"} · {dayjs(row.recorded_at).format("YYYY-MM-DD HH:mm")}
      </Text>
      <div className="mt-3 flex gap-2 flex-wrap">
        <Button type="primary" size="small" onClick={() => void goToPlotWorkflow(row)}>
          去生成剧情
        </Button>
        <Button size="small" onClick={() => openEdit(row)}>
          编辑
        </Button>
      </div>
    </div>
  );

  return (
    <div className="p-4 md:p-6 space-y-4 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2">
          <Lightbulb className="text-amber-500" size={26} />
          <div>
            <h2 className="text-xl font-semibold text-slate-900">灵感中心</h2>
            <p className="text-sm text-slate-500">记录灵感，一键进入 SOP 剧情拆解并自动关联。</p>
          </div>
        </div>
        <Segmented
          value={view}
          onChange={(v) => setView(v as "bubble" | "list")}
          options={[
            { label: "球形视图", value: "bubble" },
            { label: "列表视图", value: "list" },
          ]}
        />
      </div>

      <Card title="录入灵感" size="small" className="shadow-sm">
        <Alert
          type="info"
          showIcon
          className="mb-4"
          message="输入文字灵感 或 上传灵感图片（二选一，不可同时使用）"
        />
        <Form form={form} layout="vertical" initialValues={{ recorded_at: dayjs() }} className="max-w-3xl">
          <Form.Item name="content" label="灵感内容（think）">
            <TextArea
              rows={4}
              placeholder={draftImageUrl ? "已选择图片模式，请先移除图片再输入文字" : "写下你的想法…"}
              disabled={!!draftImageUrl}
              onChange={(e) => {
                if (e.target.value.trim()) setDraftImageUrl(null);
              }}
            />
          </Form.Item>

          <Form.Item label="灵感图片">
            <div className="space-y-3">
              <Upload
                accept="image/*"
                showUploadList={false}
                disabled={hasTextDraft || uploading}
                beforeUpload={(file: RcFile) => {
                  if (hasTextDraft) {
                    message.warning("已填写文字灵感，请先清空文字再上传图片");
                    return Upload.LIST_IGNORE;
                  }
                  void runImageUpload(file, "create");
                  return false;
                }}
              >
                <Button icon={<UploadCloud size={16} />} loading={uploading} disabled={hasTextDraft}>
                  {hasTextDraft ? "请先清空文字以启用上传" : "点击上传图片"}
                </Button>
              </Upload>
              {draftImageUrl ? (
                <div className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50 w-fit max-w-full">
                  <img
                    src={draftImageUrl}
                    alt="预览"
                    className="h-24 w-24 rounded-md object-cover border border-white shadow-sm"
                  />
                  <div className="flex flex-col gap-2">
                    <Text type="secondary" className="text-xs">
                      已选择图片灵感，保存时将只提交图片。
                    </Text>
                    <Button
                      danger
                      type="default"
                      size="small"
                      icon={<Trash2 size={14} />}
                      onClick={() => setDraftImageUrl(null)}
                    >
                      移除图片
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          </Form.Item>

          <Form.Item name="source" label="灵感来源">
            <Input placeholder="例如：通勤、对标视频、梦境…" />
          </Form.Item>
          <Form.Item name="recorded_at" label="记录时间">
            <DatePicker showTime className="w-full max-w-md" format="YYYY-MM-DD HH:mm" />
          </Form.Item>
          <Button type="primary" onClick={() => void onCreate()}>
            保存灵感
          </Button>
        </Form>
      </Card>

      {view === "list" ? (
        <Card size="small" className="shadow-sm">
          <div className="mb-2 flex justify-end">
            <Button onClick={() => void reload()} loading={loading}>
              刷新
            </Button>
          </div>
          <Table<InspirationItem>
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={rows}
            pagination={{ pageSize: 8 }}
          />
        </Card>
      ) : (
        <Card size="small" className="shadow-sm" title="灵感星系">
          <div className="mb-2 flex justify-end">
            <Button onClick={() => void reload()} loading={loading}>
              刷新
            </Button>
          </div>
          <div
            className="relative rounded-xl border border-slate-200 bg-gradient-to-br from-indigo-50 via-white to-amber-50 overflow-hidden"
            style={{ minHeight: 520 }}
          >
            {rows.length === 0 && !loading ? (
              <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">
                暂无灵感，先在上方录入一条吧
              </div>
            ) : null}
            {rows.map((row) => {
              const { leftPct, topPct, size } = bubbleLayout(row.id, bubbleWeight(row));
              const done = isPlotDone(row);
              const img = row.image_url?.trim();
              return (
                <Popover key={row.id} title={`灵感 #${row.id}`} content={bubbleContent(row)} trigger="click">
                  <button
                    type="button"
                    className={`absolute rounded-full shadow-md border-2 overflow-hidden flex items-center justify-center text-white text-xs font-medium cursor-pointer transition-transform hover:scale-110 hover:z-10 focus:outline-none focus:ring-2 focus:ring-violet-400 ${
                      done
                        ? "bg-slate-400/80 border-slate-300 opacity-80"
                        : "border-white/40 bg-gradient-to-br from-violet-500 to-fuchsia-500"
                    }`}
                    style={{
                      left: `${leftPct}%`,
                      top: `${topPct}%`,
                      width: size,
                      height: size,
                      transform: "translate(-50%, -50%)",
                    }}
                    aria-label={`灵感 ${row.id}`}
                  >
                    {img ? (
                      <img src={img} alt="" className="w-full h-full object-cover opacity-95" />
                    ) : done ? (
                      "✓"
                    ) : (
                      "💡"
                    )}
                    {done && img ? (
                      <span className="absolute inset-0 flex items-center justify-center bg-black/35 text-lg">✓</span>
                    ) : null}
                  </button>
                </Popover>
              );
            })}
          </div>
          {rows.some(isPlotDone) ? (
            <div className="mt-2 text-xs text-slate-500">
              灰色球体或带 ✓ 表示已关联剧情拆解；球内为缩略图时表示图片灵感。
            </div>
          ) : null}
        </Card>
      )}

      <Modal
        title="编辑灵感"
        open={editOpen}
        onCancel={() => {
          setEditOpen(false);
          setEditing(null);
          setEditImageUrl(null);
        }}
        onOk={() => void submitEdit()}
        destroyOnClose
        width={560}
      >
        <Alert type="info" showIcon className="mb-3" message="文字与图片二选一；与录入规则相同。" />
        <Form form={editForm} layout="vertical">
          <Form.Item name="content" label="灵感内容">
            <TextArea
              rows={4}
              placeholder={editImageUrl ? "已选择图片模式，请先移除图片" : ""}
              disabled={!!editImageUrl}
              onChange={(e) => {
                if (e.target.value.trim()) setEditImageUrl(null);
              }}
            />
          </Form.Item>
          <Form.Item label="灵感图片">
            <Space direction="vertical" size="small" className="w-full">
              <Upload
                accept="image/*"
                showUploadList={false}
                disabled={hasTextEdit || editUploading}
                beforeUpload={(file: RcFile) => {
                  if (hasTextEdit) {
                    message.warning("请先清空文字再上传图片");
                    return Upload.LIST_IGNORE;
                  }
                  void runImageUpload(file, "edit");
                  return false;
                }}
              >
                <Button icon={<ImageIcon size={16} />} loading={editUploading} disabled={hasTextEdit}>
                  {hasTextEdit ? "请先清空文字以启用上传" : "重新上传图片"}
                </Button>
              </Upload>
              {editImageUrl ? (
                <div className="flex items-start gap-3">
                  <img src={editImageUrl} alt="" className="h-20 w-20 rounded object-cover border" />
                  <Button size="small" danger onClick={() => setEditImageUrl(null)}>
                    移除图片
                  </Button>
                </div>
              ) : null}
            </Space>
          </Form.Item>
          <Form.Item name="source" label="来源">
            <Input />
          </Form.Item>
          <Form.Item name="recorded_at" label="记录时间">
            <DatePicker showTime className="w-full" format="YYYY-MM-DD HH:mm" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
