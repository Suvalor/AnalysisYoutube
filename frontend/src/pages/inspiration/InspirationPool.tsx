import {
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
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { Lightbulb } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createInspirationApi,
  deleteInspirationApi,
  listInspirationsApi,
  updateInspirationApi,
  type InspirationItem,
} from "@/services/inspirationApi";
import { createScriptApi } from "@/services/libraryApi";
import { useTabStore } from "@/store/useTabStore";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

/** 根据 id 生成稳定的球体位置与大小（轻量布局，无需 D3） */
function bubbleLayout(id: number, contentLen: number) {
  const r1 = ((id * 7919) % 1000) / 1000;
  const r2 = ((id * 4177) % 1000) / 1000;
  const size = 40 + (contentLen % 48);
  return { leftPct: 3 + r1 * 82, topPct: 3 + r2 * 78, size };
}

function isPlotDone(row: InspirationItem) {
  return row.status === "已生成剧情" || (row.plot_id != null && row.plot_id > 0);
}

export default function InspirationPool() {
  const navigate = useNavigate();
  const openTab = useTabStore((s) => s.openTab);
  const [view, setView] = useState<"bubble" | "list">("bubble");
  const [rows, setRows] = useState<InspirationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<InspirationItem | null>(null);
  const [editForm] = Form.useForm();

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

  const goToPlotWorkflow = async (row: InspirationItem) => {
    try {
      const script = await createScriptApi({
        title: `灵感 #${row.id}`,
        content: row.content,
      });
      localStorage.setItem("sop_current_script_id", String(script.id));
      localStorage.setItem("sop_current_script_title", script.title);
      const sopPath = `/sop-workflow?inspirationId=${row.id}`;
      openTab({ id: "sop-workflow", title: "SOP 工作流", path: sopPath, type: "sop-workflow" });
      navigate(sopPath);
      message.success("已跳转剧情拆解，大纲已填入该灵感内容");
    } catch (e: unknown) {
      const d =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      message.error(typeof d === "string" ? d : "创建剧本并跳转失败");
    }
  };

  const onCreate = async () => {
    try {
      const v = await form.validateFields();
      const recorded = v.recorded_at as dayjs.Dayjs | undefined;
      await createInspirationApi({
        content: String(v.content || "").trim(),
        source: String(v.source || "").trim(),
        recorded_at: recorded ? recorded.toISOString() : undefined,
      });
      message.success("灵感已保存");
      form.resetFields();
      form.setFieldsValue({ recorded_at: dayjs() });
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
    editForm.setFieldsValue({
      content: row.content,
      source: row.source,
      recorded_at: dayjs(row.recorded_at),
    });
    setEditOpen(true);
  };

  const submitEdit = async () => {
    if (!editing) return;
    try {
      const v = await editForm.validateFields();
      const recorded = v.recorded_at as dayjs.Dayjs | undefined;
      await updateInspirationApi(editing.id, {
        content: String(v.content || "").trim(),
        source: String(v.source || "").trim(),
        recorded_at: recorded ? recorded.toISOString() : undefined,
      });
      message.success("已更新");
      setEditOpen(false);
      setEditing(null);
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
      title: "内容摘要",
      dataIndex: "content",
      key: "content",
      ellipsis: true,
      render: (t: string) => (
        <Text ellipsis={{ tooltip: t }} className="max-w-[280px]">
          {t}
        </Text>
      ),
    },
    { title: "来源", dataIndex: "source", key: "source", width: 140, ellipsis: true },
    {
      title: "记录时间",
      dataIndex: "recorded_at",
      key: "recorded_at",
      width: 170,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "状态",
      key: "status",
      width: 120,
      render: (_, row) => (
        <Tag color={isPlotDone(row) ? "default" : "processing"}>{row.status}</Tag>
      ),
    },
    {
      title: "剧情 ID",
      dataIndex: "plot_id",
      key: "plot_id",
      width: 90,
      render: (v: number | null) => v ?? "—",
    },
    {
      title: "操作",
      key: "op",
      width: 280,
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
      <Paragraph className="!mb-2 whitespace-pre-wrap">{row.content}</Paragraph>
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
            <h2 className="text-xl font-semibold text-slate-900">灵感池</h2>
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
        <Form
          form={form}
          layout="vertical"
          initialValues={{ recorded_at: dayjs() }}
          className="max-w-3xl"
        >
          <Form.Item
            name="content"
            label="灵感内容（think）"
            rules={[{ required: true, message: "请填写灵感内容" }]}
          >
            <TextArea rows={4} placeholder="写下你的想法…" />
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
              const { leftPct, topPct, size } = bubbleLayout(row.id, row.content.length);
              const done = isPlotDone(row);
              return (
                <Popover key={row.id} title={`灵感 #${row.id}`} content={bubbleContent(row)} trigger="click">
                  <button
                    type="button"
                    className={`absolute rounded-full shadow-md border-2 flex items-center justify-center text-white text-xs font-medium cursor-pointer transition-transform hover:scale-110 hover:z-10 focus:outline-none focus:ring-2 focus:ring-violet-400 ${
                      done
                        ? "bg-slate-400/80 border-slate-300 opacity-75"
                        : "bg-gradient-to-br from-violet-500 to-fuchsia-500 border-white/40"
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
                    {done ? "✓" : "💡"}
                  </button>
                </Popover>
              );
            })}
          </div>
          {rows.some(isPlotDone) ? (
            <div className="mt-2 text-xs text-slate-500">
              灰色球体或带 ✓ 表示已关联剧情拆解；彩色球体为待处理。
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
        }}
        onOk={() => void submitEdit()}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="content" label="灵感内容" rules={[{ required: true }]}>
            <TextArea rows={5} />
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
