import { Alert, Button, Card, Empty, Input, Spin, Statistic, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { analyzeYouTubeApi, listYouTubeChannelsApi, YouTubeAnalyzeResponse } from "@/services/authApi";

const { Title, Paragraph, Text } = Typography;

function formatNumber(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

export default function YouTubeMonitor() {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<YouTubeAnalyzeResponse | null>(null);
  const [pool, setPool] = useState<Array<{ pool_id: number; group_name: string; channel: YouTubeAnalyzeResponse["channel"] }>>([]);

  const loadPool = async () => {
    try {
      const data = await listYouTubeChannelsApi();
      setPool(data.map((x) => ({ pool_id: x.pool_id, group_name: x.group_name, channel: x.channel })));
    } catch {
      // 忽略首屏列表错误，不影响分析能力
    }
  };

  useEffect(() => {
    void loadPool();
  }, []);

  const handleAnalyze = async () => {
    if (!youtubeUrl.trim()) {
      setError("请输入 YouTube 频道链接");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeYouTubeApi({ youtube_url: youtubeUrl.trim() });
      setResult(data);
      await loadPool();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "分析失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <Title level={3} style={{ color: "#f8fafc", marginBottom: 8 }}>
            YouTube 对标分析监控台
          </Title>
          <Paragraph style={{ color: "#94a3b8", marginBottom: 16 }}>
            输入频道链接（支持 <Text code>/channel/UC...</Text> 与 <Text code>/@handle</Text>），一键抓取频道与最近 10 条视频数据。
          </Paragraph>
          {error && <Alert type="error" message={error} showIcon className="mb-4" />}
          <div className="flex flex-col md:flex-row gap-3">
            <Input
              size="large"
              placeholder="例如：https://www.youtube.com/@GoogleDevelopers"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
            />
            <Button type="primary" size="large" loading={loading} onClick={handleAnalyze}>
              一键分析
            </Button>
          </div>
        </div>

        <Spin spinning={loading}>
          {result ? (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <Card className="lg:col-span-2 !bg-slate-900/70 !border-slate-800">
                  <div className="flex items-start gap-4">
                    {result.channel.thumbnail_url ? (
                      <img
                        src={result.channel.thumbnail_url}
                        alt="channel"
                        className="w-20 h-20 rounded-full object-cover border border-slate-700"
                      />
                    ) : (
                      <div className="w-20 h-20 rounded-full bg-slate-700" />
                    )}
                    <div className="flex-1">
                      <Title level={4} style={{ color: "#f8fafc", margin: 0 }}>
                        {result.channel.title}
                      </Title>
                      <div className="mt-2">
                        <Tag color="blue">{result.channel.yt_channel_id}</Tag>
                      </div>
                      <Paragraph style={{ color: "#94a3b8", marginTop: 12 }}>
                        {result.channel.description || "暂无简介"}
                      </Paragraph>
                    </div>
                  </div>
                </Card>
                <Card className="!bg-slate-900/70 !border-slate-800">
                  <div className="space-y-3">
                    <Statistic title="订阅数" value={formatNumber(result.channel.subscriber_count)} />
                    <Statistic title="总播放量" value={formatNumber(result.channel.total_views)} />
                    <Statistic title="视频总数" value={formatNumber(result.channel.video_count)} />
                    <Statistic title="近期平均播放量" value={formatNumber(result.recent_avg_views)} />
                  </div>
                </Card>
              </div>

              <Card
                title={<span style={{ color: "#f8fafc" }}>近期视频（最近 10 条）</span>}
                className="!bg-slate-900/70 !border-slate-800"
              >
                {result.videos.length === 0 ? (
                  <Empty description="暂无近期视频数据" />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {result.videos.map((video) => (
                      <Card key={video.id} size="small" className="!bg-slate-950/70 !border-slate-800">
                        {video.thumbnail_url ? (
                          <img
                            src={video.thumbnail_url}
                            alt={video.title}
                            className="w-full h-40 object-cover rounded-lg mb-3"
                          />
                        ) : (
                          <div className="w-full h-40 bg-slate-800 rounded-lg mb-3" />
                        )}
                        <Title level={5} style={{ color: "#f8fafc", marginBottom: 8 }}>
                          {video.title}
                        </Title>
                        <div className="text-slate-300 text-sm space-y-1">
                          <div>发布时间：{video.published_at ? new Date(video.published_at).toLocaleString() : "未知"}</div>
                          <div>播放量：{formatNumber(video.view_count)}</div>
                          <div>点赞量：{formatNumber(video.like_count)}</div>
                          <div>评论量：{formatNumber(video.comment_count)}</div>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </Card>
            </>
          ) : (
            <Card className="!bg-slate-900/70 !border-slate-800">
              <Empty description="输入链接后点击一键分析" />
            </Card>
          )}
        </Spin>

        <Card
          title={<span style={{ color: "#f8fafc" }}>我的监控池频道</span>}
          className="!bg-slate-900/70 !border-slate-800"
        >
          {pool.length === 0 ? (
            <Empty description="当前监控池为空" />
          ) : (
            <div className="flex flex-wrap gap-3">
              {pool.map((item) => (
                <Tag key={item.pool_id} color="geekblue">
                  {item.channel.title} / {item.group_name}
                </Tag>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

