import apiClient from "./apiClient";

export type YouTubeVideoAnalysisResponse = {
  video_id: number;
  model_id: string;
  agent_id: number | null;
  content: string;
  updated_at: string;
};

export async function analyzeYouTubeVideoApi(payload: {
  video_id: number;
  model_id: string;
  agent_id?: number | null;
}) {
  const res = await apiClient.post("/api/videos/analyze", payload);
  return res.data as YouTubeVideoAnalysisResponse;
}

export async function getYouTubeVideoAnalysisApi(videoId: number) {
  const res = await apiClient.get(`/api/videos/analysis/${videoId}`);
  return res.data as YouTubeVideoAnalysisResponse;
}

