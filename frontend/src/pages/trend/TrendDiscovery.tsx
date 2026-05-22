import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { buildYouTubeWatchUrl } from "@/utils/youtubeLinks";
import {
  Card,
  Select,
  Button,
  Tag,
  Statistic,
  Row,
  Col,
  Typography,
  Space,
  Image,
  Tooltip,
  Empty,
  message,
  Modal,
  Spin,
} from "antd";
import {
  FireOutlined,
  GlobalOutlined,
  EyeOutlined,
  LikeOutlined,
  MessageOutlined,
  RiseOutlined,
  PlusOutlined,
  HistoryOutlined,
  CaretUpOutlined,
  CaretDownOutlined,
} from "@ant-design/icons";
import {
  trendDiscoveryApi,
  trendHistoryApi,
  trendCacheApi,
  addChannelByIdApi,
  type TrendHistoryItem,
  type TrendDiscoveryResponse,
} from "@/services/authApi";
import { useAuth } from "@/store/authStore";

const { Title, Text } = Typography;

// REGION_OPTIONS moved to component-level useMemo

// CATEGORY_OPTIONS moved to component-level useMemo

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

/** 根据{t('discovery.region')}代码获取{t('discovery.region')}标签 */
function getRegionLabel(region: string): string {
  const map: Record<string, string> = {
    US: "discovery.regionUS", GB: "discovery.regionGB", JP: "discovery.regionJP", KR: "discovery.regionKR",
    DE: "discovery.regionDE", FR: "discovery.regionFR", BR: "discovery.regionBR", IN: "discovery.regionIN",
    CA: "discovery.regionCA", AU: "discovery.regionAU",
  };
  return map[region] || region;
}

/** 根据{t('discovery.category')} ID 获取{t('discovery.category')}标签 */
function getCategoryLabel(categoryId: string): string {
  const map: Record<string, string> = {
    "": "discovery.allCategories", "1": "discovery.catFilm", "2": "discovery.catAutos", "10": "discovery.catMusic",
    "15": "discovery.catAnimals", "17": "discovery.catSports", "20": "discovery.catGaming", "22": "discovery.catPeople",
    "23": "discovery.catComedy", "24": "discovery.catEntertainment", "25": "discovery.catNews", "26": "discovery.catHowto",
    "27": "discovery.catEducation", "28": "discovery.catScience",
  };
  return map[categoryId] || categoryId || "discovery.allCategories";
}

function SortHeader({
  label,
  field,
  current,
  order,
  onSort,
}: {
  label: string;
  field: string;
  current: string;
  order: "asc" | "desc";
  onSort: (f: any) => void;
}) {
  const active = current === field;
  return (
    <div
      onClick={() => onSort(field)}
      style={{ cursor: "pointer", userSelect: "none", display: "flex", alignItems: "center", gap: 2 }}
    >
      {label}
      <span style={{ fontSize: 10, display: "inline-flex", flexDirection: "column", lineHeight: 1 }}>
        <CaretUpOutlined style={{ color: active && order === "asc" ? "var(--color-primary)" : "var(--color-text-tertiary)", fontSize: 9 }} />
        <CaretDownOutlined style={{ color: active && order === "desc" ? "var(--color-primary)" : "var(--color-text-tertiary)", fontSize: 9, marginTop: -3 }} />
      </span>
    </div>
  );
}

