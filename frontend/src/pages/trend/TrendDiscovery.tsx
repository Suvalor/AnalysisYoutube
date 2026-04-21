import React, { useState } from "react";
import {
  Card,
  Select,
  Button,
  Table,
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
} from "antd";
import {
  FireOutlined,
  GlobalOutlined,
  EyeOutlined,
  LikeOutlined,
  MessageOutlined,
  RiseOutlined,
} from "@ant-design/icons";
import { trendDiscoveryApi } from "@/services/authApi";

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
  { value: "CA", label: "🇨🇦 加拿大" },
  { value: "AU", label: "🇦🇺 澳大利亚" },
];

const CATEGORY_OPTIONS = [
  { value: "", label: "全部品类" },
  { value: "1", label: "电影与动画" },
  { value: "2", label: "汽车与车辆" },
  { value: "10", label: "音乐" },
  { value: "15", label: "宠物与动物" },
  { value: "17", label: "体育" },
  { value: "20", label: "游戏" },
  { value: "22", label: "人物与博客" },
  { value: "23", label: "喜剧" },
  { value: "24", label: "娱乐" },
  { value: "25", label: "新闻与政治" },
  { value: "26", label: "操作指南与风格" },
  { value: "27", label: "教育" },
  { value: "28", label: "科学与技术" },
];

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function TrendDiscovery() {
  const [region, setRegion] = useState("US");
  const [categoryId, setCategoryId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleFetch = async () => {
    setLoading(true);
    try {
      const res = await trendDiscoveryApi({
        region,
        category_id: categoryId || undefined,
        max_results: 50,
      });
      setResult(res);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "获取趋势数据失败");
    } finally {
      setLoading(false);
    }
  };

  const videoColumns = [
    {
      title: "#",
      width: 48,
      render: (_: any, __: any, idx: number) => idx + 1,
    },
    {
      title: "视频",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      render: (title: string, record: any) => (
        <Space>
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
          <div>
            <Tooltip title={title}>
              <Text ellipsis style={{ maxWidth: 260, display: "block" }}>
                {title}
              </Text>
            </Tooltip>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.channel_title}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: "播放量",
      dataIndex: "view_count",
      key: "view_count",
      width: 100,
      sorter: (a: any, b: any) => a.view_count - b.view_count,
      render: (v: number) => (
        <Space size={4}>
          <EyeOutlined />
          {formatNumber(v)}
        </Space>
      ),
    },
    {
      title: "点赞",
      dataIndex: "like_count",
      key: "like_count",
      width: 90,
      sorter: (a: any, b: any) => a.like_count - b.like_count,
      render: (v: number) => (
        <Space size={4}>
          <LikeOutlined />
          {formatNumber(v)}
        </Space>
      ),
    },
    {
      title: "评论",
      dataIndex: "comment_count",
      key: "comment_count",
      width: 90,
      render: (v: number) => (
        <Space size={4}>
          <MessageOutlined />
          {formatNumber(v)}
        </Space>
      ),
    },
    {
      title: "互动率",
      dataIndex: "engagement_rate",
      key: "engagement_rate",
      width: 100,
      sorter: (a: any, b: any) => a.engagement_rate - b.engagement_rate,
      render: (v: number) => {
        const color = v >= 5 ? "#52c41a" : v >= 2 ? "#1890ff" : "#faad14";
        return <Tag color={color}>{v.toFixed(2)}%</Tag>;
      },
    },
    {
      title: "频道订阅",
      dataIndex: "channel_subscribers",
      key: "channel_subscribers",
      width: 110,
      sorter: (a: any, b: any) => a.channel_subscribers - b.channel_subscribers,
      render: (v: number) => formatNumber(v),
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <FireOutlined style={{ marginRight: 8, color: "#ff4d4f" }} />
        热门趋势
      </Title>

      {/* 搜索区 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <GlobalOutlined />
              <Text strong>地区</Text>
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
              <Text strong>品类</Text>
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
              获取趋势
            </Button>
          </Col>
        </Row>
      </Card>

      {result && (
        <>
          {/* 统计摘要 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="趋势视频数"
                  value={result.stats.total_videos}
                  prefix={<FireOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="平均播放量"
                  value={result.stats.avg_views}
                  prefix={<EyeOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="平均点赞"
                  value={result.stats.avg_likes}
                  prefix={<LikeOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="平均互动率"
                  value={result.stats.avg_engagement_rate}
                  suffix="%"
                  precision={2}
                  prefix={<RiseOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* 品类分布 */}
          {result.category_distribution?.length > 0 && (
            <Card
              title="品类分布"
              style={{ marginBottom: 24 }}
              size="small"
            >
              <Space wrap>
                {result.category_distribution.map((cat: any) => (
                  <Tag
                    key={cat.category_id}
                    color={
                      cat.percentage >= 20
                        ? "red"
                        : cat.percentage >= 10
                        ? "blue"
                        : "default"
                    }
                    style={{ fontSize: 13, padding: "4px 10px" }}
                  >
                    {cat.category_name}：{cat.video_count}个 ({cat.percentage}%)
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          {/* 视频列表 */}
          <Card title="趋势视频排行" size="small">
            <Table
              dataSource={result.trending_videos}
              columns={videoColumns}
              rowKey="video_id"
              pagination={{ pageSize: 10, showSizeChanger: false }}
              scroll={{ x: 900 }}
              size="small"
            />
          </Card>
        </>
      )}

      {!result && !loading && (
        <Card>
          <Empty
            description="选择地区和品类，点击「获取趋势」查看 YouTube 热门视频"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      )}
    </div>
  );
}
