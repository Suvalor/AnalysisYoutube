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
  status: DownloadStatus;
  local_path: string;
  error_message: string;
  file_size: number;
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

/** Submit a video mix task (runs in background). */
export async function submitMix(payload: MixRequest): Promise<MixResponse> {
  const { data } = await apiClient.post<MixResponse>('/api/materials/mix', payload);
  return data;
}