export default function TrendDiscovery() {
  const { t } = useTranslation("trend");
  const { token } = useAuth();

  /** {t('discovery.region')}选项（i18n） */
  const REGION_OPTIONS = useMemo(() => [
    { value: "US", label: `🇺🇸 ${t('discovery.regionUS')}` },
    { value: "GB", label: `🇬🇧 ${t('discovery.regionGB')}` },
    { value: "JP", label: `🇯🇵 ${t('discovery.regionJP')}` },
    { value: "KR", label: `🇰🇷 ${t('discovery.regionKR')}` },
    { value: "DE", label: `🇩🇪 ${t('discovery.regionDE')}` },
    { value: "FR", label: `🇫🇷 ${t('discovery.regionFR')}` },
    { value: "BR", label: `🇧🇷 ${t('discovery.regionBR')}` },
    { value: "IN", label: `🇮🇳 ${t('discovery.regionIN')}` },
    { value: "CA", label: `🇨🇦 ${t('discovery.regionCA')}` },
    { value: "AU", label: `🇦🇺 ${t('discovery.regionAU')}` },
  ], [t]);

  /** {t('discovery.category')}选项（i18n） */
  const CATEGORY_OPTIONS = useMemo(() => [
    { value: "", label: t('discovery.allCategories') },
    { value: "1", label: t('discovery.catFilm') },
    { value: "2", label: t('discovery.catAutos') },
    { value: "10", label: t('discovery.catMusic') },
    { value: "15", label: t('discovery.catAnimals') },
    { value: "17", label: t('discovery.catSports') },
    { value: "20", label: t('discovery.catGaming') },
    { value: "22", label: t('discovery.catPeople') },
    { value: "23", label: t('discovery.catComedy') },
    { value: "24", label: t('discovery.catEntertainment') },
    { value: "25", label: t('discovery.catNews') },
    { value: "26", label: t('discovery.catHowto') },
    { value: "27", label: t('discovery.catEducation') },
    { value: "28", label: t('discovery.catScience') },
  ], [t]);
  const [region, setRegion] = useState("US");
  const [categoryId, setCategoryId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TrendDiscoveryResponse | null>(null);
  const [history, setHistory] = useState<TrendHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // 无限滚动状态
  const [displayCount, setDisplayCount] = useState(20);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // 排序状态
  type SortField = "view_count" | "like_count" | "comment_count" | "engagement_rate" | "channel_subscribers";
  type SortOrder = "asc" | "desc";
  const [sortField, setSortField] = useState<SortField>("view_count");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  /** {t('discovery.fetchTrend')}查阅历史（仅已登录用户，游客无历史记录） */
  const fetchHistory = useCallback(async () => {
    if (!token) return;
    setHistoryLoading(true);
    try {
      const res = await trendHistoryApi(10);
      setHistory(res.items);
    } catch {
      // 静默失败
    } finally {
      setHistoryLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleFetch = async () => {
    setLoading(true);
    try {
      const res = await trendDiscoveryApi({
        region,
        category_id: categoryId || undefined,
        max_results: 50,
        region_label: t(getRegionLabel(region)),
        category_label: t(getCategoryLabel(categoryId)),
      });
      setResult(res);
      setDisplayCount(20);
      // 刷新历史
      await fetchHistory();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || t("discovery.fetchFailed"));
    } finally {
      setLoading(false);
    }
  };

  // 入库确认
  const handleAddChannel = (record: any) => {
    Modal.confirm({
      title: t("discovery.importChannel", { title: record.channel_title }),
      content: t("discovery.importChannelContent", { channelId: record.channel_id, subscribers: formatNumber(record.channel_subscribers) }),
      okText: t("discovery.confirmImport"),
      cancelText: t("discovery.cancel"),
      okButtonProps: { style: { background: "var(--color-danger)", borderColor: "var(--color-danger)" } },
      onOk: async () => {
        try {
          const res = await addChannelByIdApi({
            channel_id: record.channel_id,
            channel_title: record.channel_title,
            thumbnail_url: record.thumbnail_url,
            subscriber_count: record.channel_subscribers,
          });
          message.success(res.message);
        } catch (e: any) {
          message.error(e?.response?.data?.detail || t("discovery.importFailed"));
        }
      },
    });
  };

  // 排序后的视频列表
  const sortedVideos = result
    ? [...result.trending_videos].sort((a, b) => {
        const va = a[sortField] ?? 0;
        const vb = b[sortField] ?? 0;
        return sortOrder === "asc" ? va - vb : vb - va;
      })
    : [];
  const visibleVideos = sortedVideos.slice(0, displayCount);

  // 无限滚动：Intersection Observer
  useEffect(() => {
    if (!result || !sentinelRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          const total = sortedVideos.length;
          if (displayCount < total) {
            setDisplayCount((prev) => Math.min(prev + 20, total));
          }
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [result, displayCount, sortedVideos.length]);

  /** 点击历史记录回溯（仅已登录用户，游客无历史记录） */
  const handleHistoryClick = async (item: TrendHistoryItem) => {
    if (!token) return;
    setLoading(true);
    try {
      // 优先从缓存读取已保存的趋势数据（不消耗 YouTube 配额）
      const res = await trendCacheApi(item.region, item.category_id, item.cache_date);
      setResult(res);
    } catch {
      // 缓存不存在（404），回退到完整趋势查询
      try {
        const res = await trendDiscoveryApi({
          region: item.region,
          category_id: item.category_id || undefined,
          max_results: 50,
          region_label: t(getRegionLabel(item.region)),
          category_label: t(getCategoryLabel(item.category_id)),
        });
        setResult(res);
      } catch (e: any) {
        message.error(e?.response?.data?.detail || t("discovery.fetchFailed"));
      }
    } finally {
      setRegion(item.region);
      setCategoryId(item.category_id ?? "");
      setDisplayCount(20);
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto">
      <Title level={3} style={{ marginBottom: 24 }}>
        <FireOutlined style={{ marginRight: 8, color: "var(--color-danger)" }} />
        {t('title')}
      </Title>

      {/* 搜索区 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <GlobalOutlined />
              <Text strong>{t('discovery.region')}</Text>
            </Space>
            <Select
              value={region}
              onChange={setRegion}
              options={REGION_OPTIONS}
              style={{ width: 160, marginLeft: 8 }}
            />
          </Col>
          <Col>
            <Space>
              <RiseOutlined />
              <Text strong>{t('discovery.category')}</Text>
            </Space>
            <Select
              value={categoryId}
              onChange={setCategoryId}
              options={CATEGORY_OPTIONS}
              style={{ width: 160, marginLeft: 8 }}
            />
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<FireOutlined />}
              loading={loading}
              onClick={handleFetch}
              size="large"
            >
              {t('discovery.fetchTrend')}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 趋势历史 */}
      {history.length > 0 && (
        <Card
          title={<><HistoryOutlined style={{ marginRight: 8 }} />{t('discovery.recentHistory')}</>}
          style={{ marginBottom: 24 }}
          size="small"
          loading={historyLoading}
        >
          <Space wrap>
            {history.map((item) => (
              <Tag
                key={item.id}
                color="processing"
                style={{ fontSize: 13, padding: "4px 10px", cursor: "pointer" }}
                onClick={() => handleHistoryClick(item)}
              >
                {item.region_label} → {item.category_label}
                <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>
                  {item.cache_date}
                </Text>
              </Tag>
            ))}
          </Space>
        </Card>
      )}

      {result && (
        <>
          {/* 统计摘要 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('discovery.trendVideoCount')}
                  value={result.stats.total_videos}
                  prefix={<FireOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('discovery.avgViews')}
                  value={result.stats.avg_views}
                  prefix={<EyeOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('discovery.avgLikes')}
                  value={result.stats.avg_likes}
                  prefix={<LikeOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('discovery.avgEngagementRate')}
                  value={result.stats.avg_engagement_rate}
                  suffix="%"
                  precision={2}
                  prefix={<RiseOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* {t('discovery.category')}分布 */}
          {result.category_distribution?.length > 0 && (
            <Card
              title={t('discovery.categoryDistribution')}
              style={{ marginBottom: 24 }}
              size="small"
            >
              <Space wrap>
                {result.category_distribution.map((cat: any) => (
                  <Tag
                    key={cat.category_id}
                    color={
                      cat.percentage >= 20
                        ? "error"
                        : cat.percentage >= 10
                        ? "processing"
                        : "default"
                    }
                    style={{ fontSize: 13, padding: "4px 10px" }}
                  >
                    {cat.category_name}: {cat.video_count} ({cat.percentage}%)
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          {/* {t('discovery.trendVideoRanking')} - 无限滚动 */}
          <Card title={t('discovery.trendVideoRanking')} size="small">
            <div ref={scrollContainerRef} style={{ maxHeight: "70vh", overflowY: "auto" }}>
              {/* 表头 */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "48px 1fr 100px 90px 90px 100px 110px 80px",
                  gap: 8,
                  padding: "8px 0",
                  borderBottom: "1px solid var(--color-border)",
                  fontWeight: 600,
                  fontSize: 13,
                  color: "var(--color-text-secondary)",
                }}
              >
                <div>#</div>
                <div>{t('discovery.video')}</div>
                <SortHeader label={t("discovery.viewCount")} field="view_count" current={sortField} order={sortOrder} onSort={handleSort} />
                <SortHeader label={t("discovery.likeCount")} field="like_count" current={sortField} order={sortOrder} onSort={handleSort} />
                <SortHeader label={t("discovery.commentCount")} field="comment_count" current={sortField} order={sortOrder} onSort={handleSort} />
                <SortHeader label={t("discovery.engagementRate")} field="engagement_rate" current={sortField} order={sortOrder} onSort={handleSort} />
                <SortHeader label={t("discovery.channelSubscribers")} field="channel_subscribers" current={sortField} order={sortOrder} onSort={handleSort} />
                <div>{t('discovery.action')}</div>
              </div>

              {/* 视频行 */}
              {visibleVideos.map((record, idx) => (
                <div
                  key={record.video_id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "48px 1fr 100px 90px 90px 100px 110px 80px",
                    gap: 8,
                    padding: "8px 0",
                    borderBottom: "1px solid var(--color-border)",
                    fontSize: 13,
                    cursor: "pointer",
                    alignItems: "center",
                  }}
                  onClick={() => { const u = buildYouTubeWatchUrl(record.video_id); if (u) window.open(u, "_blank"); }}
                >
                  <div style={{ color: "var(--color-text-tertiary)" }}>{idx + 1}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                    {record.thumbnail_url && (
                      <Image
                        src={record.thumbnail_url}
                        width={80}
                        height={45}
                        style={{ borderRadius: 4, objectFit: "cover" }}
                        fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN88P/BfwAJhAPk2iMa1AAAAABJRU5ErkJggg=="
                        preview={false}
                      />
                    )}
                    <div style={{ minWidth: 0 }}>
                      <Tooltip title={record.title}>
                        <Text ellipsis style={{ maxWidth: 260, display: "block" }}>
                          {record.title}
                        </Text>
                      </Tooltip>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {record.channel_title}
                      </Text>
                    </div>
                  </div>
                  <div><Space size={4}><EyeOutlined />{formatNumber(record.view_count)}</Space></div>
                  <div><Space size={4}><LikeOutlined />{formatNumber(record.like_count)}</Space></div>
                  <div><Space size={4}><MessageOutlined />{formatNumber(record.comment_count)}</Space></div>
                  <div>
                    <Tag color={record.engagement_rate >= 5 ? "success" : record.engagement_rate >= 2 ? "processing" : "warning"}>
                      {record.engagement_rate.toFixed(2)}%
                    </Tag>
                  </div>
                  <div>{formatNumber(record.channel_subscribers)}</div>
                  <div>
                    {token && (
                    <Button
                      type="primary"
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAddChannel(record);
                      }}
                      style={{ background: "var(--color-danger)", borderColor: "var(--color-danger)" }}
                    >
                      {t('discovery.import')}
                    </Button>
                    )}
                  </div>
                </div>
              ))}

              {/* 加载更多哨兵 */}
              {sortedVideos.length > displayCount && (
                <div ref={sentinelRef} style={{ textAlign: "center", padding: "16px 0" }}>
                  <Spin size="small" />
                  <Text type="secondary" style={{ marginLeft: 8 }}>{t("discovery.loadMore")}</Text>
                </div>
              )}

              {displayCount >= sortedVideos.length && sortedVideos.length > 0 && (
                <div style={{ textAlign: "center", padding: "16px 0", color: "var(--color-text-tertiary)" }}>
                  {t("discovery.allLoaded", { count: sortedVideos.length })}
                </div>
              )}
            </div>
          </Card>
        </>
      )}

      {!result && !loading && (
        <Card>
          <Empty
            description={t('discovery.emptyHint')}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      )}
    </div>
  );
}