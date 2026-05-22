import { Button, Input, Modal, Popconfirm, Segmented, Select, Space, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { Pin } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import MarkdownEditorToggle from "@/components/MarkdownEditorToggle";
import {
  createManualKnowledgeScriptApi,
  deleteScriptApi,
  listScriptsApi,
  pinKnowledgeScriptApi,
  restoreScriptApi,
  type ScriptItem,
} from "@/services/libraryApi";

type ScriptStatus = "saved" | "configured" | "unconfigured";

function getScriptStatus(row: ScriptItem): ScriptStatus {
  // 手动录入不依赖提示词/风格，在列表中与「已配置」同级展示，便于直接进入 SOP
  if (row.origin_type === "MANUAL") return "configured";
  if (row.prompt_id && row.style_id) return "configured";
  return "unconfigured";
}

export default function KnowledgeBase() {
  const { t } = useTranslation("knowledge");
  const navigate = useNavigate();

  /** 根据脚本状态获取标签文本 */
  function getScriptStatusLabel(status: ScriptStatus): string {
    if (status === "configured") return t("base.configuredLabel");
    if (status === "unconfigured") return t("base.unconfiguredLabel");
    return t("base.savedLabel");
  }
  const [rows, setRows] = useState<ScriptItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [titleKeyword, setTitleKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | ScriptStatus>("all");
  const [viewMode, setViewMode] = useState<"active" | "recycle">("active");
  const [createOpen, setCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [formTitle, setFormTitle] = useState("");
  const [formPlot, setFormPlot] = useState("");
  const [timeSort, setTimeSort] = useState<"updated_at" | "created_at">("updated_at");
  const [pinningId, setPinningId] = useState<number | null>(null);

  const reloadScripts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listScriptsApi({
        includeDeleted: viewMode === "recycle",
        sort_by: timeSort,
      });
      setRows(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? t("base.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [viewMode, timeSort]);

  useEffect(() => {
    void reloadScripts();
  }, [reloadScripts]);

  const togglePin = useCallback(
    async (row: ScriptItem) => {
      if (viewMode !== "active") return;
      const next = !row.is_pinned;
      setPinningId(row.id);
      try {
        await pinKnowledgeScriptApi(row.id, next);
        message.success(next ? t("base.pinned") : t("base.unpinned"));
        await reloadScripts();
      } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } };
        message.error(err?.response?.data?.detail ?? t("base.pinFailed"));
      } finally {
        setPinningId(null);
      }
    },
    [reloadScripts, viewMode]
  );

  const columns: ColumnsType<ScriptItem> = useMemo(
    () => [
    {
      title: t("base.titleColumn"),
      dataIndex: "title",
      key: "title",
      render: (v: string, row) => (
        <Space size={8} wrap className="items-center">
          {viewMode === "active" ? (
            <button
              type="button"
              title={row.is_pinned ? t("base.unpinTitle") : t("base.pinTitle")}
              aria-label={row.is_pinned ? t("base.unpinTitle") : t("base.pinTitle")}
              disabled={pinningId === row.id}
              onClick={(e) => {
                e.stopPropagation();
                void togglePin(row);
              }}
              className={`p-1 rounded-md border border-transparent transition-colors shrink-0 ${
                row.is_pinned
                  ? "text-amber-600 bg-amber-100/80 border-amber-200 hover:bg-amber-100"
                  : "text-yc-text-tertiary hover:text-amber-600 hover:bg-amber-50"
              }`}
            >
              <Pin size={18} className={row.is_pinned ? "fill-amber-500" : ""} strokeWidth={row.is_pinned ? 2.5 : 2} />
            </button>
          ) : null}
          {row.origin_type === "MANUAL" ? (
            <Tag color="blue" className="m-0">
              {t("base.manualTag")}
            </Tag>
          ) : null}
          <span>{v}</span>
        </Space>
      ),
    },
    {
      title: t("base.statusColumn"),
      key: "status",
      width: 170,
      render: (_, row) => getScriptStatusLabel(getScriptStatus(row)),
    },
    {
      title: timeSort === "updated_at" ? t("base.updatedAtColumn") : t("base.createdAtColumn"),
      dataIndex: timeSort === "updated_at" ? "updated_at" : "created_at",
      key: timeSort,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
      width: 180,
    },
    {
      title: t("base.actionColumn"),
      key: "op",
      width: 260,
      render: (_, row) => (
        <Space size={8}>
          {viewMode === "active" ? (
            <>
              <Button
                type="primary"
                size="small"
                onClick={() => {
                  localStorage.setItem("sop_current_script_id", String(row.id));
                  localStorage.setItem("sop_current_script_title", row.title);
                  message.success(t("base.selectedScript", { title: row.title }));
                  navigate("/sop-workflow");
                }}
              >
                {t("base.continueSop")}
              </Button>
              <Popconfirm
                title={t("base.confirmDelete")}
                okText={t("base.confirmDeleteOk")}
                cancelText={t("base.cancel")}
                onConfirm={async () => {
                  try {
                    await deleteScriptApi(row.id);
                    message.success(t("base.deleteSuccess"));
                    await reloadScripts();
                  } catch (e: any) {
                    message.error(e?.response?.data?.detail ?? e?.message ?? t("base.deleteFailed"));
                  }
                }}
              >
                <Button danger size="small">
                  {t("base.delete")}
                </Button>
              </Popconfirm>
            </>
          ) : (
            <Popconfirm
              title={t("base.confirmRestore")}
              okText={t("base.confirmRestoreOk")}
              cancelText={t("base.cancel")}
              onConfirm={async () => {
                try {
                  await restoreScriptApi(row.id);
                  message.success(t("base.restoreSuccess"));
                  await reloadScripts();
                } catch (e: any) {
                  message.error(e?.response?.data?.detail ?? e?.message ?? t("base.restoreFailed"));
                }
              }}
            >
              <Button size="small">{t("base.restore")}</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
    ],
    [navigate, pinningId, reloadScripts, timeSort, togglePin, viewMode]
  );

  const filteredRows = useMemo(() => {
    const kw = titleKeyword.trim().toLowerCase();
    return rows.filter((row) => {
      const titleOk = !kw || row.title.toLowerCase().includes(kw);
      const status = getScriptStatus(row);
      const statusOk = viewMode === "recycle" || statusFilter === "all" || status === statusFilter;
      return titleOk && statusOk;
    });
  }, [rows, titleKeyword, statusFilter, viewMode]);

  const resetCreateForm = () => {
    setFormTitle("");
    setFormPlot("");
  };

  const submitManualCreate = async () => {
    const title = formTitle.trim();
    const plot = formPlot.trim();
    if (!title) {
      message.warning(t("base.titleRequired"));
      return;
    }
    if (!plot) {
      message.warning(t("base.plotRequired"));
      return;
    }
    setCreateSubmitting(true);
    try {
      await createManualKnowledgeScriptApi({ title, plot });
      message.success(t("base.savedToLibrary"));
      resetCreateForm();
      setCreateOpen(false);
      await reloadScripts();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? t("base.saveFailed"));
    } finally {
      setCreateSubmitting(false);
    }
  };

  return (
    <div className="p-6 md:p-10">
      <div className="max-w-6xl rounded-2xl border border-yc-border bg-yc-bg-card p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-2 text-yc-text-primary">{t("base.title")}</h2>
        <p className="text-yc-text-secondary mb-4">{t("base.subtitle")}</p>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Segmented
            value={viewMode}
            onChange={(v) => setViewMode(v as "active" | "recycle")}
            options={[
              { label: t("base.activeList"), value: "active" },
              { label: t("base.recycleBin"), value: "recycle" },
            ]}
          />
          {viewMode === "active" ? (
            <Button type="primary" onClick={() => setCreateOpen(true)}>
              {t("base.newKnowledge")}
            </Button>
          ) : null}
        </div>
        <div className="mb-4 flex flex-col md:flex-row gap-3 flex-wrap">
          <Input
            placeholder={t("base.searchPlaceholder")}
            value={titleKeyword}
            onChange={(e) => setTitleKeyword(e.target.value)}
            allowClear
            className="md:max-w-sm"
          />
          <Select
            value={timeSort}
            onChange={(v) => setTimeSort(v as "updated_at" | "created_at")}
            options={[
              { value: "updated_at", label: t("base.sortByUpdated") },
              { value: "created_at", label: t("base.sortByCreated") },
            ]}
            className="md:w-44"
          />
          {viewMode === "active" ? (
            <Select
              value={statusFilter}
              onChange={(v) => setStatusFilter(v)}
              options={[
                { value: "all", label: t("base.allStatus") },
                { value: "configured", label: t("base.configuredLabel") },
                { value: "unconfigured", label: t("base.unconfiguredLabel") },
              ]}
              className="md:w-60"
            />
          ) : null}
        </div>
        <Table<ScriptItem>
          rowKey="id"
          columns={columns}
          dataSource={filteredRows}
          loading={loading}
          rowClassName={(record) => (record.is_pinned ? "bg-amber-50/80" : "")}
          pagination={{ pageSize: 8 }}
        />

        <Modal
          title={t("base.newKnowledge")}
          open={createOpen}
          onCancel={() => {
            if (!createSubmitting) {
              setCreateOpen(false);
              resetCreateForm();
            }
          }}
          okText={t("base.save")}
          cancelText={t("base.cancel")}
          confirmLoading={createSubmitting}
          onOk={() => void submitManualCreate()}
          destroyOnClose
          width={960}
        >
          <div className="space-y-4 pt-2">
            <div>
              <div className="text-xs text-yc-text-secondary mb-1">{t("base.titleLabel")}</div>
              <Input
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                placeholder={t("base.titlePlaceholder")}
                maxLength={255}
                showCount
              />
            </div>
            <div>
              <div className="text-xs text-yc-text-secondary mb-1">{t("base.plotLabel")}</div>
              <MarkdownEditorToggle
                value={formPlot}
                onChange={setFormPlot}
                minRows={12}
                placeholder={t("base.plotPlaceholder")}
              />
              <div className="text-right text-xs text-yc-text-tertiary mt-1">{formPlot.length} / 500000</div>
            </div>
          </div>
        </Modal>
      </div>
    </div>
  );
}

