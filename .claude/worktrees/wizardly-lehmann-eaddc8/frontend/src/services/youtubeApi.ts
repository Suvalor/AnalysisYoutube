import apiClient from "./apiClient";

export type YouTubeOAuthUrlResponse = {
  auth_url: string;
  state: string;
};

export type YouTubeOAuthStatusResponse = {
  connected: boolean;
  channel_id: string | null;
  expires_at: string | null;
};

export type YouTubePublishResponse = {
  status: string;
  video_id: string | null;
  message: string;
};

export async function getYouTubeOAuthUrlApi() {
  const res = await apiClient.get("/api/youtube/oauth/url");
  return res.data as YouTubeOAuthUrlResponse;
}

export async function completeYouTubeOAuthApi(payload: {
  code: string;
  state?: string | null;
  redirect_uri?: string;
}) {
  const res = await apiClient.post("/api/youtube/oauth/callback", payload);
  return res.data as YouTubeOAuthStatusResponse;
}

export async function getYouTubeOAuthStatusApi() {
  const res = await apiClient.get("/api/youtube/oauth/status");
  return res.data as YouTubeOAuthStatusResponse;
}

export async function publishYouTubeApi(payload: {
  media_url: string;
  title: string;
  description?: string;
  privacy_status?: "private" | "public" | "unlisted";
}) {
  const res = await apiClient.post("/api/youtube/publish", payload);
  return res.data as YouTubePublishResponse;
}
