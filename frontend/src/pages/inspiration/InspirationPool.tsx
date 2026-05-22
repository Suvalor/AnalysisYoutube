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
import { useTranslation } from "react-i18next";
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
  const hasImg = Boolean((row.image_access_url || row.image_url || "").trim());
  return Math.max((row.content || "").length, hasImg ? 72 : 0);
}

function isPlotDone(row: InspirationItem) {
  return row.plot_id != null && row.plot_id > 0;
}

/** 判断灵感内容是否仅为图片占位符文本（兼容旧中文值和新英文值） */
function isPlaceholderOnlyText(row: InspirationItem) {
  const content = (row.content || "").trim();
  return (
    (content === INSPIRATION_IMAGE_PLACEHOLDER || content === "（图片灵感）") &&
    !!(row.image_access_url || row.image_url || "").trim()
  );
}

export default function InspirationPool() {
  const { t } = useTranslation("inspiration");
  const navigate = useNavigate();
  const openTab = useTabStore((s) => s.openTab);
  const [view, setView] = useState<"bubble" | "list">("bubble");
  const [rows, setRows] = useState<InspirationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [draftImageUrl, setDraftImageUrl] = useState<string | null>(null);
  const [draftImageAssetId, setDraftImageAssetId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<InspirationItem | null>(null);
  const [editForm] = Form.useForm();
  const [editImageUrl, setEditImageUrl] = useState<string | null>(null);
  const [editImageAssetId, setEditImageAssetId] = useState<number | null>(null);
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
      message.error(typeof d === "string" ? d : t("pool.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const runImageUpload = async (file: File, mode: "create" | "edit") => {
    if (!file.type.startsWith("image/")) {
      message.error(t("pool.imageOnly"));
      return;
    }
    const setBusy = mode === "create" ? setUploading : setEditUploading;
    setBusy(true);
    try {
      const res = await uploadMaterialImageApi(file, false);
      const show = (res.access_url || res.file_url || "").trim();
      if (!show) {
        message.error(t("pool.uploadNoUrl"));
        return;
      }
      if (mode === "create") {
        setDraftImageUrl(show);
        setDraftImageAssetId(res.id);
        form.setFieldsValue({ content: "" });
      } else {
        setEditImageUrl(show);
        setEditImageAssetId(res.id);
        editForm.setFieldsValue({ content: "" });
      }
      message.success(t("pool.imageUploaded"));
    } catch (e: unknown) {
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : t("pool.imageUploadFailed"));
    } finally {
      setBusy(false);
    }
  };

  const goToPlotWorkflow = async (row: InspirationItem) => {
    try {
      const outline = buildScriptOutlineFromInspiration(row);
      const script = await createScriptApi({
        title: `${t("pool.inspirationPrefix")}${row.id}`,
        content: outline,
      });
      localStorage.setItem("sop_current_script_id", String(script.id));
      localStorage.setItem("sop_current_script_title", script.title);
      const sopPath = `/sop-workflow?inspirationId=${row.id}`;
      openTab({ id: "sop-workflow", title: t("pool.sopWorkflow", { defaultValue: "SOP Workflow" }), path: sopPath, type: "sop-workflow" });
      navigate(sopPath);
      message.success(t("pool.jumpToPlot"));
    } catch (e: unknown) {
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : t("pool.createScriptFailed"));
    }
  };

  const onCreate = async () => {
    const text = String(form.getFieldValue("content") || "").trim();
    const hasImg = Boolean(draftImageUrl?.trim());
    if (!text && !hasImg) {
      message.warning(t("pool.fillTextOrImage"));
      return;
    }
    if (text && hasImg) {
      message.warning(t("pool.chooseOneOnly"));
      return;
    }
    try {
      const v = await form.validateFields(["source", "recorded_at"]);
      const recorded = v.recorded_at as dayjs.Dayjs | undefined;
      await createInspirationApi({
        content: hasImg ? "" : text,
        image_asset_id: hasImg && draftImageAssetId != null ? draftImageAssetId : undefined,
        image_url: hasImg && draftImageAssetId == null ? draftImageUrl : undefined,
        source: String(v.source || "").trim(),
        recorded_at: recorded ? recorded.toISOString() : undefined,
      });
      message.success(t("pool.saveSuccess"));
      form.resetFields();
      form.setFieldsValue({ recorded_at: dayjs() });
      setDraftImageUrl(null);
      setDraftImageAssetId(null);
      await reload();
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return;
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : t("pool.saveFailed"));
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
    setEditImageUrl((row.image_access_url || row.image_url || "").trim() || null);
    setEditImageAssetId(row.image_asset_id ?? null);
    setEditOpen(true);
  };

  const submitEdit = async () => {
    if (!editing) return;
    const text = String(editForm.getFieldValue("content") || "").trim();
    const hasImg = Boolean(editImageUrl?.trim());
    if (!text && !hasImg) {
      message.warning(t("pool.fillTextOrKeepImage"));
      return;
    }
    if (text && hasImg) {
      message.warning(t("pool.chooseOneOnly"));
      return;
    }
    try {
      const v = await editForm.validateFields(["source", "recorded_at"]);
      const recorded = v.recorded_at as dayjs.Dayjs | undefined;
      const patch: Parameters<typeof updateInspirationApi>[1] = {
        source: String(v.source || "").trim(),
        recorded_at: recorded ? recorded.toISOString() : undefined,
      };
      if (hasImg) {
        patch.content = "";
        if (editImageAssetId != null) {
          patch.image_asset_id = editImageAssetId;
        } else {
          patch.image_asset_id = null;
          patch.image_url = editImageUrl;
        }
      } else {
        patch.content = text;
        patch.image_url = null;
        patch.image_asset_id = null;
      }
      await updateInspirationApi(editing.id, patch);
      message.success(t("pool.updateSuccess"));
      setEditOpen(false);
      setEditing(null);
      setEditImageUrl(null);
      setEditImageAssetId(null);
      await reload();
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return;
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : t("pool.updateFailed"));
    }
  };

  const columns: ColumnsType<InspirationItem> = [
    {
      title: t("pool.preview"),
      key: "preview",
      width: 72,
      render: (_, row) =>
        row.image_url || row.image_access_url ? (
          <img
            src={row.image_access_url || row.image_url || ""}
            alt=""
            className="w-11 h-11 rounded-md object-cover border border-yc-border"
          />
        ) : (
          <div className="w-11 h-11 rounded-md bg-yc-bg-secondary border border-yc-border flex items-center justify-center text-yc-text-tertiary text-xs">
            {t("pool.textIcon")}
          </div>
        ),
    },
    {
      title: t("pool.contentSummary"),
      dataIndex: "content",
      key: "content",
      ellipsis: true,
      render: (_, row) => {
        const label = isPlaceholderOnlyText(row) ? t("pool.imageInspiration") : row.content;
        return (
          <Text ellipsis={{ tooltip: label }} className="max-w-[240px]">
            {label}
          </Text>
        );
      },
    },
    { title: t("pool.sourceColumn"), dataIndex: "source", key: "source", width: 120, ellipsis: true },
    {
      title: t("pool.recordedAtLabel"),
      dataIndex: "recorded_at",
      key: "recorded_at",
      width: 160,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: t("pool.statusColumn"),
      key: "status",
      width: 110,
      render: (_, row) => (
        <Tag color={isPlotDone(row) ? "default" : "processing"}>{row.status}</Tag>
      ),
    },
    {
      title: t("pool.plotIdColumn"),
      dataIndex: "plot_id",
      key: "plot_id",
      width: 80,
      render: (v: number | null) => v ?? "—",
    },
    {
      title: t("pool.actionColumn"),
      key: "op",
      width: 260,
      render: (_, row) => (
        <Space size={6} wrap>
          <Button type="primary" size="small" onClick={() => void goToPlotWorkflow(row)}>
            {t("pool.generatePlot")}
          </Button>
          <Button size="small" onClick={() => openEdit(row)}>
            {t("pool.edit")}
          </Button>
          <Popconfirm title={t("pool.confirmDelete")} onConfirm={() => void handleDelete(row.id)}>
            <Button danger size="small">
              {t("pool.delete")}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleDelete = async (id: number) => {
    try {
      await deleteInspirationApi(id);
      message.success(t("pool.deleteSuccess"));
      await reload();
    } catch (e: unknown) {
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : t("pool.deleteFailed"));
    }
  };

  const bubbleContent = (row: InspirationItem) => (
    <div className="max-w-sm">
      {(row.image_access_url || row.image_url) ? (
        <div className="mb-2">
          <img
            src={row.image_access_url || row.image_url || ""}
            alt=""
            className="max-h-48 w-full rounded-lg object-contain bg-yc-bg-secondary border border-yc-border"
          />
        </div>
      ) : null}
      {!isPlaceholderOnlyText(row) ? (
        <Paragraph className="!mb-2 whitespace-pre-wrap">{row.content}</Paragraph>
      ) : null}
      <Text type="secondary" className="text-xs">
        {t("pool.sourcePrefix")}{row.source || t("pool.sourceEmpty")} · {dayjs(row.recorded_at).format("YYYY-MM-DD HH:mm")}
      </Text>
      <div className="mt-3 flex gap-2 flex-wrap">
        <Button type="primary" size="small" onClick={() => void goToPlotWorkflow(row)}>
          {t("pool.goToPlot")}
        </Button>
        <Button size="small" onClick={() => openEdit(row)}>
          {t("pool.edit")}
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
            <h2 className="text-xl font-semibold text-yc-text-primary">{t("pool.title")}</h2>
            <p className="text-sm text-yc-text-secondary">{t("pool.subtitle")}</p>
          </div>
        </div>
        <Segmented
          value={view}
          onChange={(v) => setView(v as "bubble" | "list")}
          options={[
            { label: t("pool.bubbleView"), value: "bubble" },
            { label: t("pool.listView"), value: "list" },
          ]}
        />
      </div>

      <Card title={t("pool.addTitle")} size="small" className="shadow-sm">
        <Alert
          type="info"
          showIcon
          className="mb-4"
          message={t("pool.textOrImageOnly")}
        />
        <Form form={form} layout="vertical" initialValues={{ recorded_at: dayjs() }} className="max-w-3xl">
          <Form.Item name="content" label={t("pool.contentLabel")}>
            <TextArea
              rows={4}
              placeholder={draftImageUrl ? t("pool.contentImageMode") : t("pool.contentPlaceholder")}
              disabled={!!draftImageUrl}
              onChange={(e) => {
                if (e.target.value.trim()) {
                  setDraftImageUrl(null);
                  setDraftImageAssetId(null);
                }
              }}
            />
          </Form.Item>

          <Form.Item label={t("pool.imageLabel")}>
            <div className="space-y-3">
              <Upload
                accept="image/*"
                showUploadList={false}
                disabled={hasTextDraft || uploading}
                beforeUpload={(file: RcFile) => {
                  if (hasTextDraft) {
                    message.warning(t("pool.textExistsUploadWarning"));
                    return Upload.LIST_IGNORE;
                  }
                  void runImageUpload(file, "create");
                  return false;
                }}
              >
                <Button icon={<UploadCloud size={16} />} loading={uploading} disabled={hasTextDraft}>
                  {hasTextDraft ? t("pool.clearTextFirst") : t("pool.uploadImage")}
                </Button>
              </Upload>
              {draftImageUrl ? (
                <div className="flex items-start gap-3 p-3 rounded-lg border border-yc-border bg-yc-bg-secondary w-fit max-w-full">
                  <img
                    src={draftImageUrl}
                    alt={t("pool.previewAlt")}
                    className="h-24 w-24 rounded-md object-cover border border-white shadow-sm"
                  />
                  <div className="flex flex-col gap-2">
                    <Text type="secondary" className="text-xs">
                      {t("pool.imageSelected")}
                    </Text>
                    <Button
                      danger
                      type="default"
                      size="small"
                      icon={<Trash2 size={14} />}
                      onClick={() => {
                        setDraftImageUrl(null);
                        setDraftImageAssetId(null);
                      }}
                    >
                      {t("pool.removeImage")}
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          </Form.Item>

          <Form.Item name="source" label={t("pool.sourceLabel")}>
            <Input placeholder={t("pool.sourcePlaceholder")} />
          </Form.Item>
          <Form.Item name="recorded_at" label={t("pool.recordedAtLabel")}>
            <DatePicker showTime className="w-full max-w-md" format="YYYY-MM-DD HH:mm" />
          </Form.Item>
          <Button type="primary" onClick={() => void onCreate()}>
            {t("pool.save")}
          </Button>
        </Form>
      </Card>

      {view === "list" ? (
        <Card size="small" className="shadow-sm">
          <div className="mb-2 flex justify-end">
            <Button onClick={() => void reload()} loading={loading}>
              {t("pool.refresh")}
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
        <Card size="small" className="shadow-sm" title={t("pool.galaxyTitle")}>
          <div className="mb-2 flex justify-end">
            <Button onClick={() => void reload()} loading={loading}>
              {t("pool.refresh")}
            </Button>
          </div>
          <div
            className="relative rounded-xl border border-yc-border bg-gradient-to-br from-indigo-50 via-white to-amber-50 overflow-hidden"
            style={{ minHeight: 520 }}
          >
            {rows.length === 0 && !loading ? (
              <div className="absolute inset-0 flex items-center justify-center text-yc-text-tertiary text-sm">
                {t("pool.noInspiration")}
              </div>
            ) : null}
            {rows.map((row) => {
              const { leftPct, topPct, size } = bubbleLayout(row.id, bubbleWeight(row));
              const done = isPlotDone(row);
              const img = (row.image_access_url || row.image_url || "").trim();
              return (
                <Popover key={row.id} title={`${t("pool.inspirationPrefix")}${row.id}`} content={bubbleContent(row)} trigger="click">
                  <button
                    type="button"
                    className={`absolute rounded-full shadow-md border-2 overflow-hidden flex items-center justify-center text-white text-xs font-medium cursor-pointer transition-transform hover:scale-110 hover:z-10 focus:outline-none focus:ring-2 focus:ring-violet-400 ${
                      done
                        ? "bg-yc-text-tertiary/80 border-yc-border opacity-80"
                        : "border-white/40 bg-gradient-to-br from-violet-500 to-fuchsia-500"
                    }`}
                    style={{
                      left: `${leftPct}%`,
                      top: `${topPct}%`,
                      width: size,
                      height: size,
                      transform: "translate(-50%, -50%)",
                    }}
                    aria-label={t("pool.inspirationLabel") + " " + row.id}
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
            <div className="mt-2 text-xs text-yc-text-secondary">
              {t("pool.grayBubbleHint")}
            </div>
          ) : null}
        </Card>
      )}

      <Modal
        title={t("pool.editTitle")}
        open={editOpen}
        onCancel={() => {
          setEditOpen(false);
          setEditing(null);
          setEditImageUrl(null);
          setEditImageAssetId(null);
        }}
        onOk={() => void submitEdit()}
        destroyOnClose
        width={560}
      >
        <Alert type="info" showIcon className="mb-3" message={t("pool.textOrImageEdit")} />
        <Form form={editForm} layout="vertical">
          <Form.Item name="content" label={t("pool.contentLabel")}>
            <TextArea
              rows={4}
              placeholder={editImageUrl ? t("pool.contentImageMode") : ""}
              disabled={!!editImageUrl}
              onChange={(e) => {
                if (e.target.value.trim()) {
                  setEditImageUrl(null);
                  setEditImageAssetId(null);
                }
              }}
            />
          </Form.Item>
          <Form.Item label={t("pool.imageLabel")}>
            <Space direction="vertical" size="small" className="w-full">
              <Upload
                accept="image/*"
                showUploadList={false}
                disabled={hasTextEdit || editUploading}
                beforeUpload={(file: RcFile) => {
                  if (hasTextEdit) {
                    message.warning(t("pool.clearTextUploadWarning"));
                    return Upload.LIST_IGNORE;
                  }
                  void runImageUpload(file, "edit");
                  return false;
                }}
              >
                <Button icon={<ImageIcon size={16} />} loading={editUploading} disabled={hasTextEdit}>
                  {hasTextEdit ? t("pool.clearTextFirst") : t("pool.editUploadImage")}
                </Button>
              </Upload>
              {editImageUrl ? (
                <div className="flex items-start gap-3">
                  <img src={editImageUrl} alt="" className="h-20 w-20 rounded object-cover border" />
                  <Button
                    size="small"
                    danger
                    onClick={() => {
                      setEditImageUrl(null);
                      setEditImageAssetId(null);
                    }}
                  >
                    {t("pool.removeImage")}
                  </Button>
                </div>
              ) : null}
            </Space>
          </Form.Item>
          <Form.Item name="source" label={t("pool.editSourceLabel")}>
            <Input />
          </Form.Item>
          <Form.Item name="recorded_at" label={t("pool.recordedAtLabel")}>
            <DatePicker showTime className="w-full" format="YYYY-MM-DD HH:mm" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
