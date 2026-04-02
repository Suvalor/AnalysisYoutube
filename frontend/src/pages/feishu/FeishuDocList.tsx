import { Button, Input, Modal, Popconfirm, Table, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTabStore } from "@/store/useTabStore";
import { createFeishuDocApi, deleteFeishuDocApi, listFeishuDocsApi, type FeishuDocItem } from "@/services/feishuDocsApi";

dayjs.extend(relativeTime);

export default function FeishuDocList() {
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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listFeishuDocsApi({ page, page_size: pageSize, search: search.trim() || undefined });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      message.error("加载飞书文档列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search]);

  useEffect(() => {
    void load();
  }, [load]);

  const openViewer = (row: FeishuDocItem) => {
    const path = `/feishu/view/${row.id}`;
    openTab({ id: `feishu-view-${row.id}`, title: row.title || `飞书文档 #${row.id}`, path, type: "feishu-viewer", feishuDocId: row.id });
    navigate(path);
  };

  const columns: ColumnsType<FeishuDocItem> = useMemo(
    () => [
      {
        title: "文档名称",
        dataIndex: "title",
        render: (v: string, r) => (
          <button type="button" className="text-blue-600 hover:text-blue-500" onClick={() => openViewer(r)}>
            {v}
          </button>
        ),
      },
      {
        title: "添加时间",
        dataIndex: "created_at",
        width: 160,
        render: (v: string) => {
          if (!v) return <span className="text-slate-400">-</span>;
          const dt = dayjs(v);
          return <span title={dt.format("YYYY-MM-DD HH:mm")}>{dt.fromNow()}</span>;
        },
      },
      {
        title: "操作",
        key: "op",
        width: 220,
        render: (_, r) => (
          <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
            <Button size="small" onClick={() => openViewer(r)}>
              查看
            </Button>
            <Popconfirm
              title="确认删除该文档？"
              okText="删除"
              cancelText="取消"
              onConfirm={async () => {
                await deleteFeishuDocApi(r.id);
                message.success("已删除");
                void load();
              }}
            >
              <Button danger size="small">
                删除
              </Button>
            </Popconfirm>
          </div>
        ),
      },
    ],
    [load]
  );

  const handleCreate = async () => {
    const t = formTitle.trim();
    const u = formUrl.trim();
    if (!t) {
      message.warning("请输入文档名称");
      return;
    }
    if (!u) {
      message.warning("请输入飞书链接");
      return;
    }
    setCreating(true);
    try {
      await createFeishuDocApi({ title: t, url: u });
      message.success("已新增文档");
      setCreateOpen(false);
      setFormTitle("");
      setFormUrl("");
      setPage(1);
      void load();
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? "新增失败");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row gap-2 md:items-center md:justify-between">
          <div className="flex gap-2 items-center">
            <Input
              placeholder="按名称搜索"
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
              搜索
            </Button>
          </div>
          <Button type="primary" onClick={() => setCreateOpen(true)}>
            + 新增文档
          </Button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-2 shadow-sm">
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
        title="新增飞书文档"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        okText="提交"
        cancelText="取消"
        confirmLoading={creating}
        onOk={() => void handleCreate()}
      >
        <div className="space-y-3">
          <div>
            <div className="text-xs text-slate-600 mb-1">文档名称</div>
            <Input value={formTitle} onChange={(e) => setFormTitle(e.target.value)} placeholder="例如：选题库 / 脚本模板库" />
          </div>
          <div>
            <div className="text-xs text-slate-600 mb-1">飞书链接（URL）</div>
            <Input value={formUrl} onChange={(e) => setFormUrl(e.target.value)} placeholder="请输入飞书分享链接" />
          </div>
        </div>
      </Modal>
    </div>
  );
}

