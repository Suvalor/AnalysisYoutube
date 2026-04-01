import { Button, Input, Popconfirm, Segmented, Select, Space, Table, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteScriptApi, listScriptsApi, restoreScriptApi, type ScriptItem } from "@/services/libraryApi";

type ScriptStatus = "saved" | "configured" | "unconfigured";

function getScriptStatus(row: ScriptItem): ScriptStatus {
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

  const reloadScripts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listScriptsApi(viewMode === "recycle");
      setRows(data);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "加载剧本列表失败");
    } finally {
      setLoading(false);
    }
  }, [viewMode]);

  useEffect(() => {
    void reloadScripts();
  }, [reloadScripts]);

  const columns: ColumnsType<ScriptItem> = [
    { title: "标题", dataIndex: "title", key: "title" },
    {
      title: "状态",
      key: "status",
      width: 170,
      render: (_, row) => getScriptStatusLabel(getScriptStatus(row)),
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      key: "updated_at",
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
  ];

  const filteredRows = useMemo(() => {
    const kw = titleKeyword.trim().toLowerCase();
    return rows.filter((row) => {
      const titleOk = !kw || row.title.toLowerCase().includes(kw);
      const status = getScriptStatus(row);
      const statusOk = viewMode === "recycle" || statusFilter === "all" || status === statusFilter;
      return titleOk && statusOk;
    });
  }, [rows, titleKeyword, statusFilter, viewMode]);

  return (
    <div className="p-6 md:p-10">
      <div className="max-w-6xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-2 text-slate-900">知识库管理</h2>
        <p className="text-slate-600 mb-4">在此查看已保存剧本，并从任意剧本继续进入 SOP 下一步。</p>
        <div className="mb-4">
          <Segmented
            value={viewMode}
            onChange={(v) => setViewMode(v as "active" | "recycle")}
            options={[
              { label: "正常列表", value: "active" },
              { label: "回收站", value: "recycle" },
            ]}
          />
        </div>
        <div className="mb-4 flex flex-col md:flex-row gap-3">
          <Input
            placeholder="按标题搜索"
            value={titleKeyword}
            onChange={(e) => setTitleKeyword(e.target.value)}
            allowClear
            className="md:max-w-sm"
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
          pagination={{ pageSize: 8 }}
        />
        <div className="mt-6">
          <Link to="/assets" className="text-emerald-300 hover:text-emerald-200 mr-6">
            前往素材库页面 →
          </Link>
          <Link to="/ai-creator" className="text-indigo-300 hover:text-indigo-200">
            前往 AI 创作工作台 →
          </Link>
        </div>
      </div>
    </div>
  );
}

