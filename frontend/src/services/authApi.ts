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
    view_count: number;
    like_count: number;
    comment_count: number;
  }>;
};

export async function analyzeYouTubeApi(payload: { youtube_url: string; group_name?: string }) {
  const res = await apiClient.post("/api/youtube/analyze", payload);
  return res.data as YouTubeAnalyzeResponse;
}

export async function listYouTubeChannelsApi() {
  const res = await apiClient.get("/api/youtube/channels");
  return res.data as Array<{
    pool_id: number;
    group_name: string;
    added_at: string;
    channel: YouTubeAnalyzeResponse["channel"];
  }>;
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
  return res.data as {
    estimated_points: number;
    updated_channels: number;
    updated_videos: number;
  };
}

export async function listYouTubeVideosApi(params: {
  keyword?: string;
  start_date?: string;
  end_date?: string;
  min_duration?: number;
  max_duration?: number;
  channel_id?: number;
  definition?: string;
  privacy_status?: string;
  sort_by?: string;
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
    items: YouTubeAnalyzeResponse["videos"];
    total: number;
    page: number;
    page_size: number;
  };
}

