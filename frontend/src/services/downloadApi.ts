import apiClient from './apiClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DownloadRequest {
  video_ids: string[];
}

export interface DownloadResponse {
  message: string;
  task_count: number;
  skipped: string[];
}

export type DownloadStatus = 'PENDING' | 'DOWNLOADING' | 'COMPLETED' | 'FAILED';

export interface DownloadTask {
  id: number;
  video_id: string;
  video_title: string | null;
  thumbnail_url: string | null;
  status: DownloadStatus;
  has_file: boolean;
  error_message: string;
  file_size: number;
  progress: number;
  video_channel_title: string | null;
  video_published_at: string | null;
  video_view_count: number | null;
  video_like_count: number | null;
  video_comment_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface DownloadTaskListResponse {
  items: DownloadTask[];
  total: number;
}

export interface MixRequest {
  video_ids: string[];
  narration_text?: string;
  audio_file_id?: string;
  aspect_ratio: '16:9' | '9:16';
  use_highlights?: boolean;
}

export interface MixResponse {
  message: string;
  task_id: number;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** Submit video download tasks (runs in background). */
export async function submitDownload(payload: DownloadRequest): Promise<DownloadResponse> {
  const { data } = await apiClient.post<DownloadResponse>('/api/downloads/download', payload);
  return data;
}

/** List download tasks with optional status filter. */
export async function deleteDownloadTaskApi(taskId: number): Promise<{ message: string }> {
  const { data } = await apiClient.delete<{ message: string }>(`/api/downloads/download-tasks/${taskId}`);
  return data;
}

export async function listDownloadTasks(params?: {
  status?: DownloadStatus;
  offset?: number;
  limit?: number;
}): Promise<DownloadTaskListResponse> {
  const { data } = await apiClient.get<DownloadTaskListResponse>('/api/downloads/download-tasks', { params });
  return data;
}

/** Get a single download task by ID. */
export async function getDownloadTask(taskId: number): Promise<DownloadTask> {
  const { data } = await apiClient.get<DownloadTask>(`/api/downloads/download-tasks/${taskId}`);
  return data;
}

/** Request a short-lived play token for video playback (replaces JWT-in-URL). */
export async function requestPlayToken(taskId: number): Promise<{ play_token: string }> {
  const { data } = await apiClient.post<{ play_token: string }>(
    `/api/downloads/download-tasks/${taskId}/play-token`
  );
  return data;
}

/** Build the URL for serving a download task's video file. */
export function getDownloadFileUrl(taskId: number): string {
  return `/api/downloads/download-tasks/${taskId}/file`;
}

export async function retryDownloadTaskApi(taskId: number): Promise<DownloadTask> {
  const { data } = await apiClient.post<DownloadTask>(`/api/downloads/download-tasks/${taskId}/retry`);
  return data;
}

/** Submit a video mix task (runs in background). */
export async function submitMix(payload: MixRequest): Promise<MixResponse> {
  const { data } = await apiClient.post<MixResponse>('/api/v1/materials/mix', payload);
  return data;
}
