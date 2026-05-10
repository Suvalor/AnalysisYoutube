import React, { useCallback, useEffect, useRef, useState } from "react";
import { buildYouTubeWatchUrl } from "@/utils/youtubeLinks";
import {
  Card,
  Select,
  Button,
  Tag,
  Row,
  Col,
  Typography,
  Space,
  Image,
  Tooltip,
  Empty,
  message,
  Input,
  Spin,
  Statistic,
} from "antd";
import {
  SearchOutlined,
  GlobalOutlined,
  EyeOutlined,
  LikeOutlined,
  MessageOutlined,
  RiseOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import {
  keywordResearchApi,
  keywordHistoryApi,
  type KeywordHistoryItem,
} from "@/services/authApi";

const { Title, Text } = Typography;

const REGION_OPTIONS = [
  { value: "US", label: "🇺🇸 美国" },
  { value: "GB", label: "🇬🇧 英国" },
  { value: "JP", label: "🇯🇵 日本" },
  { value: "KR", label: "🇰🇷 韩国" },
  { value: "DE", label: "🇩🇪 德国" },
  { value: "FR", label: "🇫🇷 法国" },
  { value: "BR", label: "🇧🇷 巴西" },
  { value: "IN", label: "🇮🇳 印度" },
];

const LANGUAGE_OPTIONS = [
  { value: "zh", label: "中文" },
  { value: "en", label: "英语" },
  { value: "ja", label: "日语" },
  { value: "ko", label: "韩语" },
  { value: "de", label: "德语" },
  { value: "fr", label: "法语" },
  { value: "pt", label: "葡萄牙语" },
  { value: "hi", label: "印地语" },
];

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function getRegionLabel(region: string): string {
  const found = REGION_OPTIONS.find((o) => o.value === region);
  return found ? found.label.replace(/^./, "").trim() : region;
}

function getLanguageLabel(language: string): string {
  const found = LANGUAGE_OPTIONS.find((o) => o.value === language);
  return found ? found.label : language;
}

export default function KeywordResearch() {
  const [keyword, setKeyword] = useState("");
  const [region, setRegion] = useState("US");
  const [language, setLanguage] = useState("zh");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<KeywordHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // 无限滚动状态
  const [displayCount, setDisplayCount] = useState(10);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await keywordHistoryApi(10);
      setHistory(res.items);
    } catch {
      // 静默失败
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSearch = async () => {
    if (!keyword.trim()) {
      message.warning("请输入关键词");
      return;
    }
    setLoading(true);
    try {
      const res = await keywordResearchApi({
        keyword: keyword.trim(),
        region,
        language,
        region_label: getRegionLabel(region),
        language_label: getLanguageLabel(language),
      });
      setResult(res);
      setDisplayCount(10);
      await fetchHistory();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "关键词研究失败");
    } finally {
      setLoading(false);
    }
  };

  // 无限滚动：Intersection Observer
  useEffect(() => {
    if (!result?.popular_videos || !sentinelRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          const total = result.popular_videos.length;
          if (displayCount < total) {
            setDisplayCount((prev) => Math.min(prev + 10, total));
          }
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [result, displayCount]);

  const visibleVideos = result?.popular_videos?.slice(0, displayCount) || [];

  // 点击历史记录回溯
  const handleHistoryClick = async (item: KeywordHistoryItem) => {
    setKeyword(item.keyword);
    setRegion(item.region);
    setLanguage(item.language);
    setLoading(true);
    try {
      const res = await keywordResearchApi({
        keyword: item.keyword,
        region: item.region,
        language: item.language,
        region_label: getRegionLabel(item.region),
        language_label: getLanguageLabel(item.language),
      });
      setResult(res);
      setDisplayCount(10);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "关键词研究失败");
    } finally {
      setLoading(false);
    }
  };

  // 外部传入关键词（从 Channel Growth 联动）
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const kw = params.get("keyword");
    if (kw) {
      setKeyword(kw);
      handleSearchWithKeyword(kw);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [window.location.search]);

  const handleSearchWithKeyword = async (kw: string) => {
    if (!kw.trim()) return;
    setLoading(true);
    try {
      const res = await keywordResearchApi({
        keyword: kw.trim(),
        region,
        language,
        region_label: getRegionLabel(region),
        language_label: getLanguageLabel(language),
      });
      setResult(res);
      setDisplayCount(10);
      await fetchHistory();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "关键词研究失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto">
      <Title level={3} style={{ marginBottom: 24 }}>
        <SearchOutlined style={{ marginRight: 8, color: "var(--color-primary)" }} />
        关键词研究
      </Title>

      {/* 搜索区 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input
              placeholder="输入关键词..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
              size="large"
              prefix={<SearchOutlined />}
            />
          </Col>
          <Col>
            <Space>
              <GlobalOutlined />
              <Text strong>地区</Text>
            </Space>
            <Select
              value={region}
              onChange={setRegion}
              options={REGION_OPTIONS}
              style={{ width: 140, marginLeft: 8 }}
            />
          </Col>
          <Col>
            <Space>
              <RiseOutlined />
              <Text strong>语言</Text>
            </Space>
            <Select
              value={language}
              onChange={setLanguage}
              options={LANGUAGE_OPTIONS}
              style={{ width: 120, marginLeft: 8 }}
            />
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              loading={loading}
              onClick={handleSearch}
              size="large"
            >
              搜索
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 关键词历史 */}
      {history.length > 0 && (
        <Card
          title={<><HistoryOutlined style={{ marginRight: 8 }} />研究历史</>}
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
                {item.keyword}
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
          {/* 搜索概览 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="搜索量"
                  value={result.search_volume || 0}
                  prefix={<SearchOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="竞争度"
                  value={result.competition || 0}
                  prefix={<RiseOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="相关关键词"
                  value={result.related_keywords?.length || 0}
                  prefix={<GlobalOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="热门视频"
                  value={result.popular_videos?.length || 0}
                  prefix={<EyeOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* 相关关键词 */}
          {result.related_keywords?.length > 0 && (
            <Card title="相关关键词" style={{ marginBottom: 24 }} size="small">
              <Space wrap>
                {result.related_keywords.map((kw: any, i: number) => (
                  <Tag
                    key={i}
                    color={kw.search_volume >= 10000 ? "error" : kw.search_volume >= 1000 ? "processing" : "default"}
                    style={{ fontSize: 13, padding: "4px 10px", cursor: "pointer" }}
                    onClick={() => {
                      setKeyword(kw.keyword || kw);
                      handleSearchWithKeyword(kw.keyword || kw);
                    }}
                  >
                    {kw.keyword || kw}
                    {kw.search_volume && <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>({formatNumber(kw.search_volume)})</Text>}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          {/* 热门视频 - 无限滚动 */}
          {result.popular_videos?.length > 0 && (
            <Card title="热门视频" size="small">
              <div style={{ maxHeight: "70vh", overflowY: "auto" }}>
                {/* 表头 */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "48px 1fr 100px 90px 90px 100px",
                    gap: 8,
                    padding: "8px 0",
                    borderBottom: "1px solid var(--color-border)",
                    fontWeight: 600,
                    fontSize: 13,
                    color: "var(--color-text-secondary)",
                  }}
                >
                  <div>#</div>
                  <div>视频</div>
                  <div>播放量</div>
                  <div>点赞</div>
                  <div>评论</div>
                  <div>互动率</div>
                </div>

                {visibleVideos.map((record: any, idx: number) => (
                  <div
                    key={record.video_id || idx}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "48px 1fr 100px 90px 90px 100px",
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
                        {record.engagement_rate?.toFixed(2) || "0.00"}%
                      </Tag>
                    </div>
                  </div>
                ))}

                {result.popular_videos.length > displayCount && (
                  <div ref={sentinelRef} style={{ textAlign: "center", padding: "16px 0" }}>
                    <Spin size="small" />
                    <Text type="secondary" style={{ marginLeft: 8 }}>加载更多...</Text>
                  </div>
                )}

                {displayCount >= result.popular_videos.length && result.popular_videos.length > 0 && (
                  <div style={{ textAlign: "center", padding: "16px 0", color: "var(--color-text-tertiary)" }}>
                    共 {result.popular_videos.length} 条，已全部加载
                  </div>
                )}
              </div>
            </Card>
          )}
        </>
      )}

      {!result && !loading && (
        <Card>
          <Empty
            description="输入关键词，点击「搜索」查看 YouTube 关键词分析"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      )}
    </div>
  );
}