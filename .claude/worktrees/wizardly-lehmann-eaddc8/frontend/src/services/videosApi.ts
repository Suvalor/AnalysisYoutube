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

// ---------------------------------------------------------------------------
// Video Highlights (精彩片段)
// ---------------------------------------------------------------------------

export interface VideoHighlight {
  id: number;
  video_id: number;
  user_id: number;
  start_sec: number;
  end_sec: number;
  score: number;
  label: string;
  source: string;
  created_at: string;
}

export interface ExtractHighlightsResponse {
  highlights: VideoHighlight[];
  message: string;
}

export interface HighlightCreateRequest {
  start_sec: number;
  end_sec: number;
  label?: string;
  score?: number;
}

/** Use AI to extract highlight segments from a video. */
export async function extractVideoHighlightsApi(videoId: number): Promise<ExtractHighlightsResponse> {
  const { data } = await apiClient.post<ExtractHighlightsResponse>(`/api/videos/${videoId}/extract-highlights`);
  return data;
}

/** Get highlight segments for a video. */
export async function getVideoHighlightsApi(videoId: number): Promise<VideoHighlight[]> {
  const { data } = await apiClient.get<VideoHighlight[]>(`/api/videos/${videoId}/highlights`);
  return data;
}

/** Manually add a highlight segment. */
export async function addVideoHighlightApi(videoId: number, payload: HighlightCreateRequest): Promise<VideoHighlight> {
  const { data } = await apiClient.post<VideoHighlight>(`/api/videos/${videoId}/highlights`, payload);
  return data;
}

/** Delete a highlight segment. */
export async function deleteVideoHighlightApi(videoId: number, highlightId: number): Promise<void> {
  await apiClient.delete(`/api/videos/${videoId}/highlights/${highlightId}`);
}

