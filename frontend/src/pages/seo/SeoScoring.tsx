import React, { useState, useEffect } from "react";
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

const { TextArea } = Input;
const { Title, Text } = Typography;

const SEO_COLORS: Record<string, string> = {
  excellent: "#52c41a",
  good: "#1890ff",
  fair: "#faad14",
  poor: "#ff4d4f",
};

function getSeoLevel(score: number, max: number): { label: string; color: string } {
  const pct = score / max;
  if (pct >= 0.8) return { label: "优秀", color: SEO_COLORS.excellent };
  if (pct >= 0.6) return { label: "良好", color: SEO_COLORS.good };
  if (pct >= 0.4) return { label: "一般", color: SEO_COLORS.fair };
  return { label: "需优化", color: SEO_COLORS.poor };
}

export default function SeoScoring() {
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

  const loadHistory = async (page = 1) => {
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
      message.success("删除成功");
      loadHistory(historyPage);
    } catch {
      message.error("删除失败");
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
        { key: "title", label: "标题", score: result.title_score, max: result.title_max },
        { key: "desc", label: "描述", score: result.description_score, max: result.description_max },
        { key: "tags", label: "标签", score: result.tags_score, max: result.tags_max },
        { key: "thumb", label: "缩略图", score: result.thumbnail_score, max: result.thumbnail_max },
      ]
    : [];

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <SearchOutlined style={{ marginRight: 8 }} />
          SEO 评分
        </Title>
        <Button
          icon={<HistoryOutlined />}
          onClick={() => setHistoryVisible(true)}
        >
          评分历史
        </Button>
      </div>

      {/* 输入区 */}
      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Text strong>视频标题 *</Text>
            <Input
              placeholder="输入视频标题"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={500}
              showCount
              style={{ marginTop: 4 }}
            />
          </div>

          <div>
            <Text strong>视频描述</Text>
            <TextArea
              placeholder="输入视频描述（可选）"
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
              <Text strong>标签（逗号分隔）</Text>
              <Input
                placeholder="标签1, 标签2, 标签3"
                value={tagsText}
                onChange={(e) => setTagsText(e.target.value)}
                style={{ marginTop: 4 }}
              />
            </Col>
            <Col span={12}>
              <Text strong>目标关键词</Text>
              <Input
                placeholder="如：Python 教程"
                value={targetKeyword}
                onChange={(e) => setTargetKeyword(e.target.value)}
                style={{ marginTop: 4 }}
              />
            </Col>
          </Row>

          <div>
            <Text strong>缩略图 URL</Text>
            <Input
              placeholder="输入缩略图图片 URL（可选，用于缩略图评分）"
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
            开始评分
          </Button>
        </Space>
      </Card>

      {/* 结果区 */}
      {result && (
        <>
          {/* 总分 + 维度环形图 */}
          <Card style={{ marginBottom: 24, textAlign: "center" }}>
            <Row justify="center" align="middle" gutter={48}>
              <Col>
                <Progress
                  type="dashboard"
                  percent={result.total_score}
                  format={(p) => (
                    <span style={{ fontSize: 28, fontWeight: 700 }}>{p}</span>
                  )}
                  strokeColor={totalLevel?.color}
                  size={160}
                />
                <div style={{ marginTop: 8 }}>
                  <Tag color={totalLevel?.color} style={{ fontSize: 14, padding: "2px 12px" }}>
                    {totalLevel?.label}
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
                        strokeColor={getSeoLevel(dim.score, dim.max).color}
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

          {/* 评分明细（基础分 + AI 加分） */}
          {result.score_breakdown && (
            <Card
              title={
                <Space>
                  <TrophyOutlined />
                  <span>评分明细</span>
                </Space>
              }
              style={{ marginBottom: 24 }}
              size="small"
            >
              <Row gutter={16}>
                {[
                  { label: "标题", base: result.score_breakdown.title_base, bonus: result.score_breakdown.title_ai_bonus, total: result.title_score },
                  { label: "描述", base: result.score_breakdown.description_base, bonus: result.score_breakdown.description_ai_bonus, total: result.description_score },
                  { label: "标签", base: result.score_breakdown.tags_base, bonus: result.score_breakdown.tags_ai_bonus, total: result.tags_score },
                  { label: "缩略图", base: result.score_breakdown.thumbnail_base, bonus: result.score_breakdown.thumbnail_ai_bonus, total: result.thumbnail_score },
                ].map((item) => (
                  <Col span={6} key={item.label}>
                    <div style={{ textAlign: "center", padding: "8px 0" }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>{item.label}</Text>
                      <div style={{ fontSize: 20, fontWeight: 700 }}>{item.total}/25</div>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        基础 {item.base} + AI {item.bonus}
                      </Text>
                    </div>
                  </Col>
                ))}
              </Row>
            </Card>
          )}

          {/* AI 竞品对标分析 */}
          {result.ai_benchmark && (
            <Card
              title={
                <Space>
                  <TrophyOutlined />
                  <span>AI 竞品对标分析</span>
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              <Collapse
                items={[
                  {
                    key: "title",
                    label: "标题对标",
                    children: result.ai_benchmark.title_benchmark || "暂无分析",
                  },
                  {
                    key: "desc",
                    label: "描述对标",
                    children: result.ai_benchmark.description_benchmark || "暂无分析",
                  },
                  {
                    key: "tags",
                    label: "标签对标",
                    children: result.ai_benchmark.tags_benchmark || "暂无分析",
                  },
                  {
                    key: "thumb",
                    label: "缩略图对标",
                    children: result.ai_benchmark.thumbnail_benchmark || "暂无分析",
                  },
                ]}
                defaultActiveKey={["title"]}
              />
            </Card>
          )}

          {/* 竞品视频摘要 */}
          {result.competitor_summary && result.competitor_summary.length > 0 && (
            <Card
              title="竞品视频参考"
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

          {/* 优化建议 */}
          {result.suggestions?.length > 0 && (
            <Card
              title={
                <Space>
                  <BulbOutlined />
                  <span>优化建议</span>
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
        title="SEO 评分历史"
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
              showTotal: (t) => `共 ${t} 条`,
            }}
            size="small"
            columns={[
              {
                title: "标题",
                dataIndex: "title",
                key: "title",
                ellipsis: true,
                width: 200,
              },
              {
                title: "总分",
                dataIndex: "total_score",
                key: "total_score",
                width: 80,
                render: (v: number) => (
                  <Tag color={getSeoLevel(v, 100).color}>{v}</Tag>
                ),
              },
              {
                title: "标题",
                dataIndex: "title_score",
                key: "title_score",
                width: 60,
                render: (v: number) => `${v}/25`,
              },
              {
                title: "描述",
                dataIndex: "description_score",
                key: "description_score",
                width: 60,
                render: (v: number) => `${v}/25`,
              },
              {
                title: "标签",
                dataIndex: "tags_score",
                key: "tags_score",
                width: 60,
                render: (v: number) => `${v}/25`,
              },
              {
                title: "缩略图",
                dataIndex: "thumbnail_score",
                key: "thumbnail_score",
                width: 70,
                render: (v: number) => `${v}/25`,
              },
              {
                title: "关键词",
                dataIndex: "target_keyword",
                key: "target_keyword",
                width: 100,
                ellipsis: true,
                render: (v: string | null) => v || "-",
              },
              {
                title: "时间",
                dataIndex: "created_at",
                key: "created_at",
                width: 140,
                render: (v: string) => new Date(v).toLocaleString("zh-CN"),
              },
              {
                title: "操作",
                key: "action",
                width: 60,
                render: (_: any, record: SeoScoreRecordItem) => (
                  <Popconfirm
                    title="确定删除此记录？"
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
