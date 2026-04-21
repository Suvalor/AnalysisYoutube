import React, { useState } from "react";
import {
  Card,
  Input,
  Button,
  Tag,
  Progress,
  Descriptions,
  Space,
  Typography,
  Alert,
  Row,
  Col,
  Divider,
  Tooltip,
} from "antd";
import {
  SearchOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { seoScoringApi } from "@/services/authApi";

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
  const [targetKeyword, setTargetKeyword] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

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
        target_keyword: targetKeyword.trim() || undefined,
      });
      setResult(res);
    } catch (e: any) {
      console.error("SEO 评分失败", e);
    } finally {
      setLoading(false);
    }
  };

  const totalLevel = result ? getSeoLevel(result.total_score, 100) : null;

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <SearchOutlined style={{ marginRight: 8 }} />
        SEO 评分
      </Title>

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
            <Col span={16}>
              <Text strong>标签（逗号分隔）</Text>
              <Input
                placeholder="标签1, 标签2, 标签3"
                value={tagsText}
                onChange={(e) => setTagsText(e.target.value)}
                style={{ marginTop: 4 }}
              />
            </Col>
            <Col span={8}>
              <Text strong>目标关键词</Text>
              <Input
                placeholder="如：Python 教程"
                value={targetKeyword}
                onChange={(e) => setTargetKeyword(e.target.value)}
                style={{ marginTop: 4 }}
              />
            </Col>
          </Row>

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
          {/* 总分 */}
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
                <Space direction="vertical" size="large">
                  <div style={{ textAlign: "center" }}>
                    <Progress
                      type="circle"
                      percent={Math.round((result.title_score / result.title_max) * 100)}
                      format={() => `${result.title_score}/${result.title_max}`}
                      strokeColor={getSeoLevel(result.title_score, result.title_max).color}
                      size={80}
                    />
                    <div style={{ marginTop: 4 }}>
                      <Text strong>标题</Text>
                    </div>
                  </div>
                </Space>
                <Space direction="vertical" size="large" style={{ marginLeft: 32 }}>
                  <div style={{ textAlign: "center" }}>
                    <Progress
                      type="circle"
                      percent={Math.round((result.description_score / result.description_max) * 100)}
                      format={() => `${result.description_score}/${result.description_max}`}
                      strokeColor={getSeoLevel(result.description_score, result.description_max).color}
                      size={80}
                    />
                    <div style={{ marginTop: 4 }}>
                      <Text strong>描述</Text>
                    </div>
                  </div>
                </Space>
                <Space direction="vertical" size="large" style={{ marginLeft: 32 }}>
                  <div style={{ textAlign: "center" }}>
                    <Progress
                      type="circle"
                      percent={Math.round((result.tags_score / result.tags_max) * 100)}
                      format={() => `${result.tags_score}/${result.tags_max}`}
                      strokeColor={getSeoLevel(result.tags_score, result.tags_max).color}
                      size={80}
                    />
                    <div style={{ marginTop: 4 }}>
                      <Text strong>标签</Text>
                    </div>
                  </div>
                </Space>
              </Col>
            </Row>
          </Card>

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

          {/* 详细评分 */}
          <Card title="评分详情">
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="标题得分">
                <Space>
                  <Progress
                    percent={Math.round((result.title_score / result.title_max) * 100)}
                    strokeColor={getSeoLevel(result.title_score, result.title_max).color}
                    style={{ width: 200 }}
                    size="small"
                  />
                  <Text>
                    {result.title_score} / {result.title_max}
                  </Text>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="描述得分">
                <Space>
                  <Progress
                    percent={Math.round((result.description_score / result.description_max) * 100)}
                    strokeColor={getSeoLevel(result.description_score, result.description_max).color}
                    style={{ width: 200 }}
                    size="small"
                  />
                  <Text>
                    {result.description_score} / {result.description_max}
                  </Text>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="标签得分">
                <Space>
                  <Progress
                    percent={Math.round((result.tags_score / result.tags_max) * 100)}
                    strokeColor={getSeoLevel(result.tags_score, result.tags_max).color}
                    style={{ width: 200 }}
                    size="small"
                  />
                  <Text>
                    {result.tags_score} / {result.tags_max}
                  </Text>
                </Space>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </>
      )}
    </div>
  );
}
