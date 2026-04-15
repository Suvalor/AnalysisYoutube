import { Alert, Button, Form, Input, InputNumber, Modal, Popover, Select, Spin, Table, Tag, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import {
  analyzeYouTubeBatchApi,
  batchUpdateChannelsApi,
  deleteYouTubeChannelApi,
  discoverChannelsApi,
  getYouTubeQuotaDashboardApi,
  listYouTubeChannelsApi,
  type DiscoverChannelItem,
  type YouTubeAnalyzeResponse,
} from "@/services/authApi";
import { formatNumber } from "@/utils/format";
import { useTabStore } from "@/store/useTabStore";

dayjs.extend(relativeTime);

type Row = {
  pool_id: number;
  group_name: string;
  added_at: string;
  channel: YouTubeAnalyzeResponse["channel"];
};

type DiscoverFormValues = {
  keyword: string;
  published_after: 7 | 14 | 30;
  max_subscribers: number;
  max_results: number;
};

export default function ChannelList() {
  const PAGE_SIZE = 10;
  const navigate = useNavigate();
  const openTab = useTabStore((s) => s.openTab);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [allRows, setAllRows] = useState<Row[]>([]);
  const [rows, setRows] = useState<Row[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [sortBy, setSortBy] = useState<string>("subscriber_desc");
  const [urls, setUrls] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [discoverItems, setDiscoverItems] = useState<DiscoverChannelItem[]>([]);
  const [discoverWarnings, setDiscoverWarnings] = useState<string[]>([]);
  const [addingDiscoverYtId, setAddingDiscoverYtId] = useState<string | null>(null);
  const [discoverForm] = Form.useForm<DiscoverFormValues>();
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  const monitoredYtIds = useMemo(() => new Set(allRows.map((r) => r.channel.yt_channel_id)), [allRows]);

  const filteredRows = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    if (!kw) return allRows;
    return allRows.filter((item) => {
      const title = item.channel.title?.toLowerCase() ?? "";
      const desc = item.channel.description?.toLowerCase() ?? "";
      const tags = (item.channel.ai_tags ?? []).join(" ").toLowerCase();
      const exp = item.channel.ai_expertise?.toLowerCase() ?? "";
      return title.includes(kw) || desc.includes(kw) || tags.includes(kw) || exp.includes(kw);
    });
  }, [allRows, keyword]);

  const applyPage = useCallback((targetPage: number, source: Row[]) => {
    const safePage = Math.max(1, targetPage);
    const end = safePage * PAGE_SIZE;
    const nextRows = source.slice(0, end);
    setRows(nextRows);
    setCurrentPage(safePage);
    setHasMore(nextRows.length < source.length);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listYouTubeChannelsApi({ sort_by: sortBy });
      const mapped = data.map((x) => ({
        pool_id: x.pool_id,
        group_name: x.group_name,
        added_at: x.added_at,
        channel: x.channel,
      }));
      setAllRows(mapped);
    } catch {
      message.error("加载频道列表失败");
      setAllRows([]);
    } finally {
      setLoading(false);
    }
  }, [sortBy]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    applyPage(1, filteredRows);
  }, [filteredRows, applyPage]);

  const loadNextPage = useCallback(() => {
    if (loading || loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      applyPage(currentPage + 1, filteredRows);
    } finally {
      setLoadingMore(false);
    }
  }, [applyPage, currentPage, filteredRows, hasMore, loading, loadingMore]);

  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting) {
          loadNextPage();
        }
      },
      { root: null, rootMargin: "120px 0px", threshold: 0.1 }
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, [loadNextPage]);

  const onRowClick = (record: Row) => {
    const id = record.channel.id;
    openTab({
      id: `channel-detail-${id}`,
      title: record.channel.title || "博主详情",
      path: `/youtube/channel/${id}`,
      type: "channel-detail",
      channelId: id,
    });
    navigate(`/youtube/channel/${id}`);
  };

  const onBatchAdd = async () => {
    if (!urls.trim()) {
      message.warning("请输入 YouTube 频道链接");
      return;
    }
    setAnalyzing(true);
    message.loading({ content: "正在提交后台任务，请稍候…", key: "yt-add", duration: 0 });
    try {
      await analyzeYouTubeBatchApi({ urls: urls.trim() });
      message.success({ content: "更新任务已提交后台，这可能需要几分钟，请稍后刷新列表查看。", key: "yt-add" });
      setUrls("");
      setKeyword("");
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error({
        content: typeof err.response?.data?.detail === "string" ? err.response.data.detail : "添加失败",
        key: "yt-add",
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const openDiscoverModal = () => {
    setDiscoverItems([]);
    setDiscoverWarnings([]);
    discoverForm.resetFields();
    discoverForm.setFieldsValue({
      keyword: "",
      published_after: 14,
      max_subscribers: 50000,
      max_results: 25,
    });
    setDiscoverOpen(true);
  };

  const onDiscoverSubmit = async (values: DiscoverFormValues) => {
    setDiscoverLoading(true);
    try {
      const data = await discoverChannelsApi({
        keyword: values.keyword.trim(),
        published_after: values.published_after,
        max_subscribers: values.max_subscribers,
        max_results: values.max_results,
      });
      setDiscoverItems(data.items);
      setDiscoverWarnings(data.warnings ?? []);
      if (!data.items.length) {
        message.info("没有符合过滤条件的频道，可尝试放宽粉丝上限或延长发布时间范围");
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error(
        typeof err.response?.data?.detail === "string" ? err.response.data.detail : "挖掘请求失败"
      );
    } finally {
      setDiscoverLoading(false);
    }
  };

  const onDiscoverAddFollow = async (row: DiscoverChannelItem) => {
    if (monitoredYtIds.has(row.yt_channel_id)) {
      message.info("该频道已在关注列表中");
      return;
    }
    setAddingDiscoverYtId(row.yt_channel_id);
    message.loading({ content: "正在提交添加任务…", key: "disc-add", duration: 0 });
    try {
      await analyzeYouTubeBatchApi({ urls: row.channel_url });
      message.success({
        content: "添加任务已提交后台，请稍后刷新列表查看。",
        key: "disc-add",
      });
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error({
        content: typeof err.response?.data?.detail === "string" ? err.response.data.detail : "添加失败",
        key: "disc-add",
      });
    } finally {
      setAddingDiscoverYtId(null);
    }
  };

  const discoverColumns: ColumnsType<DiscoverChannelItem> = [
    {
      title: "频道",
      key: "ch",
      render: (_, r) => (
        <div className="flex items-center gap-2 min-w-0">
          <img src={r.thumbnail_url || ""} alt="" className="w-9 h-9 rounded-full border border-slate-200 shrink-0" />
          <Typography.Text ellipsis={{ tooltip: r.title }} className="font-medium text-slate-900">
            {r.title}
          </Typography.Text>
        </div>
      ),
    },
    {
      title: "订阅数",
      dataIndex: "subscriber_count",
      width: 100,
      render: (v: number) => formatNumber(v),
    },
    {
      title: "总播放量",
      dataIndex: "total_views",
      width: 110,
      render: (v: number) => formatNumber(v),
    },
    {
      title: "频道链接",
      key: "curl",
      width: 88,
      render: (_, r) => (
        <Typography.Link href={r.channel_url} target="_blank" rel="noreferrer">
          打开
        </Typography.Link>
      ),
    },
    {
      title: "爆款视频",
      key: "vurl",
      width: 88,
      render: (_, r) => (
        <Typography.Link href={r.viral_video_url} target="_blank" rel="noreferrer">
          打开
        </Typography.Link>
      ),
    },
    {
      title: "操作",
      key: "op",
      width: 108,
      render: (_, r) => {
        const already = monitoredYtIds.has(r.yt_channel_id);
        return (
          <Button
            type="primary"
            size="small"
            disabled={already}
            loading={addingDiscoverYtId === r.yt_channel_id}
            onClick={() => void onDiscoverAddFollow(r)}
          >
            {already ? "已关注" : "添加关注"}
          </Button>
        );
      },
    },
  ];

  const onBatchUpdate = async () => {
    const q = await getYouTubeQuotaDashboardApi();
    const n = rows.length;
    const estimated = n === 0 ? 0 : Math.floor((n + 49) / 50) + 2 * n;
    Modal.confirm({
      title: "确认一键更新",
      content: `本次预计消耗 API 额度: ${estimated} 点，今日剩余额度: ${q.today_remaining} 点，是否继续？`,
      okText: "继续",
      cancelText: "取消",
      onOk: async () => {
        setUpdating(true);
        message.loading({
          content: "正在同步 YouTube 数据，并对缺少标签的频道执行 AI 补全，请稍候…",
          key: "yt-batch",
          duration: 0,
        });
        try {
          await batchUpdateChannelsApi();
          message.success({ content: "更新任务已提交后台，这可能需要几分钟，请稍后刷新列表查看。", key: "yt-batch" });
          await load();
        } catch (e: unknown) {
          const err = e as { response?: { data?: { detail?: string } } };
          message.error({ content: err.response?.data?.detail ?? "更新失败", key: "yt-batch" });
        } finally {
          setUpdating(false);
        }
      },
    });
  };

  const columns: ColumnsType<Row> = [
    {
      title: "博主",
      key: "title",
      render: (_, r) => (
        <div className="flex items-center gap-2">
          <img src={r.channel.thumbnail_url || ""} alt="" className="w-9 h-9 rounded-full border border-slate-200" />
          <div className="min-w-0">
            <div className="font-medium text-slate-900 truncate">{r.channel.title}</div>
            {r.channel.description?.trim() ? (
              <Popover
                title="频道简介"
                content={
                  <Typography.Paragraph className="!mb-0 max-w-sm whitespace-pre-wrap text-slate-700 text-xs">
                    {r.channel.description}
                  </Typography.Paragraph>
                }
                trigger="click"
              >
                <button
                  type="button"
                  className="text-xs text-blue-600 hover:text-blue-500 truncate max-w-[200px] block text-left"
                  onClick={(e) => e.stopPropagation()}
                >
                  简介预览
                </button>
              </Popover>
            ) : (
              <span className="text-xs text-slate-400">暂无简介</span>
            )}
          </div>
        </div>
      ),
    },
    {
      title: "标签 / 擅长",
      key: "tags_expertise",
      width: 260,
      render: (_, r) => {
        const tags = r.channel.ai_tags ?? [];
        const exp = r.channel.ai_expertise?.trim();
        return (
          <div className="space-y-1" onClick={(e) => e.stopPropagation()}>
            <div className="flex flex-wrap gap-1">
              {tags.length ? (
                tags.map((tag, idx) => (
                  <Tag key={`${tag}-${idx}`} color={["blue", "geekblue", "cyan", "purple", "magenta"][idx % 5]} className="!m-0">
                    {tag}
                  </Tag>
                ))
              ) : (
                <span className="text-xs text-slate-400">待 AI 分析</span>
              )}
            </div>
            {exp ? <div className="text-xs text-slate-600 line-clamp-2 leading-snug">{exp}</div> : null}
          </div>
        );
      },
    },
    {
      title: "订阅数",
      dataIndex: ["channel", "subscriber_count"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: "总播放量",
      dataIndex: ["channel", "total_views"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: "视频数",
      dataIndex: ["channel", "video_count"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: "最后更新时间",
      key: "updated_at",
      dataIndex: ["channel", "updated_at"],
      render: (v: string) => {
        if (!v) return <span className="text-xs text-slate-400">-</span>;
        const dt = dayjs(v);
        return (
          <span title={dt.format("YYYY-MM-DD HH:mm")} className="text-xs text-slate-700">
            {dt.fromNow()}
          </span>
        );
      },
    },
    {
      title: "操作",
      key: "op",
      render: (_, r) => (
        <Button
          size="small"
          danger
          onClick={async (e) => {
            e.stopPropagation();
            await deleteYouTubeChannelApi(r.pool_id);
            message.success("已移除");
            await load();
          }}
        >
          移除
        </Button>
      ),
    },
  ];

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm space-y-2">
        <div className="text-sm text-slate-600">批量录入（分号或换行分隔多个链接）</div>
        <div className="flex flex-col md:flex-row gap-2 md:items-start">
          <Input.TextArea
            rows={3}
            className="max-w-xl"
            placeholder="请输入 YouTube 频道主页链接，支持输入多个，请使用分号 (;) 或换行分隔。例如：https://youtube.com/@a; https://youtube.com/channel/b"
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="primary" loading={analyzing} onClick={() => void onBatchAdd()}>
              添加关注
            </Button>
            <Button type="primary" ghost onClick={openDiscoverModal}>
              🔍 智能挖掘爆款小号
            </Button>
            <Button type="primary" loading={updating} onClick={() => void onBatchUpdate()}>
              一键更新数据
            </Button>
            <Button loading={loading} onClick={() => void load()}>
              刷新列表
            </Button>
          </div>
        </div>
      </div>

      <Spin spinning={loading}>
        <div className="bg-white border border-slate-200 rounded-lg p-2 shadow-sm space-y-2">
          <div className="flex flex-wrap justify-between gap-2 px-2 pt-1">
            <Input
              allowClear
              style={{ width: 320, maxWidth: "100%" }}
              placeholder="搜索频道名 / 简介 / 标签 / 擅长内容"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600 self-center">排序</span>
              <Select
                style={{ width: 220 }}
                value={sortBy}
                onChange={(v) => setSortBy(v)}
                options={[
                  { value: "added_desc", label: "最近添加" },
                  { value: "subscriber_desc", label: "订阅数 ↓" },
                  { value: "subscriber_asc", label: "订阅数 ↑" },
                  { value: "total_views_desc", label: "总播放量 ↓" },
                  { value: "total_views_asc", label: "总播放量 ↑" },
                  { value: "video_count_desc", label: "视频数 ↓" },
                  { value: "video_count_asc", label: "视频数 ↑" },
                ]}
              />
            </div>
          </div>
          <Table<Row>
            rowKey="pool_id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            pagination={false}
            onRow={(record) => ({
              onClick: () => onRowClick(record),
              className: "cursor-pointer hover:bg-slate-50",
            })}
          />
          <div ref={loadMoreRef} className="py-3 text-center text-sm text-slate-500">
            {loadingMore ? "加载中..." : hasMore ? "向下滚动加载更多" : "没有更多数据了"}
          </div>
        </div>
      </Spin>

      <Modal
        title="潜力频道挖掘"
        open={discoverOpen}
        onCancel={() => setDiscoverOpen(false)}
        footer={null}
        width={960}
        destroyOnClose
      >
        <Alert
          type="warning"
          showIcon
          className="mb-3"
          message="每次挖掘会调用 YouTube search.list，约消耗 100 点 API 配额（另加 channels.list 分块费用）。请控制使用频率。"
        />
        <Spin spinning={discoverLoading}>
          <Form<DiscoverFormValues>
            form={discoverForm}
            layout="vertical"
            className="mb-4"
            initialValues={{ published_after: 14, max_subscribers: 50000, max_results: 25 }}
            onFinish={(v) => void onDiscoverSubmit(v)}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4">
              <Form.Item
                name="keyword"
                label="搜索关键词"
                rules={[{ required: true, message: "请输入关键词" }]}
              >
                <Input allowClear placeholder="例如：健身教程、AI 工具评测" maxLength={200} />
              </Form.Item>
              <Form.Item name="published_after" label="发布时间范围（自现在起）">
                <Select
                  options={[
                    { value: 7, label: "近 7 天" },
                    { value: 14, label: "近 14 天" },
                    { value: 30, label: "近 30 天" },
                  ]}
                />
              </Form.Item>
              <Form.Item name="max_subscribers" label="粉丝上限（保留订阅数小于该值的频道）">
                <InputNumber min={0} max={999999999} className="w-full" />
              </Form.Item>
              <Form.Item name="max_results" label="search 抓取条数（1–50）">
                <InputNumber min={1} max={50} className="w-full" />
              </Form.Item>
            </div>
            <Button type="primary" htmlType="submit" loading={discoverLoading}>
              开始挖掘
            </Button>
          </Form>

          {discoverWarnings.length > 0 ? (
            <Alert
              type="info"
              showIcon
              className="mb-3"
              message="部分条目已跳过"
              description={
                <ul className="list-disc pl-4 mb-0 text-sm">
                  {discoverWarnings.slice(0, 8).map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              }
            />
          ) : null}

          <div className="text-sm text-slate-600 mb-2">挖掘结果（未写入数据库，点击「添加关注」后才会入库）</div>
          <Table<DiscoverChannelItem>
            rowKey="yt_channel_id"
            size="small"
            columns={discoverColumns}
            dataSource={discoverItems}
            pagination={false}
            locale={{ emptyText: discoverLoading ? "加载中…" : "暂无数据，请先填写表单并点击「开始挖掘」" }}
          />
        </Spin>
      </Modal>
    </div>
  );
}
