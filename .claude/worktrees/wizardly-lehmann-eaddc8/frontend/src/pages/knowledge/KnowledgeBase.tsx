import { Button, Input, Modal, Popconfirm, Segmented, Select, Space, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { Pin } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
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

function getScriptStatusLabel(status: ScriptStatus): string {
  if (status === "configured") return "已配置提示词与风格";
  if (status === "unconfigured") return "待补全配置";
  return "已保存";
}

export default function KnowledgeBase() {
  const navigate = useNavigate();
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
      message.error(e?.response?.data?.detail ?? e?.message ?? "加载剧本列表失败");
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
        message.success(next ? "已置顶" : "已取消置顶");
        await reloadScripts();
      } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } };
        message.error(err?.response?.data?.detail ?? "置顶操作失败");
      } finally {
        setPinningId(null);
      }
    },
    [reloadScripts, viewMode]
  );

  const columns: ColumnsType<ScriptItem> = useMemo(
    () => [
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      render: (v: string, row) => (
        <Space size={8} wrap className="items-center">
          {viewMode === "active" ? (
            <button
              type="button"
              title={row.is_pinned ? "取消置顶" : "置顶"}
              aria-label={row.is_pinned ? "取消置顶" : "置顶"}
              disabled={pinningId === row.id}
              onClick={(e) => {
                e.stopPropagation();
                void togglePin(row);
              }}
              className={`p-1 rounded-md border border-transparent transition-colors shrink-0 ${
                row.is_pinned
                  ? "text-amber-600 bg-amber-100/80 border-amber-200 hover:bg-amber-100"
                  : "text-slate-400 hover:text-amber-600 hover:bg-amber-50"
              }`}
            >
              <Pin size={18} className={row.is_pinned ? "fill-amber-500" : ""} strokeWidth={row.is_pinned ? 2.5 : 2} />
            </button>
          ) : null}
          {row.origin_type === "MANUAL" ? (
            <Tag color="blue" className="m-0">
              手动
            </Tag>
          ) : null}
          <span>{v}</span>
        </Space>
      ),
    },
    {
      title: "状态",
      key: "status",
      width: 170,
      render: (_, row) => getScriptStatusLabel(getScriptStatus(row)),
    },
    {
      title: timeSort === "updated_at" ? "更新时间" : "创建时间",
      dataIndex: timeSort === "updated_at" ? "updated_at" : "created_at",
      key: timeSort,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
      width: 180,
    },
    {
      title: "操作",
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
                  message.success(`已选中剧本《${row.title}》，进入下一步流程`);
                  navigate("/sop-workflow");
                }}
              >
                继续 SOP
              </Button>
              <Popconfirm
                title="确定要删除该剧本吗？"
                okText="确定删除"
                cancelText="取消"
                onConfirm={async () => {
                  try {
                    await deleteScriptApi(row.id);
                    message.success("删除成功");
                    await reloadScripts();
                  } catch (e: any) {
                    message.error(e?.response?.data?.detail ?? e?.message ?? "删除失败");
                  }
                }}
              >
                <Button danger size="small">
                  删除
                </Button>
              </Popconfirm>
            </>
          ) : (
            <Popconfirm
              title="确定要恢复该剧本吗？"
              okText="确定恢复"
              cancelText="取消"
              onConfirm={async () => {
                try {
                  await restoreScriptApi(row.id);
                  message.success("恢复成功");
                  await reloadScripts();
                } catch (e: any) {
                  message.error(e?.response?.data?.detail ?? e?.message ?? "恢复失败");
                }
              }}
            >
              <Button size="small">恢复</Button>
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
      message.warning("请填写标题/项目名");
      return;
    }
    if (!plot) {
      message.warning("请填写核心内容/剧情");
      return;
    }
    setCreateSubmitting(true);
    try {
      await createManualKnowledgeScriptApi({ title, plot });
      message.success("已保存到知识库");
      resetCreateForm();
      setCreateOpen(false);
      await reloadScripts();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? "保存失败");
    } finally {
      setCreateSubmitting(false);
    }
  };

  return (
    <div className="p-6 md:p-10">
      <div className="max-w-6xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-2 text-slate-900">知识库管理</h2>
        <p className="text-slate-600 mb-4">在此查看已保存剧本，并从任意剧本继续进入 SOP 下一步。</p>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Segmented
            value={viewMode}
            onChange={(v) => setViewMode(v as "active" | "recycle")}
            options={[
              { label: "正常列表", value: "active" },
              { label: "回收站", value: "recycle" },
            ]}
          />
          {viewMode === "active" ? (
            <Button type="primary" onClick={() => setCreateOpen(true)}>
              新建知识
            </Button>
          ) : null}
        </div>
        <div className="mb-4 flex flex-col md:flex-row gap-3 flex-wrap">
          <Input
            placeholder="按标题搜索"
            value={titleKeyword}
            onChange={(e) => setTitleKeyword(e.target.value)}
            allowClear
            className="md:max-w-sm"
          />
          <Select
            value={timeSort}
            onChange={(v) => setTimeSort(v as "updated_at" | "created_at")}
            options={[
              { value: "updated_at", label: "按最近更新" },
              { value: "created_at", label: "按创建时间" },
            ]}
            className="md:w-44"
          />
          {viewMode === "active" ? (
            <Select
              value={statusFilter}
              onChange={(v) => setStatusFilter(v)}
              options={[
                { value: "all", label: "全部状态" },
                { value: "configured", label: "已配置提示词与风格" },
                { value: "unconfigured", label: "待补全配置" },
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
          title="新建知识"
          open={createOpen}
          onCancel={() => {
            if (!createSubmitting) {
              setCreateOpen(false);
              resetCreateForm();
            }
          }}
          okText="保存"
          cancelText="取消"
          confirmLoading={createSubmitting}
          onOk={() => void submitManualCreate()}
          destroyOnClose
          width={960}
        >
          <div className="space-y-4 pt-2">
            <div>
              <div className="text-xs text-slate-600 mb-1">标题 / 项目名</div>
              <Input
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                placeholder="例如：第一集 · 开场冲突"
                maxLength={255}
                showCount
              />
            </div>
            <div>
              <div className="text-xs text-slate-600 mb-1">核心内容 / 剧情（Markdown，与 AI 脚本工坊落库格式一致）</div>
              <MarkdownEditorToggle
                value={formPlot}
                onChange={setFormPlot}
                minRows={12}
                placeholder="支持 ### 标题、**加粗**、表格、围栏代码块等；可切换「预览」或「分栏」查看渲染效果"
              />
              <div className="text-right text-xs text-slate-400 mt-1">{formPlot.length} / 500000</div>
            </div>
          </div>
        </Modal>
      </div>
    </div>
  );
}

