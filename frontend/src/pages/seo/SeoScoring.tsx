import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  Input,
  Button,
  Tag,
  Progress,
  Space,
  Typography,
  Alert,
  Row,
  Col,
  Tooltip,
  Table,
  Modal,
  Popconfirm,
  message,
  Collapse,
  Spin,
} from "antd";
import {
  SearchOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  HistoryOutlined,
  DeleteOutlined,
  TrophyOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import {
  seoScoringApi,
  seoScoreHistoryApi,
  deleteSeoScoreRecordApi,
  type SeoScoringResponse,
  type SeoScoreRecordItem,
  type AiBenchmarkResult,
  type ScoreBreakdown,
} from "@/services/authApi";
import { useAuth } from "@/store/authStore";

const { TextArea } = Input;
const { Title, Text } = Typography;

const SEO_TAG_COLORS: Record<string, string> = {
  excellent: "success",
  good: "processing",
  fair: "warning",
  poor: "error",
};

const SEO_STROKE_COLORS: Record<string, string> = {
  excellent: "var(--color-success)",
  good: "var(--color-primary)",
  fair: "var(--color-warning)",
  poor: "var(--color-danger)",
};

/** 根据评分比例返回等级标签 key、标签颜色和进度条颜色 */
function getSeoLevel(score: number, max: number): { labelKey: string; tagColor: string; strokeColor: string } {
  const pct = score / max;
  if (pct >= 0.8) return { labelKey: "scoring.grade.excellent", tagColor: SEO_TAG_COLORS.excellent, strokeColor: SEO_STROKE_COLORS.excellent };
  if (pct >= 0.6) return { labelKey: "scoring.grade.good", tagColor: SEO_TAG_COLORS.good, strokeColor: SEO_STROKE_COLORS.good };
  if (pct >= 0.4) return { labelKey: "scoring.grade.average", tagColor: SEO_TAG_COLORS.fair, strokeColor: SEO_STROKE_COLORS.fair };
  return { labelKey: "scoring.grade.needsOptimization", tagColor: SEO_TAG_COLORS.poor, strokeColor: SEO_STROKE_COLORS.poor };
}

export default function SeoScoring() {
  const { t } = useTranslation("seo");
  const { token } = useAuth();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [thumbnailUrl, setThumbnailUrl] = useState("");
  const [targetKeyword, setTargetKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SeoScoringResponse | null>(null);

  // 历史记录
  const [historyVisible, setHistoryVisible] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyData, setHistoryData] = useState<SeoScoreRecordItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);

  const handleScore = async () => {
    if (!title.trim()) return;
    setLoading(true);
    try {
      const tags = tagsText
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const res = await seoScoringApi({
        title: title.trim(),
        description: description.trim(),
        tags,
        thumbnail_url: thumbnailUrl.trim() || undefined,
        target_keyword: targetKeyword.trim() || undefined,
      });
      setResult(res);
    } catch (e: any) {
      // SEO 评分失败，静默处理
    } finally {
      setLoading(false);
    }
  };

  /** 加载 {t('scoring.scoringTitle')}历史（仅已登录用户，游客无历史记录） */
  const loadHistory = async (page = 1) => {
    if (!token) return;
    setHistoryLoading(true);
    try {
      const res = await seoScoreHistoryApi(page, 20);
      setHistoryData(res.items);
      setHistoryTotal(res.total);
      setHistoryPage(page);
    } catch {
      // 加载历史失败
    } finally {
      setHistoryLoading(false);
    }
  };

  const deleteRecord = async (id: number) => {
    try {
      await deleteSeoScoreRecordApi(id);
      message.success(t("scoring.deleteSuccess"));
      loadHistory(historyPage);
    } catch {
      message.error(t("scoring.deleteFailed"));
    }
  };

  useEffect(() => {
    if (historyVisible) {
      loadHistory(1);
    }
  }, [historyVisible]);

  const totalLevel = result ? getSeoLevel(result.total_score, 100) : null;

  const dimensions = result
    ? [
        { key: "title", label: t("scoring.dimension.title"), score: result.title_score, max: result.title_max },
        { key: "desc", label: t("scoring.dimension.description"), score: result.description_score, max: result.description_max },
        { key: "tags", label: t("scoring.dimension.tags"), score: result.tags_score, max: result.tags_max },
        { key: "thumb", label: t('scoring.thumbnail'), score: result.thumbnail_score, max: result.thumbnail_max },
      ]
    : [];

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <SearchOutlined style={{ marginRight: 8 }} />
          {t('scoring.scoringTitle')}
        </Title>
        {/* {t('scoring.scoreHistory')}按钮（仅已登录用户显示） */}
        {token && (
          <Button
            icon={<HistoryOutlined />}
            onClick={() => setHistoryVisible(true)}
          >
            {t('scoring.scoreHistory')}
          </Button>
        )}
      </div>

      {/* 输入区 */}
      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Text strong>{t('scoring.videoTitleLabel')}</Text>
            <Input
              placeholder={t('scoring.videoTitlePlaceholder')}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={500}
              showCount
              style={{ marginTop: 4 }}
            />
          </div>

          <div>
            <Text strong>{t('scoring.videoDescLabel')}</Text>
            <TextArea
              placeholder={t('scoring.videoDescPlaceholder')}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={5000}
              showCount
              rows={4}
              style={{ marginTop: 4 }}
            />
          </div>

          <Row gutter={16}>
            <Col span={12}>
              <Text strong>{t('scoring.tagsLabel')}</Text>
              <Input
                placeholder={t('scoring.tagsPlaceholder')}
                value={tagsText}
                onChange={(e) => setTagsText(e.target.value)}
                style={{ marginTop: 4 }}
              />
            </Col>
            <Col span={12}>
              <Text strong>{t('scoring.targetKeywordLabel')}</Text>
              <Input
                placeholder={t('scoring.targetKeywordPlaceholder')}
                value={targetKeyword}
                onChange={(e) => setTargetKeyword(e.target.value)}
                style={{ marginTop: 4 }}
              />
            </Col>
          </Row>

          <div>
            <Text strong>{t('scoring.thumbnailUrlLabel')}</Text>
            <Input
              placeholder={t('scoring.thumbnailUrlPlaceholder')}
              value={thumbnailUrl}
              onChange={(e) => setThumbnailUrl(e.target.value)}
              style={{ marginTop: 4 }}
            />
          </div>

          <Button
            type="primary"
            icon={<SearchOutlined />}
            loading={loading}
            onClick={handleScore}
            disabled={!title.trim()}
            size="large"
          >
            {t('scoring.startScoring')}
          </Button>
        </Space>
      </Card>

      {/* 结果区 */}
      {result && (
        <>
          {/* {t('scoring.totalScore')} + 维度环形图 */}
          <Card style={{ marginBottom: 24, textAlign: "center" }}>
            <Row justify="center" align="middle" gutter={48}>
              <Col>
                <Progress
                  type="dashboard"
                  percent={result.total_score}
                  format={(p) => (
                    <span style={{ fontSize: 28, fontWeight: 700 }}>{p}</span>
                  )}
                  strokeColor={totalLevel?.strokeColor}
                  size={160}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color={totalLevel?.tagColor} style={{ fontSize: 14, padding: "2px 12px" }}>
                    {t(totalLevel?.labelKey ?? '')}
                  </Tag>
                </div>
              </Col>
              <Col>
                <Space size={24}>
                  {dimensions.map((dim) => (
                    <div key={dim.key} style={{ textAlign: "center" }}>
                      <Progress
                        type="circle"
                        percent={Math.round((dim.score / dim.max) * 100)}
                        format={() => `${dim.score}/${dim.max}`}
                        strokeColor={getSeoLevel(dim.score, dim.max).strokeColor}
                        size={80}
                      />
                      <div style={{ marginTop: 4 }}>
                        <Text strong>{dim.label}</Text>
                      </div>
                    </div>
                  ))}
                </Space>
              </Col>
            </Row>
          </Card>

          {/* {t('scoring.scoreDetail')}（{t('scoring.baseScore')}分 + AI 加分） */}
          {result.score_breakdown && (
            <Card
              title={
                <Space>
                  <TrophyOutlined />
                  <span>{t('scoring.scoreDetail')}</span>
                </Space>
              }
              style={{ marginBottom: 24 }}
              size="small"
            >
              <Row gutter={16}>
                {[
                  { label: t("scoring.dimension.title"), base: result.score_breakdown.title_base, bonus: result.score_breakdown.title_ai_bonus, total: result.title_score },
                  { label: t("scoring.dimension.description"), base: result.score_breakdown.description_base, bonus: result.score_breakdown.description_ai_bonus, total: result.description_score },
                  { label: t("scoring.dimension.tags"), base: result.score_breakdown.tags_base, bonus: result.score_breakdown.tags_ai_bonus, total: result.tags_score },
                  { label: t('scoring.thumbnail'), base: result.score_breakdown.thumbnail_base, bonus: result.score_breakdown.thumbnail_ai_bonus, total: result.thumbnail_score },
                ].map((item) => (
                  <Col span={6} key={item.label}>
                    <div style={{ textAlign: "center", padding: "8px 0" }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>{item.label}</Text>
                      <div style={{ fontSize: 20, fontWeight: 700 }}>{item.total}/25</div>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {t('scoring.baseScore')} {item.base} + AI {item.bonus}
                      </Text>
                    </div>
                  </Col>
                ))}
              </Row>
            </Card>
          )}

          {/* {t('scoring.aiBenchmark')} */}
          {result.ai_benchmark && (
            <Card
              title={
                <Space>
                  <TrophyOutlined />
                  <span>{t('scoring.aiBenchmark')}</span>
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              <Collapse
                items={[
                  {
                    key: "title",
                    label: t('scoring.titleBenchmark'),
                    children: result.ai_benchmark.title_benchmark || t('scoring.noAnalysis'),
                  },
                  {
                    key: "desc",
                    label: t('scoring.descBenchmark'),
                    children: result.ai_benchmark.description_benchmark || t('scoring.noAnalysis'),
                  },
                  {
                    key: "tags",
                    label: t('scoring.tagsBenchmark'),
                    children: result.ai_benchmark.tags_benchmark || t('scoring.noAnalysis'),
                  },
                  {
                    key: "thumb",
                    label: t("scoring.thumbBenchmark"),
                    children: result.ai_benchmark.thumbnail_benchmark || t("scoring.noAnalysis"),
                  },
                ]}
                defaultActiveKey={["title"]}
              />
            </Card>
          )}

          {/* 竞品视频摘要 */}
          {result.competitor_summary && result.competitor_summary.length > 0 && (
            <Card
              title={t('scoring.competitorRef')}
              size="small"
              style={{ marginBottom: 24 }}
            >
              <Space direction="vertical" style={{ width: "100%" }}>
                {result.competitor_summary.map((c, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Tag color="blue">#{i + 1}</Tag>
                    <Text>{c.title}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>{c.channel_title}</Text>
                  </div>
                ))}
              </Space>
            </Card>
          )}

          {/* {t('scoring.optimizationSuggestions')} */}
          {result.suggestions?.length > 0 && (
            <Card
              title={
                <Space>
                  <BulbOutlined />
                  <span>{t('scoring.optimizationSuggestions')}</span>
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              <Space direction="vertical" style={{ width: "100%" }}>
                {result.suggestions.map((s: string, i: number) => (
                  <Alert
                    key={i}
                    message={s}
                    type="warning"
                    showIcon
                    icon={<WarningOutlined />}
                    style={{ borderRadius: 6 }}
                  />
                ))}
              </Space>
            </Card>
          )}
        </>
      )}

      {/* 历史记录弹窗 */}
      <Modal
        title={t("scoring.historyTitle")}
        open={historyVisible}
        onCancel={() => setHistoryVisible(false)}
        footer={null}
        width={800}
      >
        <Spin spinning={historyLoading}>
          <Table
            dataSource={historyData}
            rowKey="id"
            pagination={{
              current: historyPage,
              total: historyTotal,
              pageSize: 20,
              onChange: (page) => loadHistory(page),
              showTotal: (total) => t("scoring.totalRecords", { total }),
            }}
            size="small"
            columns={[
              {
                title: t("scoring.dimension.title"),
                dataIndex: "title",
                key: "title",
                ellipsis: true,
                width: 200,
              },
              {
                title: t('scoring.totalScore'),
                dataIndex: "total_score",
                key: "total_score",
                width: 80,
                render: (v: number) => (
                  <Tag color={getSeoLevel(v, 100).tagColor}>{v}</Tag>
                ),
              },
              {
                title: t("scoring.dimension.title"),
                dataIndex: "title_score",
                key: "title_score",
                width: 60,
                render: (v: number) => `${v}/25`,
              },
              {
                title: t("scoring.dimension.description"),
                dataIndex: "description_score",
                key: "description_score",
                width: 60,
                render: (v: number) => `${v}/25`,
              },
              {
                title: t("scoring.dimension.tags"),
                dataIndex: "tags_score",
                key: "tags_score",
                width: 60,
                render: (v: number) => `${v}/25`,
              },
              {
                title: t('scoring.thumbnail'),
                dataIndex: "thumbnail_score",
                key: "thumbnail_score",
                width: 70,
                render: (v: number) => `${v}/25`,
              },
              {
                title: t('scoring.keyword'),
                dataIndex: "target_keyword",
                key: "target_keyword",
                width: 100,
                ellipsis: true,
                render: (v: string | null) => v || "-",
              },
              {
                title: t('scoring.time'),
                dataIndex: "created_at",
                key: "created_at",
                width: 140,
                render: (v: string) => new Date(v).toLocaleString("zh-CN"),
              },
              {
                title: t('scoring.action'),
                key: "action",
                width: 60,
                render: (_: any, record: SeoScoreRecordItem) => (
                  <Popconfirm
                    title={t("scoring.confirmDeleteRecord")}
                    onConfirm={() => deleteRecord(record.id)}
                  >
                    <Button type="link" danger size="small" icon={<DeleteOutlined />} />
                  </Popconfirm>
                ),
              },
            ]}
          />
        </Spin>
      </Modal>
    </div>
  );
}
