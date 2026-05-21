import { Alert, Button, Drawer, Form, Input, InputNumber, Modal, Popconfirm, Popover, Select, Spin, Table, Tag, Tooltip, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import {
  analyzeYouTubeBatchApi,
  batchUpdateChannelsApi,
  blueOceanRadarApi,
  deleteYouTubeChannelApi,
  discoverChannelsApi,
  discoverChannelDetailApi,
  getYouTubeQuotaDashboardApi,
  listYouTubeChannelsApi,
  type BlueOceanChannelItem,
  type ChannelDetailResponse,
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

type BlueOceanFormValues = {
  keyword: string;
  published_after: number;
  max_subscribers: number;
  outlier_multiplier: number;
  video_duration: string;
};

export default function ChannelList() {
  const { t } = useTranslation("youtube");
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
  const [blueOceanOpen, setBlueOceanOpen] = useState(false);
  const [blueOceanLoading, setBlueOceanLoading] = useState(false);
  const [blueOceanItems, setBlueOceanItems] = useState<BlueOceanChannelItem[]>([]);
  const [blueOceanWarnings, setBlueOceanWarnings] = useState<string[]>([]);
  const [addingBlueOceanYtId, setAddingBlueOceanYtId] = useState<string | null>(null);
  const [followedBlueOceanIds, setFollowedBlueOceanIds] = useState<Set<string>>(new Set());
  const [blueOceanForm] = Form.useForm<BlueOceanFormValues>();
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  /** 频道详情 Drawer 状态 */
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [channelDetail, setChannelDetail] = useState<ChannelDetailResponse | null>(null);

  /** 打开频道详情 Drawer，调用后端缓存增强接口 */
  const handleViewDetail = useCallback(async (channelId: string) => {
    setDetailVisible(true);
    setDetailLoading(true);
    setDetailError(null);
    setChannelDetail(null);
    try {
      const data = await discoverChannelDetailApi(channelId);
      setChannelDetail(data);
    } catch {
      setDetailError(t("message.detailLoadFailed"));
    } finally {
      setDetailLoading(false);
    }
  }, [t]);

  /** 关闭频道详情 Drawer */
  const handleCloseDetail = useCallback(() => {
    setDetailVisible(false);
    setChannelDetail(null);
    setDetailError(null);
  }, []);

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
      message.error(t("message.loadFailed"));
      setAllRows([]);
    } finally {
      setLoading(false);
    }
  }, [t, sortBy]);

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
      title: record.channel.title || t("title.bloggerDetail"),
      path: `/youtube/channel/${id}`,
      type: "channel-detail",
      channelId: id,
    });
    navigate(`/youtube/channel/${id}`);
  };

  const onBatchAdd = async () => {
    if (!urls.trim()) {
      message.warning(t("message.urlRequired"));
      return;
    }
    setAnalyzing(true);
    message.loading({ content: t("message.submittingBackground"), key: "yt-add", duration: 0 });
    try {
      await analyzeYouTubeBatchApi({ urls: urls.trim() });
      message.success({ content: t("message.batchAddSuccess"), key: "yt-add" });
      setUrls("");
      setKeyword("");
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error({
        content: typeof err.response?.data?.detail === "string" ? err.response.data.detail : t("message.addFailed"),
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
      max_results: 50,
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
        message.info(t("message.noDiscoverResults"));
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error(
        typeof err.response?.data?.detail === "string" ? err.response.data.detail : t("message.discoverFailed")
      );
    } finally {
      setDiscoverLoading(false);
    }
  };

  const onDiscoverAddFollow = async (row: DiscoverChannelItem) => {
    if (monitoredYtIds.has(row.yt_channel_id)) {
      message.info(t("message.alreadyFollowed"));
      return;
    }
    setAddingDiscoverYtId(row.yt_channel_id);
    message.loading({ content: t("message.submittingAdd"), key: "disc-add", duration: 0 });
    try {
      await analyzeYouTubeBatchApi({ urls: row.channel_url });
      message.success({
        content: t("message.addTaskSubmitted"),
        key: "disc-add",
      });
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error({
        content: typeof err.response?.data?.detail === "string" ? err.response.data.detail : t("message.addFailed"),
        key: "disc-add",
      });
    } finally {
      setAddingDiscoverYtId(null);
    }
  };

  const openBlueOceanDrawer = () => {
    setBlueOceanItems([]);
    setBlueOceanWarnings([]);
    setFollowedBlueOceanIds(new Set());
    blueOceanForm.resetFields();
    blueOceanForm.setFieldsValue({
      keyword: "",
      published_after: 90,
      max_subscribers: 30000,
      outlier_multiplier: 10,
      video_duration: "long",
    });
    setBlueOceanOpen(true);
  };

  const onBlueOceanSubmit = async (values: BlueOceanFormValues) => {
    setBlueOceanLoading(true);
    try {
      const data = await blueOceanRadarApi({
        keyword: values.keyword.trim(),
        published_after: values.published_after,
        max_subscribers: values.max_subscribers,
        outlier_multiplier: values.outlier_multiplier,
        video_duration: values.video_duration,
      });
      setBlueOceanItems(data.items);
      setBlueOceanWarnings(data.warnings ?? []);
      if (!data.items.length) {
        message.info(t("message.noBlueOceanResults"));
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error(
        typeof err.response?.data?.detail === "string" ? err.response.data.detail : t("message.blueOceanScanFailed")
      );
    } finally {
      setBlueOceanLoading(false);
    }
  };

  const onBlueOceanAddFollow = async (row: BlueOceanChannelItem) => {
    if (monitoredYtIds.has(row.yt_channel_id) || followedBlueOceanIds.has(row.yt_channel_id)) {
      message.info(t("message.alreadyFollowed"));
      return;
    }
    setAddingBlueOceanYtId(row.yt_channel_id);
    message.loading({ content: t("message.submittingImport"), key: "bo-add", duration: 0 });
    try {
      await analyzeYouTubeBatchApi({ urls: row.channel_url });
      message.success({ content: t("message.importTaskSubmitted"), key: "bo-add" });
      setFollowedBlueOceanIds((prev) => new Set(prev).add(row.yt_channel_id));
      await load();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } } };
      message.error({
        content: typeof err.response?.data?.detail === "string" ? err.response.data.detail : t("message.importFailed"),
        key: "bo-add",
      });
    } finally {
      setAddingBlueOceanYtId(null);
    }
  };

  const blueOceanColumns: ColumnsType<BlueOceanChannelItem> = [
    {
      title: t("table.channelInfo"),
      key: "ch",
      width: 220,
      render: (_, r) => (
        <div className="flex items-center gap-2 min-w-0">
          <img
            src={r.avatar_url || r.thumbnail_url || ""}
            alt={r.title}
            className="w-9 h-9 rounded-full border border-yc-border shrink-0 object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
          <div className="min-w-0">
            <Typography.Link
              onClick={() => handleViewDetail(r.yt_channel_id)}
              className="font-medium text-yc-text-primary"
            >
              {r.title}
            </Typography.Link>
            {r.description && (
              <Tooltip title={r.description} placement="topLeft">
                <div className="text-xs text-yc-text-secondary mt-0.5 truncate max-w-[200px]">
                  {r.description}
                </div>
              </Tooltip>
            )}
            {r.channel_created_at && (
              <div className="text-xs text-yc-text-secondary mt-0.5">
                {t("table.createdAgo", { time: dayjs(r.channel_created_at).fromNow() })}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      title: t("table.subscribers"),
      dataIndex: "subscriber_count",
      width: 100,
      sorter: (a, b) => a.subscriber_count - b.subscriber_count,
      render: (v: number) => formatNumber(v),
    },
    {
      title: t("table.channelTotalViews"),
      dataIndex: "channel_total_views",
      width: 120,
      sorter: (a, b) => a.channel_total_views - b.channel_total_views,
      render: (v: number) => formatNumber(v),
    },
    {
      title: t("table.videos"),
      dataIndex: "video_count",
      width: 90,
      sorter: (a, b) => (a.video_count ?? 0) - (b.video_count ?? 0),
      render: (v: number) => formatNumber(v ?? 0),
    },
    {
      title: t("table.avgViews"),
      dataIndex: "avg_views_per_video",
      width: 100,
      sorter: (a, b) => (a.avg_views_per_video ?? 0) - (b.avg_views_per_video ?? 0),
      render: (v: number) => formatNumber(Math.round(v ?? 0)),
    },
    {
      title: t("table.viralVideo"),
      key: "vurl",
      width: 180,
      render: (_, r) => (
        <div className="flex flex-col leading-tight">
          <Typography.Link href={r.viral_video_url} target="_blank" rel="noreferrer">
            {t("action.openVideo")}
          </Typography.Link>
          <span className="text-xs text-yc-text-secondary">{t("table.views")}{formatNumber(r.trigger_video_views)}</span>
        </div>
      ),
    },
    {
      title: t("table.outlierScore"),
      dataIndex: "outlier_score",
      width: 110,
      defaultSortOrder: "descend" as const,
      sorter: (a, b) => a.outlier_score - b.outlier_score,
      render: (v: number) => (
        <Tag color={v >= 50 ? "red" : v >= 20 ? "orange" : "blue"} className="font-mono font-semibold text-sm">
          {v.toFixed(1)}x
        </Tag>
      ),
    },
    {
      title: t("table.action"),
      key: "op",
      width: 110,
      render: (_, r) => {
        const already = monitoredYtIds.has(r.yt_channel_id) || followedBlueOceanIds.has(r.yt_channel_id);
        return (
          <Button
            type="primary"
            size="small"
            disabled={already}
            loading={addingBlueOceanYtId === r.yt_channel_id}
            onClick={() => void onBlueOceanAddFollow(r)}
          >
            {already ? t("action.followed") : t("action.importFollow")}
          </Button>
        );
      },
    },
  ];

  /** discoverColumns — 频道卡片富化版 */
  const discoverColumns: ColumnsType<DiscoverChannelItem> = useMemo(
    () => [
      {
        title: t("table.channel"),
        key: "ch",
        width: 280,
        render: (_, r) => (
          <div className="flex items-start gap-2 min-w-0">
            <img
              src={r.avatar_url || r.thumbnail_url || ""}
              alt={r.title}
              className="w-10 h-10 rounded-full border border-yc-border shrink-0 object-cover"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
            <div className="min-w-0 flex-1">
              <Typography.Link
                onClick={() => handleViewDetail(r.yt_channel_id)}
                className="font-medium text-yc-text-primary"
              >
                {r.title}
              </Typography.Link>
              {r.description && (
                <Tooltip title={r.description} placement="topLeft">
                  <div className="text-xs text-yc-text-secondary mt-0.5 truncate max-w-[200px]">
                    {r.description}
                  </div>
                </Tooltip>
              )}
              {r.published_at && (
                <div className="text-xs text-yc-text-secondary mt-0.5">
                  {t("table.createdAgo", { time: dayjs(r.published_at).fromNow() })}
                </div>
              )}
            </div>
          </div>
        ),
      },
      {
        title: t("table.subscribers"),
        dataIndex: "subscriber_count",
        width: 100,
        sorter: (a, b) => a.subscriber_count - b.subscriber_count,
        render: (v: number) => formatNumber(v),
      },
      {
        title: t("table.videos"),
        dataIndex: "video_count",
        width: 90,
        sorter: (a, b) => (a.video_count ?? 0) - (b.video_count ?? 0),
        render: (v: number) => formatNumber(v),
      },
      {
        title: t("table.totalViews"),
        dataIndex: "channel_total_views",
        width: 110,
        sorter: (a, b) => a.channel_total_views - b.channel_total_views,
        render: (v: number) => formatNumber(v),
      },
      {
        title: t("table.avgViews"),
        dataIndex: "avg_views_per_video",
        width: 100,
        sorter: (a, b) => (a.avg_views_per_video ?? 0) - (b.avg_views_per_video ?? 0),
        render: (v: number) => formatNumber(Math.round(v ?? 0)),
      },
      {
        title: t("table.viralViews"),
        dataIndex: "trigger_video_views",
        width: 140,
        sorter: (a, b) => a.trigger_video_views - b.trigger_video_views,
        render: (v: number, r) => (
          <div>
            <span className="font-semibold text-orange-500">{formatNumber(v)}</span>
            {r.trigger_video_title && (
              <Tooltip title={r.trigger_video_title} placement="topLeft">
                <div className="text-xs text-yc-text-secondary mt-0.5 truncate max-w-[120px]">
                  {r.trigger_video_title}
                </div>
              </Tooltip>
            )}
          </div>
        ),
      },
      {
        title: t("table.links"),
        key: "links",
        width: 120,
        render: (_, r) => (
          <div className="flex flex-col gap-1">
            <Typography.Link href={r.channel_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
              {t("action.channel")}
            </Typography.Link>
            <Typography.Link href={r.viral_video_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
              {t("table.viralVideo")}
            </Typography.Link>
          </div>
        ),
      },
      {
        title: t("table.action"),
        key: "op",
        width: 100,
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
              {already ? t("action.followed") : t("action.addFollow")}
            </Button>
          );
        },
      },
    ],
    [handleViewDetail, monitoredYtIds, addingDiscoverYtId],
  );

  const onBatchUpdate = async () => {
    const q = await getYouTubeQuotaDashboardApi();
    const n = rows.length;
    const estimated = n === 0 ? 0 : Math.floor((n + 49) / 50) + 2 * n;
    Modal.confirm({
      title: t("modal.confirmBatchUpdate"),
      content: t("modal.batchUpdateContent", { estimated, remaining: q.today_remaining }),
      okText: t("action.continue"),
      cancelText: t("modal.cancel"),
      onOk: async () => {
        setUpdating(true);
        message.loading({
          content: t("message.syncingData"),
          key: "yt-batch",
          duration: 0,
        });
        try {
          await batchUpdateChannelsApi();
          message.success({ content: t("message.updateTaskSubmitted"), key: "yt-batch" });
          await load();
        } catch (e: unknown) {
          const err = e as { response?: { data?: { detail?: string } } };
          message.error({ content: err.response?.data?.detail ?? t("message.updateFailed"), key: "yt-batch" });
        } finally {
          setUpdating(false);
        }
      },
    });
  };

  const columns: ColumnsType<Row> = [
    {
      title: t("table.blogger"),
      key: "title",
      render: (_, r) => (
        <div className="flex items-center gap-2">
          <img src={r.channel.thumbnail_url || ""} alt="" className="w-9 h-9 rounded-full border border-yc-border" />
          <div className="min-w-0">
            <div className="font-medium text-yc-text-primary truncate">{r.channel.title}</div>
            {r.channel.description?.trim() ? (
              <Popover
                title={t("popover.channelDesc")}
                content={
                  <Typography.Paragraph className="!mb-0 max-w-sm whitespace-pre-wrap text-yc-text-secondary text-xs">
                    {r.channel.description}
                  </Typography.Paragraph>
                }
                trigger="click"
              >
                <button
                  type="button"
                  className="text-xs text-yc-info hover:text-yc-primary-hover truncate max-w-[200px] block text-left"
                  onClick={(e) => e.stopPropagation()}
                >
                  {t("action.descPreview")}
                </button>
              </Popover>
            ) : (
              <span className="text-xs text-yc-text-tertiary">{t("empty.noDesc")}</span>
            )}
          </div>
        </div>
      ),
    },
    {
      title: t("table.tagsExpertise"),
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
                <span className="text-xs text-yc-text-tertiary">{t("tag.pendingAi")}</span>
              )}
            </div>
            {exp ? <div className="text-xs text-yc-text-secondary line-clamp-2 leading-snug">{exp}</div> : null}
          </div>
        );
      },
    },
    {
      title: t("table.subscribers"),
      dataIndex: ["channel", "subscriber_count"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: t("table.totalViews"),
      dataIndex: ["channel", "total_views"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: t("table.videos"),
      dataIndex: ["channel", "video_count"],
      render: (v: number) => formatNumber(v),
    },
    {
      title: t("table.lastUpdated"),
      key: "updated_at",
      dataIndex: ["channel", "updated_at"],
      render: (v: string) => {
        if (!v) return <span className="text-xs text-yc-text-tertiary">-</span>;
        const dt = dayjs(v);
        return (
          <span title={dt.format("YYYY-MM-DD HH:mm")} className="text-xs text-yc-text-secondary">
            {dt.fromNow()}
          </span>
        );
      },
    },
    {
      title: t("table.action"),
      key: "op",
      render: (_, r) => (
        <Popconfirm
          title={t("modal.confirmRemove")}
          description={t("modal.removeWarning")}
          onConfirm={async () => {
            await deleteYouTubeChannelApi(r.pool_id);
            message.success(t("message.removed"));
            await load();
          }}
          okText={t("modal.confirm")}
          cancelText={t("modal.cancel")}
        >
          <Button size="small" danger onClick={(e) => e.stopPropagation()}>
            {t("action.remove")}
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="bg-yc-bg-card border border-yc-border rounded-lg p-4 shadow-sm space-y-2">
        <div className="text-sm text-yc-text-secondary">{t("desc.batchInput")}</div>
        <div className="flex flex-col md:flex-row gap-2 md:items-start">
          <Input.TextArea
            rows={3}
            className="max-w-xl"
            placeholder={t("form.urlPlaceholder")}
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="primary" loading={analyzing} onClick={() => void onBatchAdd()}>
              {t("action.addFollow")}
            </Button>
            <Button type="primary" ghost onClick={openDiscoverModal}>
              {t("action.smartDiscover")}
            </Button>
            <Button type="primary" onClick={openBlueOceanDrawer}>
              {t("action.blueOceanDiscover")}
            </Button>
            <Button type="primary" loading={updating} onClick={() => void onBatchUpdate()}>
              {t("action.batchUpdate")}
            </Button>
            <Button loading={loading} onClick={() => void load()}>
              {t("action.refreshList")}
            </Button>
          </div>
        </div>
      </div>

      <Spin spinning={loading}>
        <div className="bg-yc-bg-card border border-yc-border rounded-lg p-2 shadow-sm space-y-2">
          <div className="flex flex-wrap justify-between gap-2 px-2 pt-1">
            <Input
              allowClear
              style={{ width: 320, maxWidth: "100%" }}
              placeholder={t("form.searchPlaceholder")}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <span className="text-sm text-yc-text-secondary self-center">{t("form.sort")}</span>
              <Select
                style={{ width: 220 }}
                value={sortBy}
                onChange={(v) => setSortBy(v)}
                options={[
                  { value: "added_desc", label: t("option.recentlyAdded") },
                  { value: "subscriber_desc", label: `${t("table.subscribers")} ↓` },
                  { value: "subscriber_asc", label: `${t("table.subscribers")} ↑` },
                  { value: "total_views_desc", label: `${t("table.totalViews")} ↓` },
                  { value: "total_views_asc", label: `${t("table.totalViews")} ↑` },
                  { value: "video_count_desc", label: `${t("table.videos")} ↓` },
                  { value: "video_count_asc", label: `${t("table.videos")} ↑` },
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
              className: "cursor-pointer hover:bg-yc-bg-inset",
            })}
          />
          <div ref={loadMoreRef} className="py-3 text-center text-sm text-yc-text-tertiary">
            {loadingMore ? t("empty.loading") : hasMore ? t("empty.scrollMore") : t("empty.noMore")}
          </div>
        </div>
      </Spin>

      <Modal
        title={t("modal.discoverTitle")}
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
          message={t("desc.quotaWarning")}
        />
        <Spin spinning={discoverLoading}>
          <Form<DiscoverFormValues>
            form={discoverForm}
            layout="vertical"
            className="mb-4"
            initialValues={{ published_after: 14, max_subscribers: 50000, max_results: 50 }}
            onFinish={(v) => void onDiscoverSubmit(v)}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4">
              <Form.Item
                name="keyword"
                label={t("form.keyword")}
                rules={[{ required: true, message: t("form.keywordRequired") }]}
              >
                <Input allowClear placeholder={t("form.keywordPlaceholder")} maxLength={200} />
              </Form.Item>
              <Form.Item name="published_after" label={t("form.publishedAfter")}>
                <Select
                  options={[
                    { value: 7, label: t("option.last7Days") },
                    { value: 14, label: t("option.last14Days") },
                    { value: 30, label: t("option.last30Days") },
                  ]}
                />
              </Form.Item>
              <Form.Item name="max_subscribers" label={t("form.maxSubscribers")}>
                <InputNumber min={0} max={999999999} className="w-full" />
              </Form.Item>
              <Form.Item name="max_results" label={t("form.maxResults")}>
                <InputNumber min={1} max={50} className="w-full" />
              </Form.Item>
            </div>
            <Button type="primary" htmlType="submit" loading={discoverLoading}>
              {t("action.startDiscover")}
            </Button>
          </Form>

          {discoverWarnings.length > 0 ? (
            <Alert
              type="info"
              showIcon
              className="mb-3"
              message={t("message.partialSkipped")}
              description={
                <ul className="list-disc pl-4 mb-0 text-sm">
                  {discoverWarnings.slice(0, 8).map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              }
            />
          ) : null}

          <div className="text-sm text-yc-text-secondary mb-2">{t("desc.discoverResult")}</div>
          <Table<DiscoverChannelItem>
            rowKey="yt_channel_id"
            size="small"
            columns={discoverColumns}
            dataSource={discoverItems}
            pagination={false}
            locale={{ emptyText: discoverLoading ? t("empty.loading") : t("empty.discoverNoData") }}
          />
        </Spin>
      </Modal>

      <Drawer
        title={t("modal.blueOceanTitle")}
        open={blueOceanOpen}
        onClose={() => setBlueOceanOpen(false)}
        width={980}
        destroyOnClose
      >
        <Alert
          type="info"
          showIcon
          className="mb-4"
          message={t("desc.blueOceanInfo")}
        />
        <Spin spinning={blueOceanLoading}>
          <Form<BlueOceanFormValues>
            form={blueOceanForm}
            layout="vertical"
            className="mb-4"
            initialValues={{
              published_after: 90,
              max_subscribers: 30000,
              outlier_multiplier: 10,
              video_duration: "long",
            }}
            onFinish={(v) => void onBlueOceanSubmit(v)}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4">
              <Form.Item
                name="keyword"
                label={t("form.keyword")}
                rules={[{ required: true, message: t("form.keywordRequired") }]}
              >
                <Input allowClear placeholder={t("form.blueOceanKeywordPlaceholder")} maxLength={200} />
              </Form.Item>
              <Form.Item name="published_after" label={t("form.publishedAfter")}>
                <Select
                  options={[
                    { value: 30, label: t("option.last1Month") },
                    { value: 90, label: t("option.last3Months") },
                    { value: 180, label: t("option.lastHalfYear") },
                  ]}
                />
              </Form.Item>
              <Form.Item name="max_subscribers" label={t("form.maxSubscribersLimit")}>
                <InputNumber min={0} max={999999999} className="w-full" />
              </Form.Item>
              <Form.Item name="outlier_multiplier" label={t("form.outlierMultiplierDesc")}>
                <InputNumber min={1} max={10000} step={1} className="w-full" />
              </Form.Item>
              <Form.Item name="video_duration" label={t("form.videoDuration")}>
                <Select
                  options={[
                    { value: "long", label: t("option.longVideo") },
                    { value: "medium", label: t("option.mediumVideo") },
                    { value: "short", label: t("option.shortVideo") },
                    { value: "any", label: t("option.anyDuration") },
                  ]}
                />
              </Form.Item>
            </div>
            <Button type="primary" htmlType="submit" loading={blueOceanLoading}>
              {t("action.startDeepScan")}
            </Button>
          </Form>

          {blueOceanWarnings.length > 0 && (
            <Alert
              type="warning"
              showIcon
              className="mb-3"
              message={t("message.partialSkipped")}
              description={
                <ul className="list-disc pl-4 mb-0 text-sm">
                  {blueOceanWarnings.slice(0, 8).map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              }
            />
          )}

          <div className="text-sm text-slate-600 mb-2">
            {t("desc.blueOceanResult")}
            {blueOceanItems.length > 0 && (
              <span className="ml-2 text-slate-400">{t("desc.blueOceanCount", { count: blueOceanItems.length })}</span>
            )}
          </div>
          <Table<BlueOceanChannelItem>
            rowKey="yt_channel_id"
            size="small"
            columns={blueOceanColumns}
            dataSource={blueOceanItems}
            pagination={blueOceanItems.length > 10 ? { pageSize: 10 } : false}
            locale={{
              emptyText: blueOceanLoading ? t("empty.scanning") : t("empty.blueOceanNoData"),
            }}
          />
        </Spin>
      </Drawer>

      {/* 频道详情 Drawer */}
      <Drawer
        title={t("modal.channelDetail")}
        open={detailVisible}
        onClose={handleCloseDetail}
        width={480}
        destroyOnClose
      >
        {detailLoading && !channelDetail ? (
          <div className="flex items-center justify-center py-16">
            <Spin size="large" />
          </div>
        ) : detailError ? (
          <Alert
            type="error"
            showIcon
            message={t("message.loadFailed")}
            description={detailError}
            className="mb-4"
          />
        ) : channelDetail ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              {channelDetail.avatar_url && (
                <img
                  src={channelDetail.avatar_url}
                  alt={channelDetail.title}
                  className="w-12 h-12 rounded-full border border-yc-border object-cover"
                />
              )}
              <div>
                <div className="font-semibold text-yc-text-primary text-lg">{channelDetail.title}</div>
                {channelDetail.custom_url && (
                  <Typography.Text type="secondary" className="text-xs">
                    {channelDetail.custom_url}
                  </Typography.Text>
                )}
              </div>
            </div>
            {channelDetail.description && (
              <div>
                <div className="text-sm font-medium text-yc-text-secondary mb-1">{t("label.channelDesc")}</div>
                <Typography.Paragraph className="text-sm text-yc-text-primary whitespace-pre-wrap">
                  {channelDetail.description}
                </Typography.Paragraph>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-yc-bg-inset rounded-lg p-3">
                <div className="text-xs text-yc-text-secondary">{t("table.subscribers")}</div>
                <div className="font-semibold text-yc-text-primary">{formatNumber(channelDetail.subscriber_count)}</div>
              </div>
              <div className="bg-yc-bg-inset rounded-lg p-3">
                <div className="text-xs text-yc-text-secondary">{t("table.videos")}</div>
                <div className="font-semibold text-yc-text-primary">{formatNumber(channelDetail.video_count)}</div>
              </div>
              <div className="bg-yc-bg-inset rounded-lg p-3">
                <div className="text-xs text-yc-text-secondary">{t("table.totalViews")}</div>
                <div className="font-semibold text-yc-text-primary">{formatNumber(channelDetail.view_count)}</div>
              </div>
              <div className="bg-yc-bg-inset rounded-lg p-3">
                <div className="text-xs text-yc-text-secondary">{t("table.createdAt")}</div>
                <div className="font-semibold text-yc-text-primary">
                  {channelDetail.published_at ? dayjs(channelDetail.published_at).format("YYYY-MM-DD") : "-"}
                </div>
              </div>
            </div>
            {channelDetail.country && (
              <div className="text-sm text-yc-text-secondary">
                {t("label.countryRegion")}{channelDetail.country}
              </div>
            )}
          </div>
        ) : (
          <div className="text-center text-yc-text-tertiary py-8">{t("empty.noData")}</div>
        )}
      </Drawer>
    </div>
  );
}
