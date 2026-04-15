import apiClient from "./apiClient";

export type AuthFormValues = {
  email: string;
  password: string;
};

export async function registerApi(data: AuthFormValues) {
  const res = await apiClient.post("/api/auth/register", data);
  return res.data;
}

export async function loginApi(data: AuthFormValues) {
  const res = await apiClient.post("/api/auth/login", data);
  return res.data as { access_token: string; token_type: string };
}

export type YouTubeAnalyzeResponse = {
  channel: {
    id: number;
    yt_channel_id: string;
    title: string;
    description: string;
    thumbnail_url: string | null;
    subscriber_count: number;
    total_views: number;
    video_count: number;
    ai_tags: string[] | null;
    ai_expertise: string | null;
    ai_audience_age: string | null;
    ai_summary: string | null;
    /** 最近一次详情页 AI 分析时间（UTC ISO） */
    ai_analyzed_at?: string | null;
    ai_source_model_library_id?: number | null;
    ai_source_llm_model_name?: string | null;
    ai_source_agent_id?: number | null;
    published_at: string | null;
    created_at: string;
    updated_at: string;
  };
  recent_avg_views: number;
  videos: Array<{
    id: number;
    yt_video_id: string;
    title: string;
    thumbnail_url: string | null;
    published_at: string | null;
    duration_sec: number;
    duration_str: string;
    definition: string;
    privacy_status: string;
    category_id: string | null;
    tags: string[];
    view_count: number;
    like_count: number;
    comment_count: number;
  }>;
};

export async function analyzeYouTubeApi(payload: { youtube_url: string; group_name?: string }) {
  const res = await apiClient.post("/api/youtube/analyze", payload);
  return res.data as YouTubeAnalyzeResponse;
}

export type SubmitTaskResponse = {
  code: number;
  message: string;
};

export async function analyzeYouTubeBatchApi(payload: { urls: string; group_name?: string }) {
  const res = await apiClient.post("/api/youtube/analyze/batch", payload);
  return res.data as SubmitTaskResponse;
}

/** 潜力频道挖掘结果项（与后端 DiscoverChannelItem 一致） */
export type DiscoverChannelItem = {
  yt_channel_id: string;
  title: string;
  thumbnail_url: string | null;
  subscriber_count: number;
  total_views: number;
  channel_url: string;
  viral_video_url: string;
};

export type ChannelDiscoverResponse = {
  items: DiscoverChannelItem[];
  warnings: string[];
};

/** 关键词挖掘小号（仅查询 YouTube，不落库；单次 search 约消耗 100 quota） */
export async function discoverChannelsApi(payload: {
  keyword: string;
  published_after: 7 | 14 | 30;
  max_subscribers?: number;
  max_results?: number;
}) {
  const res = await apiClient.post("/api/channels/discover", payload);
  return res.data as ChannelDiscoverResponse;
}

/** 蓝海雷达单条结果（与后端 BlueOceanChannelItem 一致） */
export type BlueOceanChannelItem = {
  yt_channel_id: string;
  title: string;
  thumbnail_url: string | null;
  subscriber_count: number;
  total_views: number;
  channel_url: string;
  viral_video_url: string;
  viral_view_count: number;
  outlier_score: number;
};

export type BlueOceanRadarResponse = {
  items: BlueOceanChannelItem[];
  warnings: string[];
};

export type RadarAiRetrospectiveRequest = {
  lookback_days?: number;
  top_n?: number;
  model_library_id: number;
  llm_model_name: string;
  agent_id: number;
};

export type RadarAiRetrospectiveResponse = {
  analysis_summary: string;
  recommended_parameters: {
    max_subscribers: number;
    outlier_multiplier: number;
    suggested_keywords: string[];
  };
  next_step_action: string;
  sample_meta: {
    lookback_days: number;
    top_count: number;
    low_count: number;
  };
};

/** 蓝海雷达深度扫描（仅查询 YouTube，不落库） */
export async function blueOceanRadarScanApi(payload: {
  keyword: string;
  published_after: 30 | 90 | 180;
  max_subscribers?: number;
  outlier_multiplier?: number;
  video_duration?: "short" | "medium" | "long" | null;
}) {
  const res = await apiClient.post("/api/radar/scan", payload);
  return res.data as BlueOceanRadarResponse;
}

/** 蓝海雷达 AI 复盘：基于近期业务表现推荐参数 */
export async function radarAiRetrospectiveApi(payload: RadarAiRetrospectiveRequest) {
  const res = await apiClient.post("/api/radar/ai-retrospective", payload);
  return res.data as RadarAiRetrospectiveResponse;
}

