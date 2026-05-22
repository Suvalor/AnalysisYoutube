import { Button, Input, Modal, Popconfirm, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useTabStore } from "@/store/useTabStore";
import {
  createFeishuDocApi,
  deleteFeishuDocApi,
  listFeishuDocsApi,
  triggerFeishuDocArchiveApi,
  type FeishuDocItem,
} from "@/services/feishuDocsApi";

dayjs.extend(relativeTime);

export default function FeishuDocList() {
  const { t } = useTranslation("feishu");
  const navigate = useNavigate();
  const openTab = useTabStore((s) => s.openTab);

  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<FeishuDocItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formTitle, setFormTitle] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [archiveSubmittingId, setArchiveSubmittingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listFeishuDocsApi({ page, page_size: pageSize, search: search.trim() || undefined });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      message.error(t("docList.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const archiving = items.some((x) => (x.archive_status ?? "UNARCHIVED") === "ARCHIVING");
    if (!archiving) return;
    const timer = window.setInterval(() => void load(), 4000);
    return () => window.clearInterval(timer);
  }, [items, load]);

  const openViewer = useCallback(
    (row: FeishuDocItem) => {
      const path = `/feishu/view/${row.id}`;
      openTab({
        id: `feishu-view-${row.id}`,
        title: row.title || `${t("docList.feishuDocPrefix")}${row.id}`,
        path,
        type: "feishu-viewer",
        feishuDocId: row.id,
      });
      navigate(path);
    },
    [navigate, openTab]
  );

  const handleArchive = useCallback(
    async (id: number) => {
      setArchiveSubmittingId(id);
      try {
        const res = await triggerFeishuDocArchiveApi(id);
        if (res.status === "already_archived") {
          message.success(res.message ?? t("docList.alreadyArchived"));
        } else {
          message.info(res.message ?? t("docList.archiveSubmitted"));
        }
        void load();
      } catch (e: unknown) {
        const err = e as { response?: { status?: number; data?: { detail?: string } } };
        const detail = err?.response?.data?.detail;
        if (err?.response?.status === 409) {
          message.warning(typeof detail === "string" ? detail : t("docList.archivingWarning"));
        } else {
          message.error(typeof detail === "string" ? detail : t("docList.archiveFailed"));
        }
      } finally {
        setArchiveSubmittingId(null);
      }
    },
    [load]
  );

  const columns: ColumnsType<FeishuDocItem> = useMemo(
    () => [
      {
        title: t("docList.docNameColumn"),
        dataIndex: "title",
        render: (v: string, r) => (
          <button type="button" className="text-blue-600 hover:text-blue-500" onClick={() => openViewer(r)}>
            {v}
          </button>
        ),
      },
      {
        title: t("docList.addedAtColumn"),
        dataIndex: "created_at",
        width: 160,
        render: (v: string) => {
          if (!v) return <span className="text-yc-text-tertiary">-</span>;
          const dt = dayjs(v);
          return <span title={dt.format("YYYY-MM-DD HH:mm")}>{dt.fromNow()}</span>;
        },
      },
      {
        title: t("docList.archiveStatusColumn"),
        key: "archive_state",
        width: 120,
        render: (_, r) => {
          const st = r.archive_status ?? "UNARCHIVED";
          if (st === "SUCCESS") {
            return <Tag color="success">{t("docList.success")}</Tag>;
          }
          if (st === "ARCHIVING") {
            return <Tag color="processing">{t("docList.saving")}</Tag>;
          }
          if (st === "FAILED") {
            return <Tag color="error">{t("docList.saveFailed")}</Tag>;
          }
          return <Tag>{t("docList.unarchived")}</Tag>;
        },
      },
      {
        title: t("docList.actionColumn"),
        key: "op",
        width: 340,
        render: (_, r) => {
          const st = r.archive_status ?? "UNARCHIVED";
          const canArchive = st === "UNARCHIVED" || st === "FAILED";
          return (
            <div className="flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
              <Button size="small" onClick={() => openViewer(r)}>
                {t("docList.view")}
              </Button>
              {st === "ARCHIVING" ? (
                <Button size="small" loading disabled>
                  {t("docList.archiving")}
                </Button>
              ) : canArchive ? (
                <Button size="small" onClick={() => void handleArchive(r.id)} loading={archiveSubmittingId === r.id}>
                  {st === "FAILED" ? t("docList.resave") : t("docList.offlineSave")}
                </Button>
              ) : null}
              <Popconfirm
                title={t("docList.confirmDelete")}
                okText={t("docList.delete")}
                cancelText={t("docList.cancel")}
                onConfirm={async () => {
                  await deleteFeishuDocApi(r.id);
                  message.success(t("docList.deleteSuccess"));
                  void load();
                }}
              >
                <Button danger size="small">
                  {t("docList.delete")}
                </Button>
              </Popconfirm>
            </div>
          );
        },
      },
    ],
    [archiveSubmittingId, handleArchive, load, openViewer]
  );

  const handleCreate = async () => {
    const titleVal = formTitle.trim();
    const urlVal = formUrl.trim();
    if (!titleVal) {
      message.warning(t("docList.titleRequired"));
      return;
    }
    if (!urlVal) {
      message.warning(t("docList.urlRequired"));
      return;
    }
    setCreating(true);
    try {
      await createFeishuDocApi({ title: titleVal, url: urlVal });
      message.success(t("docList.createSuccess"));
      setCreateOpen(false);
      setFormTitle("");
      setFormUrl("");
      setPage(1);
      void load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? t("docList.createFailed"));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="bg-yc-bg-card border border-yc-border rounded-lg p-4 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row gap-2 md:items-center md:justify-between">
          <div className="flex gap-2 items-center">
            <Input
              placeholder={t("docList.searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onPressEnter={() => {
                setPage(1);
                void load();
              }}
              style={{ width: 320 }}
            />
            <Button
              onClick={() => {
                setPage(1);
                void load();
              }}
              loading={loading}
            >
              {t("docList.search")}
            </Button>
          </div>
          <Button type="primary" onClick={() => setCreateOpen(true)}>
            {t("docList.addDoc")}
          </Button>
        </div>
      </div>

      <div className="bg-yc-bg-card border border-yc-border rounded-lg p-2 shadow-sm">
        <Table<FeishuDocItem>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={items}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: [10, 20, 50, 100],
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
        />
      </div>

      <Modal
        title={t("docList.addTitle")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        okText={t("docList.submit")}
        cancelText={t("docList.cancel")}
        confirmLoading={creating}
        onOk={() => void handleCreate()}
      >
        <div className="space-y-3">
          <div>
            <div className="text-xs text-yc-text-secondary mb-1">{t("docList.docNameLabel")}</div>
            <Input value={formTitle} onChange={(e) => setFormTitle(e.target.value)} placeholder={t("docList.docNamePlaceholder")} />
          </div>
          <div>
            <div className="text-xs text-yc-text-secondary mb-1">{t("docList.urlLabel")}</div>
            <Input value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder={t("docList.urlPlaceholder")} />
          </div>
        </div>
      </Modal>
    </div>
  );
}

