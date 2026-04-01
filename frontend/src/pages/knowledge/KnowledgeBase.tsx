import { Button, Input, Select, Table, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listScriptsApi, type ScriptItem } from "@/services/libraryApi";

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

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      try {
        const data = await listScriptsApi();
        if (!mounted) return;
        setRows(data);
      } catch (e: any) {
        if (!mounted) return;
        message.error(e?.response?.data?.detail ?? e?.message ?? "加载剧本列表失败");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

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
      width: 180,
      render: (_, row) => (
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
      ),
    },
  ];

  const filteredRows = useMemo(() => {
    const kw = titleKeyword.trim().toLowerCase();
    return rows.filter((row) => {
      const titleOk = !kw || row.title.toLowerCase().includes(kw);
      const status = getScriptStatus(row);
      const statusOk = statusFilter === "all" || status === statusFilter;
      return titleOk && statusOk;
    });
  }, [rows, titleKeyword, statusFilter]);

  return (
    <div className="p-6 md:p-10">
      <div className="max-w-6xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-2 text-slate-900">知识库管理</h2>
        <p className="text-slate-600 mb-4">在此查看已保存剧本，并从任意剧本继续进入 SOP 下一步。</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
            <h3 className="font-medium mb-1">提示词库</h3>
            <p className="text-sm text-slate-500">接口：`/api/libraries/prompts`</p>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
            <h3 className="font-medium mb-1">风格库</h3>
            <p className="text-sm text-slate-500">接口：`/api/libraries/styles`</p>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
            <h3 className="font-medium mb-1">素材库</h3>
            <p className="text-sm text-slate-500">接口：`/api/libraries/assets`</p>
          </div>
        </div>
        <div className="mb-4 flex flex-col md:flex-row gap-3">
          <Input
            placeholder="按标题搜索"
            value={titleKeyword}
            onChange={(e) => setTitleKeyword(e.target.value)}
            allowClear
            className="md:max-w-sm"
          />
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