export async function listYouTubeChannelsApi(params?: { sort_by?: string }) {
  const searchParams = new URLSearchParams();
  if (params?.sort_by) searchParams.append("sort_by", params.sort_by);
  const q = searchParams.toString();
  const res = await apiClient.get(`/api/youtube/channels${q ? `?${q}` : ""}`);
  return res.data as Array<{
    pool_id: number;
    group_name: string;
    added_at: string;
    channel: YouTubeAnalyzeResponse["channel"];
  }>;
}

export async function getYouTubeChannelDetailApi(channelId: number) {
  const res = await apiClient.get(`/api/youtube/channels/detail/${channelId}`);
  return res.data as YouTubeAnalyzeResponse["channel"];
}

/** 博主详情页 AI 深度分析请求体（与后端 YouTubeChannelAiAnalyzeRequest 一致） */
export type ChannelAiAnalyzePayload = {
  model_library_id: number;
  llm_model_name: string;
  agent_id?: number | null;
};

export type ChannelAiAnalyzeResult = {
  tags: string[];
  expertise: string;
  age_group: string;
  summary: string;
  analyzed_at?: string | null;
  model_library_id?: number | null;
  llm_model_name?: string | null;
  agent_id?: number | null;
};

export async function analyzeYouTubeChannelAiApi(channelId: number, payload: ChannelAiAnalyzePayload) {
  const res = await apiClient.post(`/api/youtube/channels/${channelId}/ai-analyze`, payload);
  return res.data as ChannelAiAnalyzeResult;
}

export async function scrapeVideoCommentsApi(videoId: number, keyword: string) {
  const res = await apiClient.post(`/api/youtube/videos/${videoId}/comments/scrape`, { keyword });
  return res.data as { scraped_count: number; quota_used: number };
}

export async function deleteYouTubeChannelApi(poolId: number) {
  const res = await apiClient.delete(`/api/youtube/channels/${poolId}`);
  return res.data as { success: boolean };
}

export async function compareCompetitorsApi(params: { channel_ids: number[]; days?: number }) {
  const searchParams = new URLSearchParams();
  params.channel_ids.forEach((id) => searchParams.append("channel_ids", String(id)));
  searchParams.append("days", String(params.days ?? 30));
  const res = await apiClient.get(`/api/youtube/competitors/compare?${searchParams.toString()}`);
  return res.data as Array<Record<string, string | number>>;
}

export async function getYouTubeQuotaDashboardApi() {
  const res = await apiClient.get("/api/youtube/quota-dashboard");
  return res.data as {
    today_total: number;
    today_used: number;
    today_remaining: number;
    history: Array<{ date: string; points_used: number }>;
  };
}

export async function batchUpdateChannelsApi() {
  const res = await apiClient.post("/api/youtube/channels/batch-update");
  return res.data as SubmitTaskResponse;
}

export type VideoListItem = YouTubeAnalyzeResponse["videos"][number] & {
  channel_title?: string | null;
  /** 列表接口附带：当前组织是否已有持久化视频 AI 分析（仅布尔，正文仍走独立 GET） */
  has_analysis?: boolean;
};

export async function listYouTubeVideosApi(params: {
  keyword?: string;
  start_date?: string;
  end_date?: string;
  min_duration?: number;
  max_duration?: number;
  min_view_count?: number;
  max_view_count?: number;
  min_like_count?: number;
  max_like_count?: number;
  min_comment_count?: number;
  max_comment_count?: number;
  channel_id?: number;
  definition?: string;
  privacy_status?: string;
  /** 单列排序（未传多列参数时使用） */
  sort_by?: string;
  /** 多列同时排序，与 sort_by 二选一：任意一项有值则按多列 ORDER BY（优先级见后端说明） */
  publish_time_sort?: "asc" | "desc";
  view_count_sort?: "asc" | "desc";
  like_count_sort?: "asc" | "desc";
  comment_count_sort?: "asc" | "desc";
  page?: number;
  page_size?: number;
}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && `${v}` !== "") {
      searchParams.append(k, String(v));
    }
  });
  const res = await apiClient.get(`/api/youtube/videos?${searchParams.toString()}`);
  return res.data as {
    items: VideoListItem[];
    total: number;
    page: number;
    page_size: number;
  };
}

export async function listYouTubeVideosAllApi(params: Parameters<typeof listYouTubeVideosApi>[0]) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && `${v}` !== "") {
      searchParams.append(k, String(v));
    }
  });
  const res = await apiClient.get(`/api/youtube/videos/all?${searchParams.toString()}`);
  return res.data as {
    items: VideoListItem[];
    total: number;
    page: number;
    page_size: number;
  };
}

